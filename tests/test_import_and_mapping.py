"""実装履歴を起点に調査した取り込み・紐づけの回帰テスト。"""
import os
from pathlib import Path
import tempfile
import time
import shutil
import subprocess
import wave
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QMessageBox

from gui.step_panels.step1_import import ImportWorker, Step1ImportPanel
from gui.step_panels.step2_demucs import Step2DemucsPanel
from gui.step_panels.step3_tagging import Step3TaggingPanel
from logic.demucs_detector import extract_instrumental_files
from logic.state_manager import StateManager
from logic.workflow_manager import WorkflowManager
from logic.instrumental_import import import_instrumental, save_synced_instrumental


class ImportAndMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.album = self.root / "work/Album"
        self.album.mkdir(parents=True)
        self.state = StateManager(str(self.album))
        self.state.initialize("Album", "Artist", [])
        self.workflow = WorkflowManager(Mock())
        self.workflow.load_album(str(self.album))
        self.config = Mock()
        self.config.get_demucs_keywords.return_value = ["(Inst)", "off vocal"]
        self.audio = self.album / "_flac_src/Album"
        self.audio.mkdir(parents=True)

    def tracks(self, names):
        tracks = []
        for i, name in enumerate(names, 1):
            (self.audio / name).write_bytes(name.encode())
            tracks.append({"id": f"track_{i:03}", "originalFile": name,
                           "finalFile": name, "demucsTarget": True})
        self.workflow.state.state["tracks"] = tracks
        return tracks

    def test_copy_worker_does_not_delete_source_before_state_exists(self):
        source = self.root / "source"
        source.mkdir()
        (source / "01 Song.flac").write_bytes(b"audio")
        dest = self.root / "copy"
        worker = ImportWorker(str(source), str(dest))
        with patch("gui.step_panels.step1_import.send2trash") as trash:
            worker.run()
        trash.assert_not_called()
        self.assertEqual((dest / "01 Song.flac").read_bytes(), b"audio")

    def test_initialization_failure_preserves_copied_audio(self):
        (self.album / "01 Song.flac").write_bytes(b"audio")
        panel = Step1ImportPanel(self.config, self.workflow)
        panel.failed_imports = []
        panel.current_import_index = 0
        with patch.object(panel, "_initialize_album_state", return_value=False), \
             patch.object(panel, "_import_next_album"):
            panel._on_single_import_finished(True, "", str(self.album), "Album", "Artist")
        self.assertEqual((self.album / "01 Song.flac").read_bytes(), b"audio")

    def test_existing_destination_and_source_overlap_are_rejected(self):
        source = self.root / "source"
        source.mkdir()
        (source / "01 Song.flac").write_bytes(b"original")
        for destination in [source, source / "copy", self.root]:
            with self.subTest(destination=destination):
                worker = ImportWorker(str(source), str(destination))
                worker.run()
                self.assertFalse(worker.result[0])
                self.assertEqual((source / "01 Song.flac").read_bytes(), b"original")

    def test_initialization_does_not_hide_failed_audio_move(self):
        panel = Step1ImportPanel(self.config, self.workflow)
        (self.album / "01 Song.flac").write_bytes(b"original")
        (self.audio / "02 Existing.flac").write_bytes(b"existing")
        with patch("gui.step_panels.step1_import.os.rename", side_effect=OSError("locked")):
            self.assertFalse(panel._initialize_album_state(str(self.album), "Album", "Artist"))
        self.assertEqual((self.album / "01 Song.flac").read_bytes(), b"original")

    def test_import_trash_failure_keeps_successful_work_and_original(self):
        source = self.root / "source"
        source.mkdir()
        (source / "01 Song.flac").write_bytes(b"original")
        (self.album / "01 Song.flac").write_bytes(b"original")
        panel = Step1ImportPanel(self.config, self.workflow)
        panel.failed_imports = []
        panel.current_import_index = 0
        with patch("gui.step_panels.step1_import.send2trash", side_effect=OSError("busy")), \
             patch("gui.step_panels.step1_import.QTimer.singleShot"):
            panel._on_single_import_finished(True, "", str(self.album), "Album", "Artist", str(source))
        self.assertEqual(panel.failed_imports, [])
        self.assertEqual(len(panel.import_warnings), 1)
        self.assertTrue((source / "01 Song.flac").exists())
        self.assertTrue((self.audio / "01 Song.flac").exists())
        self.state.load()
        self.assertEqual(self.state.get_current_step(), 2)

    def test_sequential_import_waits_for_native_thread_finish(self):
        sources = []
        for name in ["First", "Second"]:
            source = self.root / "original/Artist" / name
            source.mkdir(parents=True)
            (source / "01 Song.flac").write_bytes(b"audio")
            sources.append(str(source))
        work = self.root / "new-work"
        self.config.get_directory.return_value = str(work)
        panel = Step1ImportPanel(self.config, self.workflow)
        panel.selected_sources = sources
        committed_sources = []
        def trash_after_commit(source):
            state = StateManager(str(work / Path(source).name))
            self.assertTrue(state.load())
            self.assertEqual(state.get_current_step(), 2)
            committed_sources.append(source)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
             patch.object(QMessageBox, "information"), patch.object(QMessageBox, "warning"), \
             patch("gui.step_panels.step1_import.send2trash", side_effect=trash_after_commit):
            panel.on_import_all()
            deadline = time.monotonic() + 5
            while panel.importing and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.001)
            if panel.import_worker:
                panel.import_worker.wait(5000)
            self.assertFalse(panel.importing)
        self.assertEqual(committed_sources, sources)
        self.assertEqual(panel.failed_imports, [])

    def test_demucs_flac_output_is_detected(self):
        output = self.root / "demucs/01 Song"
        output.mkdir(parents=True)
        (output / "no_vocals.flac").write_bytes(b"audio")
        self.assertEqual(extract_instrumental_files(str(self.root / "demucs")),
                         [(str(output), str(output / "no_vocals.flac"))])

    def test_demucs_titles_with_dots_are_not_treated_as_extensions(self):
        self.tracks(["01 Mr. Music.flac"])
        panel = Step2DemucsPanel(self.config, self.workflow)
        panel.album_folder = str(self.album)
        self.assertEqual(panel._find_original_for_song("01 Mr. Music"), str(self.audio / "01 Mr. Music.flac"))

    def test_demucs_ambiguous_title_is_not_assigned_to_first_track(self):
        self.tracks(["01 Song.flac", "02 Song.flac"])
        panel = Step2DemucsPanel(self.config, self.workflow)
        panel.album_folder = str(self.album)
        self.assertIsNone(panel._find_original_for_song("Song"))
        self.assertEqual(panel._find_original_for_song("02 Song"), str(self.audio / "02 Song.flac"))

    def test_failed_conversion_preserves_previous_instrumental(self):
        source = self.root / "no_vocals.wav"
        source.write_bytes(b"wav")
        destination = self.audio / "01 Song (Inst).flac"
        destination.write_bytes(b"previous")
        with patch("logic.instrumental_import.ExternalToolRunner") as runner:
            runner.return_value.run_cli_tool.return_value = (False, "", "encode failed")
            with self.assertRaises(OSError):
                import_instrumental(str(source), "original.flac", str(destination), "flac.exe", str(self.album))
        self.assertEqual(destination.read_bytes(), b"previous")
        self.assertEqual(source.read_bytes(), b"wav")
        self.assertEqual(list(self.audio.glob(".demucs-import-*")), [])

    def test_failed_tag_save_preserves_previous_and_demucs_source(self):
        source = self.root / "no_vocals.flac"
        source.write_bytes(b"new")
        destination = self.audio / "01 Song (Inst).flac"
        destination.write_bytes(b"previous")
        original = Mock(tags={"title": ["Song"]}, pictures=[])
        from unittest.mock import MagicMock
        output = MagicMock()
        output.save.side_effect = OSError("tag failed")
        with patch("logic.instrumental_import.FLAC", side_effect=[original, output]):
            with self.assertRaises(OSError):
                import_instrumental(str(source), "original.flac", str(destination), None, str(self.album))
        self.assertEqual(destination.read_bytes(), b"previous")
        self.assertEqual(source.read_bytes(), b"new")

    def test_demucs_flac_import_without_encoder_and_partial_failure(self):
        self.tracks(["01 First.flac", "02 Second.flac"])
        demucs = self.root / "demucs"
        for name in ["01 First", "02 Second"]:
            folder = demucs / name
            folder.mkdir(parents=True)
            (folder / "no_vocals.flac").write_bytes(b"inst")
        self.config.get_tool_path.return_value = None
        self.config.get_default_directory.return_value = str(demucs)
        panel = Step2DemucsPanel(self.config, self.workflow)
        panel.album_folder = str(self.album)
        completed = Mock()
        panel.step_completed.connect(completed)
        def prepare(source, original, destination, *args):
            if "Second" in source:
                raise OSError("bad tags")
            Path(destination).write_bytes(b"ready")
        from PySide6.QtWidgets import QFileDialog
        with patch.object(QFileDialog, "getExistingDirectory", return_value=str(demucs)), \
             patch.object(QMessageBox, "information"), patch.object(QMessageBox, "warning"), \
             patch("logic.instrumental_import.import_instrumental", side_effect=prepare):
            panel.on_demucs_completed()
        self.assertTrue((self.audio / "01 First (Inst).flac").is_file())
        self.assertFalse((self.audio / "Album").exists())
        completed.assert_not_called()
        self.assertEqual(self.workflow.state.get_tracks()[0]["currentInstFile"], "01 First (Inst).flac")

    def test_sync_collision_and_tag_failure_preserve_both_files(self):
        source = self.audio / "original-inst.flac"
        destination = self.audio / "renamed-inst.flac"
        source.write_bytes(b"source")
        destination.write_bytes(b"destination")
        with self.assertRaises(FileExistsError):
            save_synced_instrumental(str(source), str(destination), Mock())
        audio = Mock()
        audio.save.side_effect = OSError("save failed")
        with self.assertRaises(OSError):
            save_synced_instrumental(str(source), str(source), audio)
        self.assertEqual(source.read_bytes(), b"source")
        self.assertEqual(destination.read_bytes(), b"destination")

    @unittest.skipUnless(os.environ.get("RIPTAG_TEST_FLAC") or shutil.which("flac"), "flac.exeが必要な合成音声の統合テスト")
    def test_real_flac_import_and_sync_preserve_audio_and_disc_numbering(self):
        from mutagen.flac import FLAC
        tool = os.environ.get("RIPTAG_TEST_FLAC") or shutil.which("flac")
        wav = self.root / "no_vocals.wav"
        with wave.open(str(wav), "wb") as output:
            output.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
            output.writeframes(b"\x00\x00" * 4410)
        master = self.root / "master.flac"
        subprocess.run([tool, "--silent", str(wav), "-o", str(master)], check=True, capture_output=True)
        tracks = []
        # 意図的に曲番号とstateの順序を逆にし、独立インストの最大番号も含める。
        for index, disc, number, title, independent in [
            (1, 1, 2, "Second", False), (2, 1, 1, "First", False),
            (3, 1, 9, "Piano", True), (4, 2, 1, "First", False)
        ]:
            original = self.audio / f"original-{index}.flac"
            shutil.copy2(master, original)
            metadata = FLAC(original)
            metadata.update(title=[title], tracknumber=[str(number)], discnumber=[str(disc)])
            metadata.save()
            track = {"id": str(index), "originalFile": original.name, "currentFile": original.name,
                     "demucsTarget": not independent, "isInstrumental": independent, "hasInstrumental": not independent}
            if not independent:
                inst = self.audio / f"generated-{index}.flac"
                # WAV変換と既存FLAC取り込みの両方を実ライブラリで検証。
                import_instrumental(str(wav if index == 1 else master), str(original), str(inst), tool, str(self.album))
                track["currentInstFile"] = inst.name
            tracks.append(track)
        self.workflow.state.state["tracks"] = tracks
        panel = self.mapping_panel()
        with patch.object(panel, "update_file_mapping"), patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
             patch.object(QMessageBox, "information"):
            panel.on_sync_instrumental()
            panel.on_sync_instrumental()  # 再実行でも同じ音源を失わない。
        for index, expected in [(0, "11"), (1, "10"), (3, "2")]:
            output = self.audio / tracks[index]["currentInstFile"]
            metadata = FLAC(output)
            self.assertEqual(metadata["tracknumber"], [expected])
            self.assertEqual(metadata["genre"], ["Instrumental"])
            subprocess.run([tool, "--silent", "--test", str(output)], check=True, capture_output=True)
        self.assertTrue(tracks[3]["currentInstFile"].startswith("Disc 2-02-"))
        self.assertTrue(wav.exists())
        self.assertTrue(master.exists())

    def mapping_panel(self):
        panel = Step3TaggingPanel(self.config, self.workflow)
        panel.album_folder = str(self.album)
        return panel

    def test_inst_is_never_shared_between_two_originals(self):
        self.tracks(["01 Song.flac", "02 Song Remix.flac"])
        (self.audio / "03 Song (Inst).flac").write_bytes(b"inst")
        panel = self.mapping_panel()
        with patch.object(panel, "_generate_final_filename", side_effect=lambda name: name):
            panel.update_file_mapping()
        assignments = [t["currentInstFile"] for t in self.workflow.state.get_tracks() if t.get("currentInstFile")]
        self.assertEqual(len(assignments), len(set(assignments)))

    def test_missing_track_clears_final_file_and_instrumental_flag(self):
        tracks = self.tracks(["01 Gone.flac"])
        tracks[0]["hasInstrumental"] = True
        (self.audio / "01 Gone.flac").unlink()
        panel = self.mapping_panel()
        panel.update_file_mapping()
        track = self.workflow.state.get_tracks()[0]
        self.assertFalse(track.get("finalFile"))
        self.assertFalse(track.get("hasInstrumental"))

    def test_missing_track_blocks_step3_completion(self):
        self.tracks(["01 Gone.flac"])
        (self.audio / "01 Gone.flac").unlink()
        panel = self.mapping_panel()
        completed = Mock()
        panel.step_completed.connect(completed)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
             patch.object(QMessageBox, "warning"), patch.object(panel, "_apply_replaygain_if_enabled") as replaygain:
            panel.on_complete()
        completed.assert_not_called()
        replaygain.assert_not_called()

    def test_new_inst_id_does_not_collide_with_existing_id(self):
        tracks = self.tracks(["01 Song.flac"])
        tracks[0]["id"] = "track_002"
        (self.audio / "03 Unrelated (Inst).flac").write_bytes(b"inst")
        panel = self.mapping_panel()
        with patch.object(panel, "_generate_final_filename", side_effect=lambda name: name):
            panel.update_file_mapping()
        ids = [track["id"] for track in self.workflow.state.get_tracks()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_inst_substring_in_title_is_not_an_instrumental_marker(self):
        panel = self.mapping_panel()
        for name in ["01 Instinct.flac", "02 Against.flac", "instrumentals/03 Song.flac"]:
            self.assertFalse(panel._is_instrumental_by_name(name))
        for name in ["01 Song (Inst).flac", "02 Song - Instrumental.flac", "03 Song (off-vocal).flac"]:
            self.assertTrue(panel._is_instrumental_by_name(name))

    def test_rescan_does_not_renumber_independent_disc_track(self):
        self.tracks(["Disc 2-09 Piano (Inst).flac"])
        panel = self.mapping_panel()
        with patch.object(panel, "_generate_final_filename", side_effect=lambda name: name):
            panel.update_file_mapping()
        self.assertEqual(self.workflow.state.get_tracks()[0]["finalFile"], "Disc 2-09 Piano (Inst).flac")

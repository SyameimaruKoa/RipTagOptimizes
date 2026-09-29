import os
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog, QDialog
from gui.step_panels.step2_demucs import Step2DemucsPanel
from gui.step_panels.step3_tagging import Step3TaggingPanel
from gui.step_panels.step6_artwork import Step6ArtworkPanel
from logic.state_manager import StateManager
from logic.workflow_manager import WorkflowManager
from logic.artwork_handler import ensure_artwork_resized_outputs
from logic.demucs_detector import extract_instrumental_files
from gui.manual_mapping_dialog import ManualMappingDialog


class RescanAndRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.album = Path(self.temp.name) / "Album"
        self.audio = self.album / "_flac_src/Album"
        self.audio.mkdir(parents=True)
        state = StateManager(str(self.album))
        state.initialize("Album", "Artist", [])
        self.workflow = WorkflowManager(Mock())
        self.workflow.load_album(str(self.album))
        self.config = Mock()
        self.config.get_demucs_keywords.return_value = []

    def rescan(self, tracks, files):
        self.workflow.state.state["tracks"] = tracks
        for name in files:
            path = self.audio / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"audio")
        panel = Step3TaggingPanel(self.config, self.workflow)
        panel.album_folder = str(self.album)
        with patch.object(panel, "_generate_final_filename", side_effect=lambda name: name):
            panel.update_file_mapping()
        return self.workflow.state.get_tracks()

    def test_rescan_preserves_valid_manual_assignment(self):
        tracks = self.rescan([{"id": "1", "originalFile": "01 Song.flac", "currentFile": "99 Correct.flac"}],
                             ["01 Song.flac", "99 Correct.flac"])
        self.assertEqual(tracks[0]["currentFile"], "99 Correct.flac")

    def test_repeated_current_file_cannot_assign_one_vocal_twice(self):
        tracks = self.rescan([
            {"id": "1", "originalFile": "01 Song.flac", "currentFile": "01 Song.flac"},
            {"id": "2", "originalFile": "02 Song.flac", "currentFile": "01 Song.flac"},
        ], ["01 Song.flac"])
        paths = [t["currentFile"] for t in tracks if t.get("currentFile")]
        self.assertEqual(len(paths), len(set(paths)))

    def test_ambiguous_exact_title_is_not_assigned(self):
        tracks = self.rescan([{"id": "1", "originalFile": "Song.flac"}], ["01 Song.flac", "02 Song.flac"])
        self.assertFalse(tracks[0].get("currentFile"))

    def test_duplicate_song_names_keep_their_disc(self):
        tracks = self.rescan([
            {"id": "1", "originalFile": "01 Song.flac"},
            {"id": "2", "originalFile": "Disc 2-01 Song.flac"},
        ], ["Disc 1-01 Song.flac", "Disc 2-01 Song.flac"])
        self.assertEqual(tracks[0].get("currentFile"), "Disc 1-01 Song.flac")
        self.assertEqual(tracks[1].get("currentFile"), "Disc 2-01 Song.flac")

    def test_demucs_skip_stays_on_step_if_restore_fails(self):
        panel = Step2DemucsPanel(self.config, self.workflow)
        panel.album_folder = str(self.album)
        ignored = self.audio / "demucs_ignore"
        ignored.mkdir()
        (ignored / "01 Song.flac").write_bytes(b"original")
        completed = Mock()
        panel.step_completed.connect(completed)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
             patch.object(QMessageBox, "warning"), patch("shutil.move", side_effect=OSError("locked")):
            panel.on_skip()
        completed.assert_not_called()
        self.assertFalse(self.workflow.state.get_flag("step2_skipped"))

    def test_demucs_duplicate_outputs_from_different_runs_are_rejected(self):
        original = "01 Song.flac"
        (self.audio / original).write_bytes(b"original")
        self.workflow.state.state["tracks"] = [{"id": "1", "originalFile": original, "demucsTarget": True}]
        source = Path(self.temp.name) / "output"
        for run in ["run-a", "run-b"]:
            folder = source / run / "01 Song"
            folder.mkdir(parents=True)
            (folder / "no_vocals.flac").write_bytes(run.encode())
        self.config.get_default_directory.return_value = str(source)
        self.config.get_tool_path.return_value = None
        panel = Step2DemucsPanel(self.config, self.workflow)
        panel.album_folder = str(self.album)
        with patch.object(QFileDialog, "getExistingDirectory", return_value=str(source)), \
             patch.object(QMessageBox, "warning"), patch.object(QMessageBox, "information"), \
             patch("logic.instrumental_import.import_instrumental") as ingest:
            panel.on_demucs_completed()
        ingest.assert_not_called()

    def test_artwork_skip_does_not_advance_when_state_save_fails(self):
        panel = Step6ArtworkPanel(self.config, self.workflow)
        panel.album_folder = str(self.album)
        self.workflow.state.state["hasArtwork"] = False
        completed = Mock()
        panel.step_completed.connect(completed)
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
             patch.object(QMessageBox, "warning"), patch.object(self.workflow.state, "save", return_value=False):
            panel.on_complete()
        completed.assert_not_called()

    def test_failed_second_image_does_not_mix_old_and_new_covers(self):
        output = self.album / "_artwork_resized"
        output.mkdir()
        for extension in ["jpg", "webp"]:
            (output / f"cover.{extension}").write_bytes(b"old")
        def resize(tool, source, destination, **kwargs):
            Path(destination).write_bytes(b"new")
            return (True, "") if kwargs["format"] == "jpg" else (False, "webp failed")
        with patch("logic.artwork_handler.resize_artwork_with_magick", side_effect=resize):
            self.assertFalse(ensure_artwork_resized_outputs(str(self.album), "magick.exe", "cover.png")[0])
        for extension in ["jpg", "webp"]:
            self.assertEqual((output / f"cover.{extension}").read_bytes(), b"old")

    def test_artwork_embedding_failure_blocks_completion(self):
        output = self.album / "_artwork_resized"
        output.mkdir()
        for extension in ["jpg", "webp"]:
            (output / f"cover.{extension}").write_bytes(b"cover")
        aac = self.album / "_aac_output/Artist/Album"
        aac.mkdir(parents=True)
        (aac / "01 Song.m4a").write_bytes(b"audio")
        panel = Step6ArtworkPanel(self.config, self.workflow)
        panel.album_folder = str(self.album)
        completed = Mock()
        panel.step_completed.connect(completed)
        with patch("logic.artwork_handler.embed_artwork_to_mp4", return_value=(False, "locked")), \
             patch.object(QMessageBox, "warning"), patch.object(QMessageBox, "information"):
            panel.on_complete()
        completed.assert_not_called()
        self.assertFalse(self.workflow.state.is_step_completed("step6_artwork"))

    def test_demucs_same_folder_prefers_flac_and_excludes_isolated_files(self):
        song = self.audio / "01 Song"
        ignored = self.audio / "demucs_ignore/02 Song"
        for folder in [song, ignored]:
            folder.mkdir(parents=True)
            for name in ["no_vocals.wav", "no_vocals.flac"]:
                (folder / name).write_bytes(b"audio")
        self.assertEqual(extract_instrumental_files(str(self.audio)), [(str(song), str(song / "no_vocals.flac"))])

    def test_manual_dialog_edit_does_not_mutate_live_state(self):
        tracks = [{"id": "1", "originalFile": "Song.flac", "currentFile": "old.flac"}]
        dialog = ManualMappingDialog(tracks, ["old.flac", "new.flac"])
        dialog.table.cellWidget(0, 1).setCurrentText("new.flac")
        self.assertEqual(dialog.get_updated_tracks()[0]["currentFile"], "new.flac")
        self.assertEqual(tracks[0]["currentFile"], "old.flac")

    def test_manual_dialog_rejects_duplicate_assignments(self):
        dialog = ManualMappingDialog([{"id": "1"}, {"id": "2"}], ["Song.flac"])
        for row in [0, 1]:
            dialog.table.cellWidget(row, 1).setCurrentText("Song.flac")
        with patch.object(QMessageBox, "warning"):
            dialog.accept()
        self.assertNotEqual(dialog.result(), QDialog.DialogCode.Accepted)

    def test_existing_instrumental_manual_mapping_is_preserved(self):
        tracks = self.rescan([{"id": "1", "originalFile": "01 Old (Inst).flac", "currentFile": "09 New (Inst).flac"}],
                             ["01 Old (Inst).flac", "09 New (Inst).flac"])
        self.assertEqual(tracks[0]["currentFile"], "09 New (Inst).flac")

    def test_second_cover_publish_failure_rolls_back_first_cover(self):
        output = self.album / "_artwork_resized"
        output.mkdir()
        for extension in ["jpg", "webp"]:
            (output / f"cover.{extension}").write_bytes(b"old")
        def resize(tool, source, destination, **kwargs):
            Path(destination).write_bytes(b"new")
            return True, ""
        replace = os.replace
        def publish(source, destination):
            if Path(source).name == "cover.webp":
                raise OSError("locked")
            return replace(source, destination)
        with patch("logic.artwork_handler.resize_artwork_with_magick", side_effect=resize), \
             patch("logic.artwork_handler.os.replace", side_effect=publish):
            self.assertFalse(ensure_artwork_resized_outputs(str(self.album), "magick", "source")[0])
        for extension in ["jpg", "webp"]:
            self.assertEqual((output / f"cover.{extension}").read_bytes(), b"old")

    def test_both_covers_published_after_success(self):
        def resize(tool, source, destination, **kwargs):
            Path(destination).write_bytes(kwargs["format"].encode())
            return True, ""
        with patch("logic.artwork_handler.resize_artwork_with_magick", side_effect=resize):
            ok, jpg, webp = ensure_artwork_resized_outputs(str(self.album), "magick", "source")
        self.assertTrue(ok)
        self.assertEqual(Path(jpg).read_bytes(), b"jpg")
        self.assertEqual(Path(webp).read_bytes(), b"webp")

    def test_existing_instrumental_owner_is_not_stolen_by_earlier_track(self):
        tracks = self.rescan([
            {"id": "1", "originalFile": "01 Song.flac"},
            {"id": "2", "originalFile": "02 Song.flac", "currentInstFile": "03 Song (Inst).flac"},
        ], ["01 Song.flac", "02 Song.flac", "03 Song (Inst).flac"])
        self.assertFalse(tracks[0].get("hasInstrumental"))
        self.assertEqual(tracks[1].get("currentInstFile"), "03 Song (Inst).flac")

    def test_unique_minor_typo_can_still_match(self):
        tracks = self.rescan([{"id": "1", "originalFile": "01 Sunshinee.flac"}], ["01 Sunshine.flac"])
        self.assertEqual(tracks[0].get("currentFile"), "01 Sunshine.flac")

    @unittest.skipUnless(os.environ.get("RIPTAG_TEST_MAGICK") or shutil.which("magick"), "ImageMagickが必要な画像生成の統合テスト")
    def test_real_magick_generates_both_formats_from_synthetic_image(self):
        from PySide6.QtGui import QImage
        tool = os.environ.get("RIPTAG_TEST_MAGICK") or shutil.which("magick")
        source = self.album / "synthetic.png"
        image = QImage(20, 10, QImage.Format.Format_ARGB32)
        image.fill(0xff336699)
        self.assertTrue(image.save(str(source)))
        original = source.read_bytes()
        ok, jpg, webp = ensure_artwork_resized_outputs(str(self.album), tool, str(source), width=6)
        self.assertTrue(ok, jpg)
        for path in [jpg, webp]:
            size = subprocess.run([tool, "identify", "-format", "%wx%h", path], check=True, capture_output=True, text=True)
            self.assertEqual(size.stdout, "6x3")
        self.assertEqual(source.read_bytes(), original)

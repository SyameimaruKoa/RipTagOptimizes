import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

from gui.batch_process_dialog import BatchProcessWorker
from logic.state_manager import StateManager
from logic.workflow_manager import WorkflowManager
from logic.utils import sanitize_foldername
from logic.output_ingest import ingest_outputs, missing_outputs
from gui.batch_process_dialog import BatchProcessDialog
from gui.step_panels.step7_transfer import Step7TransferPanel


class RegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.album = Path(self.temp.name) / "Album"
        self.album.mkdir()
        self.state = StateManager(str(self.album))
        self.state.initialize("Album", "Artist", ["01 Song.flac"])
        self.workflow = WorkflowManager(Mock())
        self.workflow.load_album(str(self.album))

    def test_failed_state_save_preserves_previous_json(self):
        before = (self.album / "state.json").read_bytes()
        self.state.state["invalid"] = object()
        self.assertFalse(self.state.save())
        self.assertEqual((self.album / "state.json").read_bytes(), before)

    def test_completion_reports_save_failure(self):
        self.workflow.state.state["currentStep"] = 7
        with patch.object(self.workflow.state, "save", return_value=False):
            self.assertFalse(self.workflow.advance_step())

    def test_batch_step7_only_prepares_and_preserves_files(self):
        src = self.album / "_flac_src" / "Album"
        src.mkdir(parents=True)
        (src / "01 Song.flac").write_bytes(b"audio")
        self.workflow.state.set_current_step(7)
        worker = BatchProcessWorker([], Mock())
        with patch("send2trash.send2trash") as trash:
            self.assertTrue(worker._process_step7(self.workflow, str(self.album), "Album"))
            trash.assert_not_called()
        self.assertNotEqual(self.workflow.state.get_status(), "COMPLETED")
        self.assertFalse(self.workflow.state.is_step_completed("step7_transfer"))
        self.assertEqual((self.album / "_final_flac/Artist/Album/01 Song.flac").read_bytes(), b"audio")

    def test_batch_step7_missing_audio_is_failure(self):
        self.workflow.state.set_current_step(7)
        worker = BatchProcessWorker([], Mock())
        with patch("send2trash.send2trash"):
            self.assertFalse(worker._process_step7(self.workflow, str(self.album), "Album"))

    def test_windows_quote_is_sanitized(self):
        self.assertNotIn('"', sanitize_foldername('An "Album"'))

    def test_failed_replace_preserves_state_and_removes_temporary(self):
        before = (self.album / "state.json").read_bytes()
        with patch("logic.state_manager.os.replace", side_effect=OSError("disk error")):
            self.assertFalse(self.state.set_current_step(5))
        self.assertEqual((self.album / "state.json").read_bytes(), before)
        self.assertEqual(list(self.album.glob(".state-*.tmp")), [])

    def test_state_saves_valid_json(self):
        self.assertTrue(self.state.set_current_step(5))
        self.assertEqual(json.loads((self.album / "state.json").read_text(encoding="utf-8"))["currentStep"], 5)

    def test_bad_root_and_failed_album_load_are_rejected(self):
        (self.album / "state.json").write_text("[]", encoding="utf-8")
        self.assertFalse(self.workflow.load_album(str(self.album)))
        self.assertIsNone(self.workflow.state)

    def test_rollback_clears_actual_completion_keys(self):
        state = self.workflow.state
        state.state.update(currentStep=6, status="ERROR", lastError={"message": "oops"})
        state.state["completedSteps"] = {"step4_aac": True, "step5_opus": True, "step6_artwork": True, "step7_transfer": True}
        self.assertTrue(self.workflow.rollback_step())
        self.assertEqual(state.get_current_step(), 5)
        self.assertEqual(state.state["completedSteps"], {"step4_aac": True})
        self.assertEqual(state.get_status(), "WAITING_USER")

    def test_rollback_failure_restores_memory(self):
        self.workflow.state.set_current_step(6)
        with patch.object(self.workflow.state, "save", return_value=False):
            self.assertFalse(self.workflow.rollback_step())
        self.assertEqual(self.workflow.get_current_step(), 6)

    def test_rollback_from_step7_restores_audio_for_previous_steps(self):
        self.workflow.state.set_current_step(7)
        final = self.album / "_final_flac/Artist/Album"
        final.mkdir(parents=True)
        (final / "01 Song.flac").write_bytes(b"audio")
        self.assertTrue(self.workflow.rollback_step())
        self.assertEqual((self.album / "_flac_src/Album/01 Song.flac").read_bytes(), b"audio")
        self.assertFalse(final.exists())

    def test_rollback_save_failure_restores_audio_location(self):
        self.workflow.state.set_current_step(7)
        final = self.album / "_final_flac/Artist/Album"
        final.mkdir(parents=True)
        (final / "01 Song.flac").write_bytes(b"audio")
        with patch.object(self.workflow.state, "save", return_value=False):
            self.assertFalse(self.workflow.rollback_step())
        self.assertEqual((final / "01 Song.flac").read_bytes(), b"audio")
        self.assertFalse((self.album / "_flac_src/Album").exists())

    def test_main_window_constructs_all_panels_with_temporary_config(self):
        from gui.main_window import MainWindow
        from logic.config_manager import ConfigManager
        config_path = Path(self.temp.name) / "test.ini"
        config_path.write_text(f"[Paths]\nWorkDir = {self.temp.name}\n", encoding="utf-8")
        config = ConfigManager(str(config_path))
        with patch("gui.main_window.ConfigManager", return_value=config):
            window = MainWindow()
        try:
            window.refresh_timer.stop()
            self.assertEqual(window.step_stack.count(), 8)
            self.assertEqual(window.album_list.count(), 1)
            window.on_album_selected(window.album_list.item(0), None)
            self.assertEqual(window.workflow.get_current_step(), 1)
        finally:
            window.deleteLater()
            self.app.processEvents()

    def test_batch_runs_only_checked_steps(self):
        self.state.set_current_step(4)
        worker = BatchProcessWorker([str(self.album)], Mock(), steps=[4, 6])
        with patch.object(worker, "_process_step4", return_value=True) as aac, \
             patch.object(worker, "_process_step5", return_value=True) as opus, \
             patch.object(worker, "_process_step6", return_value=True) as art:
            worker.run()
        aac.assert_called_once()
        opus.assert_not_called()
        art.assert_called_once()
        self.state.load()
        self.assertEqual(self.state.get_current_step(), 5)

    def test_stop_prevents_next_step(self):
        self.state.set_current_step(4)
        worker = BatchProcessWorker([str(self.album)], Mock(), steps=[4, 5])
        def stop_after_step(*args):
            worker.stop()
            return True
        with patch.object(worker, "_process_step4", side_effect=stop_after_step), \
             patch.object(worker, "_process_step5") as opus:
            worker.run()
        opus.assert_not_called()

    def test_dialog_reject_waits_for_worker(self):
        dialog = BatchProcessDialog([], Mock())
        dialog.worker = Mock()
        dialog.worker.isRunning.return_value = True
        dialog.reject()
        dialog.worker.stop.assert_called_once()

    def test_step7_conflicting_folders_preserves_both(self):
        self.workflow.state.set_current_step(7)
        src = self.album / "_flac_src/Album"
        dst = self.album / "_final_flac/Artist/Album"
        for folder, data in [(src, b"source"), (dst, b"final")]:
            folder.mkdir(parents=True)
            (folder / "01 Song.flac").write_bytes(data)
        self.assertFalse(BatchProcessWorker([], Mock())._process_step7(self.workflow, str(self.album), "Album"))
        self.assertEqual((src / "01 Song.flac").read_bytes(), b"source")
        self.assertEqual((dst / "01 Song.flac").read_bytes(), b"final")

    def test_trash_failure_keeps_work_and_does_not_signal_completion(self):
        panel = Step7TransferPanel(Mock(), self.workflow)
        panel.album_folder = str(self.album)
        completed = Mock()
        panel.step_completed.connect(completed)
        from PySide6.QtWidgets import QMessageBox
        with patch("send2trash.send2trash", side_effect=OSError("busy")), \
             patch.object(QMessageBox, "question", return_value=QMessageBox.Yes), \
             patch.object(QMessageBox, "warning"):
            panel.on_complete()
        self.assertTrue((self.album / "state.json").exists())
        completed.assert_not_called()

    def test_batch_embedding_failure_does_not_complete_step(self):
        cfg = Mock()
        cfg.get_tool_path.return_value = __file__
        cfg.get_setting.side_effect = lambda key, default=None: default
        worker = BatchProcessWorker([], cfg)
        dst = self.album / "_aac_output/Artist/Album"
        dst.mkdir(parents=True)
        (dst / "01 Song.m4a").write_bytes(b"aac")
        with patch("logic.artwork_handler.find_first_flac_with_artwork", return_value="audio.flac"), \
             patch("logic.artwork_handler.extract_artwork_from_flac", return_value=True), \
             patch("logic.artwork_handler.ensure_artwork_resized_outputs", return_value=(True, "cover.jpg", "cover.webp")), \
             patch("logic.artwork_handler.embed_artwork_to_mp4", return_value=(False, "bad audio")):
            self.assertFalse(worker._process_step6(self.workflow, str(self.album), "Album"))
        self.assertFalse(self.workflow.state.is_step_completed("step6_artwork"))

    def test_batch_does_not_accept_partial_unnumbered_outputs(self):
        self.workflow.state.state["tracks"] = [{"finalFile": "First.flac"}, {"finalFile": "Second.flac"}]
        external = Path(self.temp.name) / "external"
        source = external / "aac/Artist/Album"
        source.mkdir(parents=True)
        (source / "First.m4a").write_bytes(b"audio")
        cfg = Mock()
        cfg.get_setting.return_value = str(external)
        cfg.expand_path.side_effect = lambda path: path
        cfg.get_directory_name.return_value = "aac"
        worker = BatchProcessWorker([], cfg)
        self.assertFalse(worker._process_step4(self.workflow, str(self.album), "Album"))
        self.assertFalse(self.workflow.state.is_step_completed("step4_aac"))
        (source / "Second.m4a").write_bytes(b"audio2")
        self.assertTrue(worker._process_step4(self.workflow, str(self.album), "Album"))
        self.assertTrue(self.workflow.state.is_step_completed("step4_aac"))

    def test_freefilesync_uses_paths_setting(self):
        cfg = Mock()
        settings_file = self.album / "sync.ffs_gui"
        settings_file.write_text("config", encoding="utf-8")
        cfg.get_tool_path.side_effect = lambda key: str(settings_file) if key == "FreeFileSync_Config" else __file__
        cfg.expand_path.side_effect = lambda path: path
        panel = Step7TransferPanel(cfg, self.workflow)
        with patch("gui.step_panels.step7_transfer.subprocess.Popen") as launch:
            panel.on_launch_freefilesync()
        launch.assert_called_once_with([__file__, str(settings_file)])

    def test_discard_rejects_work_root_and_prefix_sibling(self):
        from gui.main_window import MainWindow
        root = Path(self.temp.name) / "work"
        sibling = Path(self.temp.name) / "work-backup"
        root.mkdir()
        sibling.mkdir()
        window = Mock()
        window.config.get_directory.return_value = str(root)
        from PySide6.QtWidgets import QMessageBox
        for target in [root, sibling]:
            with self.subTest(target=target):
                window.album_list.currentItem.return_value.data.return_value = str(target)
                with patch.object(QMessageBox, "critical"), patch.object(QMessageBox, "question") as question, \
                     patch("gui.main_window.send2trash") as trash:
                    MainWindow.on_discard_album(window)
                question.assert_not_called()
                trash.assert_not_called()

    def test_manual_aac_and_opus_panels_use_safe_ingest(self):
        from gui.step_panels.step4_aac import Step4AacPanel
        from gui.step_panels.step5_opus import Step5OpusPanel
        from PySide6.QtWidgets import QFileDialog
        for cls, method, extension, folder in [
            (Step4AacPanel, "on_ingest_outputs", ".m4a", "_aac_output"),
            (Step5OpusPanel, "on_ingest", ".opus", "_opus_output")
        ]:
            with self.subTest(extension=extension):
                source = Path(self.temp.name) / extension[1:]
                source.mkdir()
                (source / ("01 Song" + extension)).write_bytes(b"audio")
                panel = cls(Mock(), self.workflow)
                panel.album_folder = str(self.album)
                with patch.object(QFileDialog, "getExistingDirectory", return_value=str(source)):
                    getattr(panel, method)(str(source))
                output = self.album / folder / "Artist/Album" / ("01 Song" + extension)
                self.assertEqual(output.read_bytes(), b"audio")


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.src = Path(self.temp.name) / "source"
        self.dst = Path(self.temp.name) / "destination"
        self.src.mkdir()
        self.dst.mkdir()

    def test_multidisc_tracks_are_not_overwritten(self):
        for extension in [".m4a", ".opus"]:
            with self.subTest(extension=extension):
                tracks = [{"finalFile": f"Disc {disc}-01 Title.flac"} for disc in [1, 2]]
                for disc in [1, 2]:
                    (self.src / f"Disc {disc}-01 Converted{extension}").write_bytes(bytes([disc]))
                count, errors = ingest_outputs(str(self.src), str(self.dst), tracks, extension)
                self.assertEqual((count, errors), (2, []))
                for disc in [1, 2]:
                    self.assertEqual((self.dst / f"Disc {disc}-01 Title{extension}").read_bytes(), bytes([disc]))

    def test_missing_disc_is_ambiguous(self):
        tracks = [{"finalFile": f"Disc {disc}-01 Title.flac"} for disc in [1, 2]]
        (self.src / "01 Converted.m4a").write_bytes(b"audio")
        count, errors = ingest_outputs(str(self.src), str(self.dst), tracks, ".m4a")
        self.assertEqual(count, 0)
        self.assertTrue(errors)
        self.assertTrue((self.src / "01 Converted.m4a").exists())

    def test_same_directory_does_not_delete_audio(self):
        name = "01 Song.m4a"
        (self.src / name).write_bytes(b"audio")
        count, errors = ingest_outputs(str(self.src), str(self.src), [{"finalFile": "01 Song.flac"}], ".m4a")
        self.assertEqual((count, errors), (0, []))
        self.assertEqual((self.src / name).read_bytes(), b"audio")

    def test_copy_failure_keeps_existing_destination_and_source(self):
        name = "01 Song.m4a"
        (self.src / name).write_bytes(b"new")
        (self.dst / name).write_bytes(b"old")
        with patch("logic.output_ingest.shutil.copy2", side_effect=OSError("full")):
            count, errors = ingest_outputs(str(self.src), str(self.dst), [{"finalFile": "01 Song.flac"}], ".m4a")
        self.assertEqual(count, 0)
        self.assertTrue(errors)
        self.assertEqual((self.src / name).read_bytes(), b"new")
        self.assertEqual((self.dst / name).read_bytes(), b"old")
        self.assertEqual(list(self.dst.glob(".ingest-*")), [])

    def test_duplicate_targets_are_rejected_before_moves(self):
        for name in ["01 First.m4a", "01 Second.m4a"]:
            (self.src / name).write_bytes(b"audio")
        count, errors = ingest_outputs(str(self.src), str(self.dst), [{"finalFile": "01 Song.flac"}], ".m4a")
        self.assertEqual(count, 0)
        self.assertTrue(errors)
        self.assertEqual(len(list(self.src.iterdir())), 2)

    def test_unnumbered_and_instrumental_outputs_are_counted(self):
        tracks = [{"finalFile": "Song.flac", "instrumentalFile": "Song (Inst).flac"}]
        (self.src / "Song.m4a").write_bytes(b"song")
        count, errors = ingest_outputs(str(self.src), str(self.dst), tracks, ".m4a")
        self.assertEqual((count, errors), (1, []))
        self.assertEqual(missing_outputs(str(self.dst), tracks, ".m4a"), ["Song (Inst).m4a"])

    def test_shared_output_does_not_match_by_number(self):
        (self.src / "01 Other album.m4a").write_bytes(b"other")
        count, errors = ingest_outputs(str(self.src), str(self.dst), [{"finalFile": "01 Song.flac"}], ".m4a", allow_number_match=False)
        self.assertEqual(count, 0)
        self.assertTrue(errors)

    def test_missing_source_is_reported_without_raising(self):
        count, errors = ingest_outputs(str(self.src / "missing"), str(self.dst), [], ".m4a")
        self.assertEqual(count, 0)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()

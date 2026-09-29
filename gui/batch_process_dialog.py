"""
一括処理ダイアログ - Step4~7の自動実行
"""
import os
import shutil
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QProgressBar, QTextEdit,
    QMessageBox, QCheckBox
)
from PySide6.QtCore import QThread, Signal

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager
from logic.log_manager import get_logger


class BatchProcessWorker(QThread):
    """一括処理ワーカースレッド"""
    progress = Signal(int, int, str)  # current, total, message
    album_completed = Signal(str, bool, str)  # album_name, success, error_msg
    all_completed = Signal(int, int)  # success_count, fail_count
    
    def __init__(self, album_folders, config, start_step=4, end_step=7, *, steps=None):
        super().__init__()
        self.album_folders = album_folders
        self.config = config
        self.start_step = start_step
        self.end_step = end_step
        self.steps = sorted(set(steps if steps is not None else range(start_step, end_step + 1)))
        self.should_stop = False
    
    def stop(self):
        """処理を停止"""
        self.should_stop = True
    
    def run(self):
        success_count = 0
        fail_count = 0
        for idx, album_folder in enumerate(self.album_folders):
            if self.should_stop:
                break
            album_name = os.path.basename(album_folder)
            self.progress.emit(idx, len(self.album_folders), f"処理中: {album_name}")
            workflow = WorkflowManager(self.config)
            if not workflow.load_album(album_folder):
                self.album_completed.emit(album_name, False, "アルバム読み込み失敗")
                fail_count += 1
                continue
            logger = get_logger()
            logger.set_album_folder(album_folder)
            try:
                if workflow.get_current_step() < 4 or workflow.state.get_status() == "COMPLETED":
                    raise ValueError("Step 4以降の未完了アルバムを選択してください")
                for step in self.steps:
                    if self.should_stop:
                        break
                    if not getattr(self, f"_process_step{step}")(workflow, album_folder, album_name):
                        raise RuntimeError(f"Step {step} の処理に失敗しました。ログを確認してください")
                    # Step 7は転送準備のみ。外部転送完了はユーザーが確認する。
                    if step < 7 and workflow.get_current_step() == step:
                        if not workflow.advance_step():
                            raise RuntimeError("進捗の保存に失敗しました")
                if self.should_stop:
                    break
                self.album_completed.emit(album_name, True, "")
                success_count += 1
                logger.info("batch", f"一括処理完了: {album_name}")
            except Exception as e:
                self.album_completed.emit(album_name, False, f"予期しないエラー: {e}")
                fail_count += 1
                logger.error("batch", f"予期しないエラー: {album_name} - {e}")
        self.all_completed.emit(success_count, fail_count)

    def _process_step4(self, workflow, album_folder, album_name):
        return self._ingest(workflow, album_folder, ".m4a", "aac_output", "aacOutput", "step4_aac")

    def _process_step5(self, workflow, album_folder, album_name):
        return self._ingest(workflow, album_folder, ".opus", "opus_output", "opusOutput", "step5_opus")

    def _ingest(self, workflow, album_folder, extension, directory_key, path_key, step_key):
        from logic.output_ingest import expected_outputs, ingest_outputs, missing_outputs
        from logic.utils import sanitize_foldername
        state = workflow.state
        tracks = state.get_tracks()
        if not expected_outputs(tracks, extension):
            return False
        album = sanitize_foldername(state.get_album_name())
        artist = sanitize_foldername(state.get_artist_name())
        dst = os.path.join(album_folder, state.get_path(path_key), artist, album)
        if not missing_outputs(dst, tracks, extension):
            return state.mark_step_completed(step_key)
        ext_dir = self.config.get_setting("ExternalOutputDir")
        folder_name = self.config.get_directory_name(directory_key)
        if not ext_dir or not folder_name:
            return False
        base = os.path.join(self.config.expand_path(ext_dir), folder_name)
        for src in [os.path.join(base, artist, album), os.path.join(base, album), base]:
            if not os.path.isdir(src):
                continue
            if not any(f.lower().endswith(extension) for f in os.listdir(src)):
                continue
            _, errors = ingest_outputs(src, dst, tracks, extension, allow_number_match=(src != base))
            for error in errors:
                get_logger().error("batch", error)
            if errors or missing_outputs(dst, tracks, extension):
                return False
            return state.mark_step_completed(step_key)
        return False

    def _process_step6(self, workflow, album_folder, album_name):
        if workflow.state.is_step_completed("step6_artwork"):
            return True
        import logic.artwork_handler as ah
        album_name = workflow.state.get_album_name()
        flac_path = ah.find_first_flac_with_artwork(album_folder, album_name)
        if not flac_path:
            return workflow.state.set_artwork(False) and workflow.state.mark_step_completed("step6_artwork")
        magick = self.config.get_tool_path("Magick")
        if not magick or not os.path.exists(magick):
            return False
        tmp_cover = os.path.join(album_folder, "_cover_src.jpg")
        if not ah.extract_artwork_from_flac(flac_path, tmp_cover):
            return False
        w = int(self.config.get_setting("ResizeWidth", "600"))
        jq = int(self.config.get_setting("JpegQuality", "85"))
        wq = int(self.config.get_setting("WebpQuality", "85"))
        ok, jpg_path, webp_path = ah.ensure_artwork_resized_outputs(album_folder, magick, tmp_cover, w, jq, wq)
        if not ok:
            return False
        if not workflow.state.set_artwork(True):
            return False
        def resolve_dir(base_dir_name):
            from logic.utils import sanitize_foldername
            sa = sanitize_foldername(album_name)
            art = sanitize_foldername(workflow.state.get_artist_name())
            b_dir = os.path.join(album_folder, base_dir_name)
            for cand in [os.path.join(b_dir, art, sa), os.path.join(b_dir, sa), b_dir]:
                if os.path.isdir(cand):
                    return cand
            return os.path.join(b_dir, art, sa)
        aac_dir = resolve_dir(workflow.state.get_path("aacOutput"))
        if os.path.isdir(aac_dir):
            for n in os.listdir(aac_dir):
                if n.lower().endswith(".m4a"):
                    ok, error = ah.embed_artwork_to_mp4(os.path.join(aac_dir, n), jpg_path)
                    if not ok:
                        get_logger().error("batch", f"{n}: {error}")
                        return False
        opus_dir = resolve_dir(workflow.state.get_path("opusOutput"))
        if os.path.isdir(opus_dir):
            for n in os.listdir(opus_dir):
                if n.lower().endswith(".opus"):
                    ok, error = ah.embed_artwork_to_opus(os.path.join(opus_dir, n), webp_path)
                    if not ok:
                        get_logger().error("batch", f"{n}: {error}")
                        return False
        return workflow.state.mark_step_completed("step6_artwork")

    def _process_step7(self, workflow, album_folder, album_name):
        """転送用フォルダを準備する。転送や作業フォルダの削除は行わない。"""
        if workflow.get_current_step() != 7:
            return False
        from logic.utils import sanitize_foldername
        sa = sanitize_foldername(workflow.state.get_album_name())
        art = sanitize_foldername(workflow.state.get_artist_name())
        flac_src = os.path.join(album_folder, "_flac_src", sa)
        final_flac = os.path.join(album_folder, "_final_flac", art, sa)
        if os.path.exists(flac_src) and os.path.exists(final_flac):
            get_logger().error("batch", "移動元と最終FLACフォルダが両方存在します。確認してください")
            return False
        if os.path.isdir(flac_src):
            if not any(n.lower().endswith(".flac") for n in os.listdir(flac_src)):
                return False
            os.makedirs(os.path.dirname(final_flac), exist_ok=True)
            shutil.move(flac_src, final_flac)
        if not os.path.isdir(final_flac):
            return False
        if not any(n.lower().endswith(".flac") for n in os.listdir(final_flac)):
            return False
        playlist = os.path.join(final_flac, "_mp3tag_target.m3u8")
        if os.path.isfile(playlist):
            os.remove(playlist)
        return True



class BatchProcessDialog(QDialog):
    """一括処理ダイアログ"""
    
    def __init__(self, album_folders, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.album_folders = album_folders
        self.config = config
        self.worker = None
        
        self.setWindowTitle("一括処理 (Step4~7)")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel("<h2>🔄 一括処理 (Step4~7)</h2>")
        layout.addWidget(title)
        
        # 説明
        desc = QLabel(
            f"選択された {len(self.album_folders)} 個のアルバムを順次処理します。\n"
            "チェックしたステップを実行します。\n"
            "Step 7は転送準備のみです。転送と作業フォルダの整理は、後で個別に完了してください。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # ステップ選択
        step_layout = QHBoxLayout()
        step_layout.addWidget(QLabel("処理範囲:"))
        
        self.step4_check = QCheckBox("Step4 (AAC)")
        self.step4_check.setChecked(True)
        step_layout.addWidget(self.step4_check)
        
        self.step5_check = QCheckBox("Step5 (Opus)")
        self.step5_check.setChecked(True)
        step_layout.addWidget(self.step5_check)
        
        self.step6_check = QCheckBox("Step6 (Artwork)")
        self.step6_check.setChecked(True)
        step_layout.addWidget(self.step6_check)
        
        self.step7_check = QCheckBox("Step7 (準備)")
        self.step7_check.setChecked(False)
        step_layout.addWidget(self.step7_check)
        
        step_layout.addStretch()
        layout.addLayout(step_layout)
        
        layout.addSpacing(10)
        
        # プログレスバー
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(len(self.album_folders))
        layout.addWidget(self.progress_bar)
        
        # 進捗ラベル
        self.progress_label = QLabel("待機中...")
        layout.addWidget(self.progress_label)
        
        # ログ表示
        layout.addWidget(QLabel("<b>処理ログ:</b>"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        layout.addWidget(self.log_text)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("開始")
        self.start_button.setMinimumHeight(35)
        self.start_button.clicked.connect(self.on_start)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("停止")
        self.stop_button.setMinimumHeight(35)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.on_stop)
        button_layout.addWidget(self.stop_button)
        
        self.close_button = QPushButton("閉じる")
        self.close_button.setMinimumHeight(35)
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def on_start(self):
        """処理を開始"""
        # ステップ範囲を取得
        steps = []
        if self.step4_check.isChecked():
            steps.append(4)
        if self.step5_check.isChecked():
            steps.append(5)
        if self.step6_check.isChecked():
            steps.append(6)
        if self.step7_check.isChecked():
            steps.append(7)
        
        if not steps:
            QMessageBox.warning(self, "エラー", "処理するステップを選択してください。")
            return
        
        start_step = min(steps)
        end_step = max(steps)
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.close_button.setEnabled(False)
        
        # ワーカースレッド起動
        self.worker = BatchProcessWorker(self.album_folders, self.config, start_step, end_step, steps=steps)
        self.worker.progress.connect(self.on_progress)
        self.worker.album_completed.connect(self.on_album_completed)
        self.worker.all_completed.connect(self.on_all_completed)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()
        
        self.log_text.append(f"=== 一括処理開始 ({len(self.album_folders)}アルバム) ===")
    
    def on_stop(self):
        """処理を停止"""
        if self.worker:
            self.worker.stop()
            self.log_text.append("\n[停止要求] 処理を中断しています...")
    
    def on_progress(self, current, total, message):
        """進捗更新"""
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{message} ({current + 1}/{total})")
    
    def on_album_completed(self, album_name, success, error_msg):
        """アルバム処理完了"""
        if success:
            self.log_text.append(f"✅ {album_name}: 完了")
        else:
            self.log_text.append(f"❌ {album_name}: {error_msg}")
    
    def on_all_completed(self, success_count, fail_count):
        """全処理完了"""
        self.progress_bar.setValue(success_count + fail_count)
        stopped = self.worker is not None and self.worker.should_stop
        self.progress_label.setText("停止しました" if stopped else "処理完了")
        
        result_label = "停止しました" if stopped else "処理完了"
        self.log_text.append(f"\n=== {result_label} ===")
        self.log_text.append(f"成功: {success_count} / 失敗: {fail_count}")
        QMessageBox.information(
            self,
            result_label,
            f"{result_label}\n\n成功: {success_count}\n失敗: {fail_count}"
        )

    def on_worker_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.close_button.setEnabled(True)

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.on_stop()
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.on_stop()
            event.ignore()
            return
        super().closeEvent(event)

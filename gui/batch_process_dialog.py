"""
一括処理ダイアログ - Step4~7の自動実行
"""
import os
import shutil
import re
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
    
    def __init__(self, album_folders, config, start_step=4, end_step=7):
        super().__init__()
        self.album_folders = album_folders
        self.config = config
        self.start_step = start_step
        self.end_step = end_step
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
                if self.start_step <= 4 <= self.end_step:
                    if not self._process_step4(workflow, album_folder, album_name):
                        self.album_completed.emit(album_name, False, "Step4 AAC変換失敗")
                        fail_count += 1
                        logger.error("batch", f"Step4失敗: {album_name}")
                        continue
                    if workflow.get_current_step() == 4:
                        workflow.advance_step()
                if self.start_step <= 5 <= self.end_step:
                    if not self._process_step5(workflow, album_folder, album_name):
                        self.album_completed.emit(album_name, False, "Step5 Opus変換失敗")
                        fail_count += 1
                        logger.error("batch", f"Step5失敗: {album_name}")
                        continue
                    if workflow.get_current_step() == 5:
                        workflow.advance_step()
                if self.start_step <= 6 <= self.end_step:
                    if not self._process_step6(workflow, album_folder, album_name):
                        self.album_completed.emit(album_name, False, "Step6 Artwork最適化失敗")
                        fail_count += 1
                        logger.error("batch", f"Step6失敗: {album_name}")
                        continue
                    if workflow.get_current_step() == 6:
                        workflow.advance_step()
                if self.start_step <= 7 <= self.end_step:
                    if not self._process_step7(workflow, album_folder, album_name):
                        self.album_completed.emit(album_name, False, "Step7 転送失敗")
                        fail_count += 1
                        logger.error("batch", f"Step7失敗: {album_name}")
                        continue
                    if workflow.get_current_step() == 7:
                        workflow.advance_step()
                self.album_completed.emit(album_name, True, "")
                success_count += 1
                logger.info("batch", f"一括処理完了: {album_name}")
            except Exception as e:
                self.album_completed.emit(album_name, False, f"予期しないエラー: {e}")
                fail_count += 1
                logger.error("batch", f"予期しないエラー: {album_name} - {e}")
        self.all_completed.emit(success_count, fail_count)

    def _process_step4(self, workflow, album_folder, album_name):
        if workflow.state.is_step_completed("step4_aac"):
            return True
        ext_dir = self.config.get_setting("ExternalOutputDir")
        aac_name = self.config.get_directory_name("aac_output")
        if not ext_dir or not aac_name:
            return False
        ext_dir = self.config.expand_path(ext_dir)
        cand_base = os.path.join(ext_dir, aac_name)
        artist_name = workflow.state.get_artist_name()
        from logic.utils import sanitize_foldername
        sanitized_album = sanitize_foldername(album_name)
        sanitized_artist = sanitize_foldername(artist_name)
        candidates = [
            os.path.join(cand_base, sanitized_artist, sanitized_album),
            os.path.join(cand_base, sanitized_album),
            cand_base
        ]
        src_dir = None
        for c in candidates:
            if os.path.isdir(c) and [f for f in os.listdir(c) if f.lower().endswith(".m4a")]:
                src_dir = c
                break
        if not src_dir:
            return False
        aac_dir_name = workflow.state.get_path("aacOutput")
        dst_base = os.path.join(album_folder, aac_dir_name)
        dst = os.path.join(dst_base, sanitized_artist, sanitized_album)
        os.makedirs(dst, exist_ok=True)
        tracks = workflow.state.get_tracks()
        expected = {}
        for t in tracks:
            ff = t.get("finalFile")
            inst = t.get("instrumentalFile")
            if ff:
                m = re.match(r"^(?:Disc \d+-)?(\d+)", ff)
                if m:
                    expected[str(int(m.group(1))).zfill(2)] = os.path.splitext(ff)[0] + ".m4a"
            if inst:
                m = re.match(r"^(?:Disc \d+-)?(\d+)", inst)
                if m:
                    expected[str(int(m.group(1))).zfill(2) + "_inst"] = os.path.splitext(inst)[0] + ".m4a"
        for name in os.listdir(src_dir):
            if name.lower().endswith(".m4a"):
                src_file = os.path.join(src_dir, name)
                m = re.match(r"^(?:Disc \d+-)?(\d+)", name)
                if m:
                    t_num = str(int(m.group(1))).zfill(2)
                    is_inst = any(k in name.lower() for k in ["(inst)", "instrumental", "off vocal", "off-vocal", "offvocal", "backing track", "karaoke"])
                    k = t_num + "_inst" if is_inst else t_num
                    exp_name = expected.get(k)
                    dst_file = os.path.join(dst, exp_name if exp_name else name)
                else:
                    dst_file = os.path.join(dst, name)
                try:
                    if os.path.exists(dst_file):
                        os.remove(dst_file)
                    shutil.move(src_file, dst_file)
                except Exception:
                    pass
        got = len([f for f in os.listdir(dst) if f.lower().endswith(".m4a")])
        if got < len(expected):
            return False
        workflow.state.mark_step_completed("step4_aac")
        return True

    def _process_step5(self, workflow, album_folder, album_name):
        if workflow.state.is_step_completed("step5_opus"):
            return True
        ext_dir = self.config.get_setting("ExternalOutputDir")
        opus_name = self.config.get_directory_name("opus_output")
        if not ext_dir or not opus_name:
            return False
        ext_dir = self.config.expand_path(ext_dir)
        cand_base = os.path.join(ext_dir, opus_name)
        artist_name = workflow.state.get_artist_name()
        from logic.utils import sanitize_foldername
        sanitized_album = sanitize_foldername(album_name)
        sanitized_artist = sanitize_foldername(artist_name)
        candidates = [
            os.path.join(cand_base, sanitized_artist, sanitized_album),
            os.path.join(cand_base, sanitized_album),
            cand_base
        ]
        src_dir = None
        for c in candidates:
            if os.path.isdir(c) and [f for f in os.listdir(c) if f.lower().endswith(".opus")]:
                src_dir = c
                break
        if not src_dir:
            return False
        opus_dir_name = workflow.state.get_path("opusOutput")
        dst_base = os.path.join(album_folder, opus_dir_name)
        dst = os.path.join(dst_base, sanitized_artist, sanitized_album)
        os.makedirs(dst, exist_ok=True)
        tracks = workflow.state.get_tracks()
        expected = {}
        for t in tracks:
            ff = t.get("finalFile")
            inst = t.get("instrumentalFile")
            if ff:
                m = re.match(r"^(?:Disc \d+-)?(\d+)", ff)
                if m:
                    expected[str(int(m.group(1))).zfill(2)] = os.path.splitext(ff)[0] + ".opus"
            if inst:
                m = re.match(r"^(?:Disc \d+-)?(\d+)", inst)
                if m:
                    expected[str(int(m.group(1))).zfill(2) + "_inst"] = os.path.splitext(inst)[0] + ".opus"
        for name in os.listdir(src_dir):
            if name.lower().endswith(".opus"):
                src_file = os.path.join(src_dir, name)
                m = re.match(r"^(?:Disc \d+-)?(\d+)", name)
                if m:
                    t_num = str(int(m.group(1))).zfill(2)
                    is_inst = any(k in name.lower() for k in ["(inst)", "instrumental", "off vocal", "off-vocal", "offvocal", "backing track", "karaoke"])
                    k = t_num + "_inst" if is_inst else t_num
                    exp_name = expected.get(k)
                    dst_file = os.path.join(dst, exp_name if exp_name else name)
                else:
                    dst_file = os.path.join(dst, name)
                try:
                    if os.path.exists(dst_file):
                        os.remove(dst_file)
                    shutil.move(src_file, dst_file)
                except Exception:
                    pass
        got = len([f for f in os.listdir(dst) if f.lower().endswith(".opus")])
        if got < len(expected):
            return False
        workflow.state.mark_step_completed("step5_opus")
        return True

    def _process_step6(self, workflow, album_folder, album_name):
        if workflow.state.is_step_completed("step6_artwork"):
            return True
        magick = self.config.get_tool_path("Magick")
        if not magick or not os.path.exists(magick):
            return False
        import logic.artwork_handler as ah
        flac_path = ah.find_first_flac_with_artwork(album_folder, album_name)
        if not flac_path:
            workflow.state.mark_step_completed("step6_artwork")
            return True
        tmp_cover = os.path.join(album_folder, "_cover_src.jpg")
        if not ah.extract_artwork_from_flac(flac_path, tmp_cover):
            return False
        w = int(self.config.get_setting("ResizeWidth", "600"))
        jq = int(self.config.get_setting("JpegQuality", "85"))
        wq = int(self.config.get_setting("WebpQuality", "85"))
        ok, jpg_path, webp_path = ah.ensure_artwork_resized_outputs(album_folder, magick, tmp_cover, w, jq, wq)
        if not ok:
            return False
        workflow.state.set_artwork(True)
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
                    ah.embed_artwork_to_mp4(os.path.join(aac_dir, n), jpg_path)
        opus_dir = resolve_dir(workflow.state.get_path("opusOutput"))
        if os.path.isdir(opus_dir):
            for n in os.listdir(opus_dir):
                if n.lower().endswith(".opus"):
                    ah.embed_artwork_to_opus(os.path.join(opus_dir, n), webp_path)
        workflow.state.mark_step_completed("step6_artwork")
        return True

    def _process_step7(self, workflow, album_folder, album_name):
        if workflow.state.is_step_completed("step7_transfer"):
            return True
        from logic.utils import sanitize_foldername
        sa = sanitize_foldername(album_name)
        art = sanitize_foldername(workflow.state.get_artist_name())
        flac_src = os.path.join(album_folder, "_flac_src", sa)
        final_flac_base = os.path.join(album_folder, "_final_flac")
        final_flac = os.path.join(final_flac_base, art, sa)
        if os.path.exists(flac_src):
            try:
                import shutil
                os.makedirs(final_flac_base, exist_ok=True)
                os.makedirs(os.path.join(final_flac_base, art), exist_ok=True)
                if os.path.exists(final_flac):
                    shutil.rmtree(final_flac)
                shutil.move(flac_src, final_flac)
                pl = os.path.join(final_flac, "_mp3tag_target.m3u8")
                if os.path.exists(pl):
                    os.remove(pl)
            except Exception:
                return False
        workflow.state.mark_step_completed("step7_transfer")
        workflow.state.set_status("COMPLETED")
        workflow.state.save()
        try:
            from send2trash import send2trash
            send2trash(album_folder)
        except Exception:
            try:
                import shutil
                shutil.rmtree(album_folder)
            except Exception:
                pass
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
            "各ステップが自動的に実行されます。"
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
        self.worker = BatchProcessWorker(self.album_folders, self.config, start_step, end_step)
        self.worker.progress.connect(self.on_progress)
        self.worker.album_completed.connect(self.on_album_completed)
        self.worker.all_completed.connect(self.on_all_completed)
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
        self.progress_bar.setValue(len(self.album_folders))
        self.progress_label.setText("処理完了")
        
        self.log_text.append(f"\n=== 処理完了 ===")
        self.log_text.append(f"成功: {success_count} / 失敗: {fail_count}")
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        QMessageBox.information(
            self,
            "完了",
            f"一括処理が完了しました。\n\n成功: {success_count}\n失敗: {fail_count}"
        )

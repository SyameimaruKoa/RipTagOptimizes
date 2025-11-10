"""
一括処理ダイアログ - Step4~7の自動実行
"""
import os
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
        """一括処理を実行"""
        success_count = 0
        fail_count = 0
        
        for idx, album_folder in enumerate(self.album_folders):
            if self.should_stop:
                break
            
            album_name = os.path.basename(album_folder)
            self.progress.emit(idx, len(self.album_folders), f"処理中: {album_name}")
            
            # ワークフローマネージャーを作成
            workflow = WorkflowManager(self.config)
            if not workflow.load_album(album_folder):
                self.album_completed.emit(album_name, False, "アルバム読み込み失敗")
                fail_count += 1
                continue
            
            # ログ設定
            logger = get_logger()
            logger.set_album_folder(album_folder)
            
            try:
                # Step 4~7を順次実行
                if self.start_step <= 4 <= self.end_step:
                    if not self._process_step4(workflow, album_folder, album_name):
                        self.album_completed.emit(album_name, False, "Step4 AAC変換失敗")
                        fail_count += 1
                        logger.error("batch", f"Step4失敗: {album_name}")
                        continue
                
                if self.start_step <= 5 <= self.end_step:
                    if not self._process_step5(workflow, album_folder, album_name):
                        self.album_completed.emit(album_name, False, "Step5 Opus変換失敗")
                        fail_count += 1
                        logger.error("batch", f"Step5失敗: {album_name}")
                        continue
                
                if self.start_step <= 6 <= self.end_step:
                    if not self._process_step6(workflow, album_folder, album_name):
                        self.album_completed.emit(album_name, False, "Step6 Artwork最適化失敗")
                        fail_count += 1
                        logger.error("batch", f"Step6失敗: {album_name}")
                        continue
                
                if self.start_step <= 7 <= self.end_step:
                    if not self._process_step7(workflow, album_folder, album_name):
                        self.album_completed.emit(album_name, False, "Step7 転送失敗")
                        fail_count += 1
                        logger.error("batch", f"Step7失敗: {album_name}")
                        continue
                
                self.album_completed.emit(album_name, True, "")
                success_count += 1
                logger.info("batch", f"一括処理完了: {album_name}")
                
            except Exception as e:
                self.album_completed.emit(album_name, False, f"予期しないエラー: {e}")
                fail_count += 1
                logger.error("batch", f"予期しないエラー: {album_name} - {e}")
        
        self.all_completed.emit(success_count, fail_count)
    
    def _process_step4(self, workflow, album_folder, album_name):
        """Step4: AAC変換を実行"""
        from logic.aac_handler import AacHandler
        
        # state.jsonの確認
        if workflow.state.is_step_completed("step4_aac"):
            return True  # 既に完了済み
        
        aac_handler = AacHandler(self.config)
        flac_src = os.path.join(album_folder, "_flac_src")
        aac_dest = os.path.join(album_folder, "_aac")
        
        if not os.path.exists(flac_src):
            return False
        
        # AAC変換実行
        success = aac_handler.convert_all(flac_src, aac_dest)
        if success:
            workflow.state.mark_step_completed("step4_aac")
            return True
        return False
    
    def _process_step5(self, workflow, album_folder, album_name):
        """Step5: Opus変換を実行"""
        from logic.opus_handler import OpusHandler
        
        # state.jsonの確認
        if workflow.state.is_step_completed("step5_opus"):
            return True  # 既に完了済み
        
        opus_handler = OpusHandler(self.config)
        flac_src = os.path.join(album_folder, "_flac_src")
        opus_dest = os.path.join(album_folder, "_opus")
        
        if not os.path.exists(flac_src):
            return False
        
        # Opus変換実行
        success = opus_handler.convert_all(flac_src, opus_dest)
        if success:
            workflow.state.mark_step_completed("step5_opus")
            return True
        return False
    
    def _process_step6(self, workflow, album_folder, album_name):
        """Step6: Artwork最適化を実行"""
        from logic.artwork_handler import ArtworkHandler
        
        # state.jsonの確認
        if workflow.state.is_step_completed("step6_artwork"):
            return True  # 既に完了済み
        
        # hasArtworkフラグチェック
        if not workflow.state.has_artwork():
            workflow.state.mark_step_completed("step6_artwork")
            return True  # アートワークなしの場合はスキップ
        
        artwork_handler = ArtworkHandler(self.config)
        
        # cover.jpg -> cover.webp 変換
        cover_jpg = os.path.join(album_folder, "cover.jpg")
        cover_webp = os.path.join(album_folder, "cover.webp")
        
        if not os.path.exists(cover_jpg):
            return False
        
        success = artwork_handler.optimize_artwork(cover_jpg, cover_webp)
        if success:
            workflow.state.mark_step_completed("step6_artwork")
            return True
        return False
    
    def _process_step7(self, workflow, album_folder, album_name):
        """Step7: 転送を実行（自動モードでは実際の転送はスキップ）"""
        # Step7は手動確認が必要なため、状態を完了にするのみ
        # 実際の転送はGUIから手動で行う
        if workflow.state.is_step_completed("step7_transfer"):
            return True
        
        # 必要なファイルの存在確認のみ
        flac_src = os.path.join(album_folder, "_flac_src")
        aac_dest = os.path.join(album_folder, "_aac")
        opus_dest = os.path.join(album_folder, "_opus")
        
        if not os.path.exists(flac_src):
            return False
        
        # Step7は準備完了としてマーク（実際の転送は手動）
        # workflow.state.mark_step_completed("step7_transfer")
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

"""
汎用ステップパネル (Step 4-10)
"""
import os
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QTextEdit
)
from PySide6.QtCore import Signal

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager
from logic.external_tools import ExternalToolRunner
from logic.artwork_handler import extract_artwork_from_flac, resize_artwork_with_magick
from send2trash import send2trash


class GenericStepPanel(QWidget):
    """汎用ステップパネル (Step 4-10)"""
    
    step_completed = Signal()
    
    def __init__(self, config: ConfigManager, workflow: WorkflowManager, step_num: int):
        super().__init__()
        self.config = config
        self.workflow = workflow
        self.step_num = step_num
        self.album_folder = None
        self.tool_runner = None
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        step_name = self.workflow.STEP_NAMES.get(self.step_num, f"Step {self.step_num}")
        title = QLabel(f"<h2>{step_name}</h2>")
        layout.addWidget(title)
        
        # 説明（ステップごとに異なる）
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)
        
        layout.addSpacing(10)
        
        # 指示テキスト
        self.instruction_text = QTextEdit()
        self.instruction_text.setReadOnly(True)
        layout.addWidget(self.instruction_text)
        
        # アクションボタン
        button_layout = QHBoxLayout()
        
        self.action_button = QPushButton("実行")
        self.action_button.clicked.connect(self.on_action)
        button_layout.addWidget(self.action_button)
        
        self.complete_button = QPushButton("完了")
        self.complete_button.clicked.connect(self.on_complete)
        button_layout.addWidget(self.complete_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # ステップごとの説明とボタンラベルを設定
        self.setup_step_content()
    
    def setup_step_content(self):
        """ステップごとの内容を設定"""
        if self.step_num == 4:
            self.desc_label.setText("MediaHuman Audio Converter で AAC (M4A) 形式に変換します。")
            self.instruction_text.setPlainText(
                "【手順】\n"
                "1. 「実行」ボタンを押して MediaHuman を起動\n"
                "2. アルバムフォルダの全FLACファイルを追加\n"
                "3. 出力形式を AAC (M4A) に設定\n"
                "4. 出力先を '_aac_output' フォルダに設定\n"
                "5. 変換を実行\n"
                "6. MediaHuman を終了\n"
                "7. 「完了」ボタンを押す"
            )
            self.action_button.setText("MediaHuman を起動")
        
        elif self.step_num == 5:
            self.desc_label.setText("foobar2000 で Opus 形式に変換します。")
            self.instruction_text.setPlainText(
                "【手順】\n"
                "1. 「実行」ボタンを押して foobar2000 を起動\n"
                "2. アルバムフォルダの全FLACファイルを追加\n"
                "3. 右クリック → Convert → ...\n"
                "4. 出力形式を Opus に設定\n"
                "5. 出力先を '_opus_output' フォルダに設定\n"
                "6. 変換を実行\n"
                "7. foobar2000 を終了\n"
                "8. 「完了」ボタンを押す"
            )
            self.action_button.setText("foobar2000 を起動")
        
        elif self.step_num == 6:
            self.desc_label.setText("アートワークを600x600にリサイズし、JPG/WebP形式で保存します。")
            self.instruction_text.setPlainText(
                "【自動処理】\n"
                "「実行」ボタンを押すと、自動的に:\n"
                "1. 1曲目のFLACからアートワークを抽出\n"
                "2. ImageMagick で JPG (Q85) にリサイズ\n"
                "3. ImageMagick で WebP (Q85) にリサイズ\n"
                "4. '_artwork_resized' フォルダに保存"
            )
            self.action_button.setText("自動実行")
        
        elif self.step_num == 7:
            self.desc_label.setText("リサイズしたアートワークを圧縮音源に埋め込みます。")
            self.instruction_text.setPlainText(
                "【手順】\n"
                "1. 「実行」ボタンを押して Mp3tag を起動\n"
                "2. '_aac_output' フォルダを開く\n"
                "3. 全ファイルを選択し、'_artwork_resized/cover.jpg' を埋め込む\n"
                "4. '_opus_output' フォルダを開く\n"
                "5. 全ファイルを選択し、'_artwork_resized/cover.webp' を埋め込む\n"
                "6. Mp3tag を終了\n"
                "7. 「完了」ボタンを押す"
            )
            self.action_button.setText("Mp3tag を起動")
        
        elif self.step_num == 8:
            self.desc_label.setText("ReplayGain スキャンを実行し、最終FLACをアーカイブします。")
            self.instruction_text.setPlainText(
                "【手順】\n"
                "1. 「実行」ボタンを押して foobar2000 を起動\n"
                "2. アルバムフォルダの全FLACファイルを追加\n"
                "3. 右クリック → ReplayGain → Scan per-file track gain\n"
                "4. foobar2000 を終了\n"
                "5. 自動的に '_final_flac' フォルダにコピーされます\n"
                "6. 「完了」ボタンを押す"
            )
            self.action_button.setText("foobar2000 を起動")
        
        elif self.step_num == 9:
            self.desc_label.setText("完成したファイルをNASやクラウドに転送します。")
            self.instruction_text.setPlainText(
                "【手順】\n"
                "1. 「実行」ボタンを押して WinSCP を起動\n"
                "2. NASまたはクラウドに接続\n"
                "3. '_final_flac' フォルダをアップロード\n"
                "4. '_aac_output' と '_opus_output' フォルダもアップロード（任意）\n"
                "5. WinSCP を終了\n"
                "6. 「完了」ボタンを押す"
            )
            self.action_button.setText("WinSCP を起動")
        
        elif self.step_num == 10:
            self.desc_label.setText("作業フォルダをクリーンアップします。")
            self.instruction_text.setPlainText(
                "【警告】\n"
                "このステップを実行すると、作業フォルダがゴミ箱に移動されます。\n"
                "必ず全ての成果物が正しく保存されていることを確認してください。\n\n"
                "「実行」ボタンを押すと、アルバムフォルダがゴミ箱に移動されます。"
            )
            self.action_button.setText("ゴミ箱に移動")
            self.complete_button.setVisible(False)
    
    def load_album(self, album_folder: str):
        """アルバムを読み込み"""
        self.album_folder = album_folder
    
    def on_action(self):
        """実行ボタンの処理"""
        if self.step_num == 4:
            self.launch_tool("MediaHuman")
        elif self.step_num == 5:
            self.launch_tool("Foobar2000")
        elif self.step_num == 6:
            self.auto_resize_artwork()
        elif self.step_num == 7:
            self.launch_tool("Mp3Tag")
        elif self.step_num == 8:
            self.launch_tool_and_copy_final("Foobar2000")
        elif self.step_num == 9:
            self.launch_tool("WinSCP")
        elif self.step_num == 10:
            self.cleanup_folder()
    
    def launch_tool(self, tool_name: str):
        """ツールを起動"""
        tool_path = self.config.get_tool_path(tool_name)
        
        if not tool_path:
            QMessageBox.warning(
                self,
                "警告",
                f"{tool_name}.exe が見つかりません。\n"
                f"config.ini で {tool_name} のパスを設定してください。"
            )
            return
        
        if not self.album_folder:
            QMessageBox.warning(self, "エラー", "アルバムフォルダが選択されていません。")
            return
        
        # ツールを起動
        self.tool_runner = ExternalToolRunner(self)
        self.tool_runner.finished.connect(self.on_tool_finished)
        
        success = self.tool_runner.run_gui_tool(
            tool_path,
            [self.album_folder],
            self.album_folder
        )
        
        if success:
            self.action_button.setEnabled(False)
    
    def launch_tool_and_copy_final(self, tool_name: str):
        """ツールを起動し、終了後に _final_flac にコピー"""
        self.launch_tool(tool_name)
    
    def on_tool_finished(self, exit_code, exit_status):
        """ツール終了時の処理"""
        self.action_button.setEnabled(True)
        
        # Step 8 の場合は _final_flac にコピー
        if self.step_num == 8:
            self.copy_to_final_flac()
    
    def auto_resize_artwork(self):
        """アートワーク自動リサイズ (Step 6)"""
        if not self.album_folder or not self.workflow.state:
            return
        
        # アートワークがない場合はスキップ
        if not self.workflow.state.has_artwork():
            QMessageBox.information(
                self,
                "スキップ",
                "アートワークが存在しないため、このステップをスキップします。"
            )
            self.step_completed.emit()
            return
        
        # 1曲目のFLACを取得
        tracks = self.workflow.state.get_tracks()
        if not tracks:
            QMessageBox.warning(self, "エラー", "トラック情報が見つかりません。")
            return
        
        first_flac = os.path.join(self.album_folder, tracks[0].get("finalFile", ""))
        if not os.path.exists(first_flac):
            QMessageBox.warning(self, "エラー", "1曲目のFLACファイルが見つかりません。")
            return
        
        # 出力フォルダを作成
        artwork_dir = os.path.join(self.album_folder, "_artwork_resized")
        os.makedirs(artwork_dir, exist_ok=True)
        
        # アートワークを抽出
        temp_image = os.path.join(artwork_dir, "cover_temp.jpg")
        if not extract_artwork_from_flac(first_flac, temp_image):
            QMessageBox.critical(self, "エラー", "アートワークの抽出に失敗しました。")
            return
        
        # magick でリサイズ
        magick_path = self.config.get_tool_path("Magick")
        if not magick_path:
            QMessageBox.warning(self, "警告", "magick.exe が見つかりません。")
            return
        
        jpeg_quality = int(self.config.get_setting("JpegQuality", "85"))
        webp_quality = int(self.config.get_setting("WebpQuality", "85"))
        width = int(self.config.get_setting("ResizeWidth", "600"))
        
        # JPG
        jpg_output = os.path.join(artwork_dir, "cover.jpg")
        success, error = resize_artwork_with_magick(
            magick_path, temp_image, jpg_output, width, jpeg_quality, "jpg"
        )
        if not success:
            QMessageBox.critical(self, "エラー", f"JPGリサイズ失敗:\n{error}")
            return
        
        # WebP
        webp_output = os.path.join(artwork_dir, "cover.webp")
        success, error = resize_artwork_with_magick(
            magick_path, temp_image, webp_output, width, webp_quality, "webp"
        )
        if not success:
            QMessageBox.critical(self, "エラー", f"WebPリサイズ失敗:\n{error}")
            return
        
        # 一時ファイルを削除
        os.remove(temp_image)
        
        QMessageBox.information(
            self,
            "完了",
            f"アートワークのリサイズが完了しました。\n\n"
            f"出力先: {artwork_dir}"
        )
    
    def copy_to_final_flac(self):
        """_final_flac フォルダにコピー (Step 8)"""
        if not self.album_folder:
            return
        
        final_dir = os.path.join(self.album_folder, "_final_flac")
        os.makedirs(final_dir, exist_ok=True)
        
        # 全FLACをコピー
        success_count = 0
        try:
            for file in os.listdir(self.album_folder):
                if file.lower().endswith('.flac'):
                    src = os.path.join(self.album_folder, file)
                    dst = os.path.join(final_dir, file)
                    shutil.copy2(src, dst)
                    success_count += 1
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"ファイルコピー失敗:\n{e}")
            return
        
        QMessageBox.information(
            self,
            "完了",
            f"{success_count} 個のFLACファイルを '_final_flac' にコピーしました。"
        )
    
    def cleanup_folder(self):
        """作業フォルダをクリーンアップ (Step 10)"""
        if not self.album_folder:
            return
        
        reply = QMessageBox.warning(
            self,
            "警告",
            f"以下のフォルダをゴミ箱に移動します:\n\n"
            f"{self.album_folder}\n\n"
            f"この操作は取り消せません。続行しますか?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                send2trash(self.album_folder)
                QMessageBox.information(
                    self,
                    "完了",
                    "作業フォルダをゴミ箱に移動しました。"
                )
                self.step_completed.emit()
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"削除に失敗しました:\n{e}")
    
    def on_complete(self):
        """完了ボタン"""
        # バリデーション
        can_advance, error_msg = self.workflow.can_advance_to_next_step()
        
        if not can_advance:
            QMessageBox.warning(self, "エラー", f"次のステップに進めません:\n{error_msg}")
            return
        
        self.step_completed.emit()

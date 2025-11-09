"""
Step 7: 最終転送パネル
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox
)
from PySide6.QtCore import Signal

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager


class Step7TransferPanel(QWidget):
    """Step 7: 最終転送パネル"""
    
    step_completed = Signal()
    
    def __init__(self, config: ConfigManager, workflow: WorkflowManager):
        super().__init__()
        self.config = config
        self.workflow = workflow
        self.album_folder = None
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel("<h2>Step 7: 最終転送</h2>")
        layout.addWidget(title)
        
        # 説明
        desc = QLabel(
            "完成したファイル（FLAC、AAC、Opus、アートワーク）を\n"
            "NAS、クラウド、または外部ストレージに転送します。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        # 転送フォルダ情報
        info_label = QLabel(
            "<b>転送対象:</b><br>"
            "• _flac_src フォルダ（FLACファイル）<br>"
            "• _aac_output フォルダ（AACファイル）<br>"
            "• _opus_output フォルダ（Opusファイル）<br>"
            "• _artwork_resized フォルダ（カバー画像）"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # メインボタン
        main_btns = QHBoxLayout()
        
        self.btn_open_folder = QPushButton("📁 作業フォルダを開く")
        self.btn_open_folder.setMinimumHeight(40)
        self.btn_open_folder.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_open_folder.clicked.connect(self.on_open_folder)
        main_btns.addWidget(self.btn_open_folder)
        
        self.btn_complete = QPushButton("✓ Step 7 完了")
        self.btn_complete.setMinimumHeight(40)
        self.btn_complete.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_complete.clicked.connect(self.on_complete)
        main_btns.addWidget(self.btn_complete)
        
        layout.addLayout(main_btns)
        
        layout.addSpacing(10)
        
        # 補助ボタン
        helper_label = QLabel("<b>転送ツール（任意）:</b>")
        layout.addWidget(helper_label)
        
        helper_btns = QHBoxLayout()
        
        self.btn_winscp = QPushButton("🌐 WinSCP を起動")
        self.btn_winscp.setMaximumWidth(150)
        self.btn_winscp.setToolTip("WinSCPでNASやサーバーに転送")
        self.btn_winscp.clicked.connect(self.on_launch_winscp)
        helper_btns.addWidget(self.btn_winscp)
        
        self.btn_explorer = QPushButton("📂 エクスプローラーで開く")
        self.btn_explorer.setMaximumWidth(180)
        self.btn_explorer.clicked.connect(self.on_open_explorer)
        helper_btns.addWidget(self.btn_explorer)
        
        helper_btns.addStretch()
        layout.addLayout(helper_btns)
        
        layout.addSpacing(10)
        
        # 転送手順の案内
        instructions = QLabel(
            "<b>転送手順:</b><br>"
            "1. 「作業フォルダを開く」で対象フォルダを確認<br>"
            "2. 手動またはWinSCPで転送先にコピー<br>"
            "3. 転送完了後「Step 7 完了」をクリック"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: gray;")
        layout.addWidget(instructions)
        
        layout.addStretch()
    
    def load_album(self, album_folder: str):
        """アルバムを読み込み"""
        self.album_folder = album_folder
    
    def on_open_folder(self):
        """作業フォルダを開く"""
        if not self.album_folder:
            QMessageBox.warning(self, "エラー", "アルバムフォルダが選択されていません。")
            return
        
        try:
            os.startfile(self.album_folder)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"フォルダを開けませんでした:\n{e}")
    
    def on_open_explorer(self):
        """エクスプローラーで開く（on_open_folderと同じ）"""
        self.on_open_folder()
    
    def on_launch_winscp(self):
        """WinSCPを起動"""
        winscp_path = self.config.get_tool_path("WinSCP")
        
        if not winscp_path:
            QMessageBox.information(
                self,
                "WinSCP未設定",
                "WinSCPのパスが設定されていません。\n\n"
                "config.ini の [Paths] セクションに\n"
                "WinSCP = C:\\Program Files (x86)\\WinSCP\\WinSCP.exe\n"
                "のように設定してください。"
            )
            return
        
        try:
            import subprocess
            subprocess.Popen([winscp_path])
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"WinSCPの起動に失敗しました:\n{e}")
    
    def on_complete(self):
        """完了ボタン"""
        reply = QMessageBox.question(
            self,
            "確認",
            "Step 7 を完了しますか?\n\n"
            "全てのファイルが正しく転送されたことを確認してください。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.step_completed.emit()

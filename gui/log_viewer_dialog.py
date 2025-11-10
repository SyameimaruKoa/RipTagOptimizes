"""
ログビューアーダイアログ - _logs フォルダのログを表示
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QTextEdit,
    QSplitter, QMessageBox
)
from PySide6.QtCore import Qt

from logic.log_manager import LogManager


class LogViewerDialog(QDialog):
    """ログビューアーダイアログ"""
    
    def __init__(self, log_manager: LogManager, parent=None):
        super().__init__(parent)
        self.log_manager = log_manager
        self.setWindowTitle("ログビューアー")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        self.init_ui()
        self.load_log_list()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel("<h2>📋 ログビューアー</h2>")
        layout.addWidget(title)
        
        # スプリッター（左: ファイル一覧、右: ログ内容）
        splitter = QSplitter(Qt.Horizontal)
        
        # 左ペイン: ログファイル一覧
        left_widget = QVBoxLayout()
        left_container = QVBoxLayout()
        
        left_container.addWidget(QLabel("<b>ログファイル一覧:</b>"))
        
        self.log_list = QListWidget()
        self.log_list.currentItemChanged.connect(self.on_log_selected)
        left_container.addWidget(self.log_list)
        
        # 削除ボタン
        btn_delete = QPushButton("🗑️ 選択したログを削除")
        btn_delete.clicked.connect(self.on_delete_log)
        left_container.addWidget(btn_delete)
        
        # 左ペインコンテナ
        from PySide6.QtWidgets import QWidget
        left_pane = QWidget()
        left_pane.setLayout(left_container)
        splitter.addWidget(left_pane)
        
        # 右ペイン: ログ内容
        right_widget = QVBoxLayout()
        right_container = QVBoxLayout()
        
        right_container.addWidget(QLabel("<b>ログ内容:</b>"))
        
        self.log_content = QTextEdit()
        self.log_content.setReadOnly(True)
        self.log_content.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10pt;")
        right_container.addWidget(self.log_content)
        
        # 右ペインコンテナ
        right_pane = QWidget()
        right_pane.setLayout(right_container)
        splitter.addWidget(right_pane)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        # 閉じるボタン
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("閉じる")
        btn_close.setMinimumHeight(35)
        btn_close.clicked.connect(self.accept)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
    
    def load_log_list(self):
        """ログファイル一覧を読み込む"""
        self.log_list.clear()
        log_files = self.log_manager.get_log_files()
        
        if not log_files:
            self.log_list.addItem("（ログファイルがありません）")
            return
        
        for filename in log_files:
            self.log_list.addItem(filename)
    
    def on_log_selected(self):
        """ログファイルが選択されたときの処理"""
        current_item = self.log_list.currentItem()
        if not current_item:
            return
        
        filename = current_item.text()
        if filename == "（ログファイルがありません）":
            self.log_content.clear()
            return
        
        # ログ内容を読み込んで表示
        content = self.log_manager.read_log_file(filename)
        self.log_content.setPlainText(content)
    
    def on_delete_log(self):
        """選択したログを削除"""
        current_item = self.log_list.currentItem()
        if not current_item:
            return
        
        filename = current_item.text()
        if filename == "（ログファイルがありません）":
            return
        
        reply = QMessageBox.question(
            self,
            "確認",
            f"ログファイルを削除しますか?\n\n{filename}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                import os
                log_path = os.path.join(self.log_manager.log_dir, filename)
                os.remove(log_path)
                self.load_log_list()
                self.log_content.clear()
                QMessageBox.information(self, "完了", "ログファイルを削除しました。")
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"ログファイルの削除に失敗しました:\n{e}")

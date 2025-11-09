"""
設定ダイアログ - config.ini の GUI 編集機能
"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog,
    QGroupBox, QSpinBox, QMessageBox, QTabWidget, QWidget
)
from PySide6.QtCore import Qt

from logic.config_manager import ConfigManager


class SettingsDialog(QDialog):
    """設定ダイアログ"""
    
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("設定")
        self.setMinimumWidth(700)
        self.setMinimumHeight(550)
        
        # 設定値を保持する辞書
        self.path_edits = {}
        self.quality_spins = {}
        self.keyword_edit = None
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel("<h2>⚙️ 設定</h2>")
        layout.addWidget(title)
        
        # タブウィジェット
        tabs = QTabWidget()
        
        # タブ1: ツールパス
        tab_tools = self.create_tools_tab()
        tabs.addTab(tab_tools, "🔧 ツールパス")
        
        # タブ2: 品質設定
        tab_quality = self.create_quality_tab()
        tabs.addTab(tab_quality, "🎨 品質設定")
        
        # タブ3: Demucs設定
        tab_demucs = self.create_demucs_tab()
        tabs.addTab(tab_demucs, "🎵 Demucs設定")
        
        layout.addWidget(tabs)
        
        # ボタン
        btn_layout = QHBoxLayout()
        
        btn_save = QPushButton("💾 保存")
        btn_save.setMinimumHeight(35)
        btn_save.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        btn_save.clicked.connect(self.on_save)
        btn_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.setMinimumHeight(35)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
    
    def create_tools_tab(self) -> QWidget:
        """ツールパスタブを作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        desc = QLabel(
            "各ツールの実行ファイルパスを設定してください。\n"
            "空欄の場合は PATH から自動検出を試みます（警告付き）。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # ツールパス設定
        form = QFormLayout()
        
        tools = [
            ("FastCopy", "FastCopy.exe"),
            ("Mp3Tag", "Mp3tag.exe"),
            ("MediaHuman", "MediaHuman Audio Converter.exe"),
            ("Foobar2000", "foobar2000.exe"),
            ("WinSCP", "WinSCP.exe"),
            ("FreeFileSync", "FreeFileSync.exe"),
            ("Flac", "flac.exe"),
            ("Metaflac", "metaflac.exe"),
            ("Magick", "magick.exe"),
        ]
        
        for key, label in tools:
            row = QHBoxLayout()
            
            edit = QLineEdit()
            edit.setPlaceholderText(f"例: C:\\Program Files\\{label}")
            self.path_edits[key] = edit
            row.addWidget(edit, 1)
            
            btn_browse = QPushButton("📁 参照")
            btn_browse.setMaximumWidth(80)
            btn_browse.clicked.connect(lambda checked, k=key: self.on_browse_tool(k))
            row.addWidget(btn_browse)
            
            form.addRow(f"{label}:", row)
        
        layout.addLayout(form)
        layout.addStretch()
        
        return widget
    
    def create_quality_tab(self) -> QWidget:
        """品質設定タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        desc = QLabel(
            "アートワーク最適化とリサイズの品質を設定します。\n"
            "品質: 1-100 (高いほど高品質、ファイルサイズも大きくなります)"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        form = QFormLayout()
        
        # JpegQuality
        spin_jpeg = QSpinBox()
        spin_jpeg.setRange(1, 100)
        spin_jpeg.setValue(85)
        spin_jpeg.setSuffix(" %")
        self.quality_spins["JpegQuality"] = spin_jpeg
        form.addRow("JPEG 品質:", spin_jpeg)
        
        # WebpQuality
        spin_webp = QSpinBox()
        spin_webp.setRange(1, 100)
        spin_webp.setValue(85)
        spin_webp.setSuffix(" %")
        self.quality_spins["WebpQuality"] = spin_webp
        form.addRow("WebP 品質:", spin_webp)
        
        # ResizeWidth
        spin_width = QSpinBox()
        spin_width.setRange(100, 2000)
        spin_width.setValue(600)
        spin_width.setSuffix(" px")
        self.quality_spins["ResizeWidth"] = spin_width
        form.addRow("リサイズ幅:", spin_width)
        
        layout.addLayout(form)
        layout.addStretch()
        
        return widget
    
    def create_demucs_tab(self) -> QWidget:
        """Demucs設定タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        desc = QLabel(
            "Demucs 処理で自動除外するキーワードを設定します。\n"
            "カンマ区切りで複数指定可能です（例: instrumental, inst, off vocal）"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        form = QFormLayout()
        
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("例: instrumental, inst, off vocal, カラオケ")
        form.addRow("除外キーワード:", self.keyword_edit)
        
        layout.addLayout(form)
        layout.addStretch()
        
        return widget
    
    def load_settings(self):
        """現在の設定を読み込む"""
        # ツールパス
        for key, edit in self.path_edits.items():
            path = self.config.get_tool_path(key)
            if path:
                edit.setText(path)
        
        # 品質設定
        self.quality_spins["JpegQuality"].setValue(int(self.config.get_setting("JpegQuality", "85")))
        self.quality_spins["WebpQuality"].setValue(int(self.config.get_setting("WebpQuality", "85")))
        self.quality_spins["ResizeWidth"].setValue(int(self.config.get_setting("ResizeWidth", "600")))
        
        # Demucs キーワード
        keywords = self.config.get_demucs_keywords()
        if keywords:
            self.keyword_edit.setText(", ".join(keywords))
    
    def on_browse_tool(self, key: str):
        """ツール参照ボタン"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"{key} を選択",
            "",
            "実行ファイル (*.exe);;すべてのファイル (*.*)"
        )
        if path:
            self.path_edits[key].setText(path)
    
    def on_save(self):
        """設定を保存"""
        try:
            # ツールパス
            for key, edit in self.path_edits.items():
                path = edit.text().strip()
                if path:
                    self.config.config['Paths'][key] = path
                else:
                    # 空欄の場合は削除
                    if key in self.config.config['Paths']:
                        del self.config.config['Paths'][key]
            
            # 品質設定
            if 'Artwork' not in self.config.config:
                self.config.config['Artwork'] = {}
            
            self.config.config['Artwork']['JpegQuality'] = str(self.quality_spins["JpegQuality"].value())
            self.config.config['Artwork']['WebpQuality'] = str(self.quality_spins["WebpQuality"].value())
            self.config.config['Artwork']['ResizeWidth'] = str(self.quality_spins["ResizeWidth"].value())
            
            # Demucs キーワード
            if 'Demucs' not in self.config.config:
                self.config.config['Demucs'] = {}
            
            keywords = self.keyword_edit.text().strip()
            if keywords:
                self.config.config['Demucs']['SkipKeywords'] = keywords
            else:
                if 'SkipKeywords' in self.config.config['Demucs']:
                    del self.config.config['Demucs']['SkipKeywords']
            
            # 保存
            if self.config.save():
                QMessageBox.information(self, "保存完了", "設定を保存しました。")
                self.accept()
            else:
                QMessageBox.critical(self, "エラー", "設定の保存に失敗しました。")
        
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定の保存中にエラーが発生しました:\n{e}")

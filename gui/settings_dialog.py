"""
設定ダイアログ - config.ini の GUI 編集機能
"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog,
    QGroupBox, QSpinBox, QMessageBox, QTabWidget, QWidget,
    QListWidget, QListWidgetItem
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
        self.dir_edits = {}  # ディレクトリ用
        self.quality_spins = {}
        self.keyword_list = None
        self.keyword_input = None
        
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
        
        # タブ0: ディレクトリ設定（最初のタブ）
        tab_dirs = self.create_directories_tab()
        tabs.addTab(tab_dirs, "📁 ディレクトリ")
        
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
    
    def create_directories_tab(self) -> QWidget:
        """ディレクトリ設定タブを作成"""
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        
        desc = QLabel(
            "⚠️ 必須設定：ワークフロー実行に必要なディレクトリを設定してください。\n"
            "これらが未設定の場合、アプリケーション起動時に設定を求められます。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #ff6b6b; font-weight: bold; margin-bottom: 10px; padding: 10px; background-color: #fff3cd; border-radius: 5px;")
        layout.addWidget(desc)
        
        # ディレクトリ設定
        form = QFormLayout()
        
        directories = [
            ("WorkDir", "作業フォルダ", "アルバムデータを管理する作業ディレクトリ"),
            ("MusicCenterDir", "Music Center フォルダ", "Music Center の取り込み先ディレクトリ"),
            ("ExternalOutputDir", "外部ツール出力先", "MediaHuman/foobar2000 の初期出力先"),
        ]
        
        for key, label, tooltip in directories:
            row = QVBoxLayout()
            
            # ラベルと説明
            label_widget = QLabel(f"<b>{label}</b>")
            row.addWidget(label_widget)
            
            desc_widget = QLabel(tooltip)
            desc_widget.setStyleSheet("color: gray; font-size: 10px;")
            row.addWidget(desc_widget)
            
            # 入力欄と参照ボタン
            input_row = QHBoxLayout()
            
            edit = QLineEdit()
            edit.setPlaceholderText(f"例: C:\\Users\\YourName\\{key}")
            self.dir_edits[key] = edit
            input_row.addWidget(edit, 1)
            
            btn_browse = QPushButton("📁 参照")
            btn_browse.setMaximumWidth(80)
            btn_browse.clicked.connect(lambda checked, k=key: self.on_browse_directory(k))
            input_row.addWidget(btn_browse)
            
            row.addLayout(input_row)
            form.addRow(row)
        
        layout.addLayout(form)
        layout.addStretch()
        
        return widget
    
    def on_browse_directory(self, key: str):
        """ディレクトリ参照ボタン"""
        current = self.dir_edits[key].text().strip()
        start_dir = current if current and os.path.isdir(current) else ""
        
        path = QFileDialog.getExistingDirectory(
            self,
            f"{key} を選択",
            start_dir
        )
        if path:
            self.dir_edits[key].setText(path)
    
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
            "ファイル名にこれらのキーワードが含まれる場合、Demucs処理がスキップされます。"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # 入力エリア
        input_layout = QHBoxLayout()
        input_label = QLabel("キーワード追加:")
        input_layout.addWidget(input_label)
        
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("例: instrumental, inst, off vocal")
        self.keyword_input.returnPressed.connect(self.on_add_keyword)
        input_layout.addWidget(self.keyword_input, 1)
        
        btn_add = QPushButton("➕ 追加")
        btn_add.setMinimumWidth(80)
        btn_add.clicked.connect(self.on_add_keyword)
        input_layout.addWidget(btn_add)
        
        layout.addLayout(input_layout)
        
        # リストウィジェット
        list_label = QLabel("登録済みキーワード:")
        layout.addWidget(list_label)
        
        self.keyword_list = QListWidget()
        self.keyword_list.setMinimumHeight(250)
        self.keyword_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.keyword_list)
        
        # 削除ボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_remove = QPushButton("🗑️ 選択項目を削除")
        btn_remove.clicked.connect(self.on_remove_keywords)
        btn_layout.addWidget(btn_remove)
        
        btn_clear = QPushButton("🧹 すべてクリア")
        btn_clear.clicked.connect(self.on_clear_keywords)
        btn_layout.addWidget(btn_clear)
        
        layout.addLayout(btn_layout)
        
        return widget
    
    def on_add_keyword(self):
        """キーワードを追加"""
        text = self.keyword_input.text().strip()
        if not text:
            return
        
        # カンマ区切りで複数追加可能
        keywords = [kw.strip() for kw in text.split(',') if kw.strip()]
        
        # 重複チェック
        existing_keywords = [self.keyword_list.item(i).text() 
                           for i in range(self.keyword_list.count())]
        
        for keyword in keywords:
            if keyword.lower() not in [k.lower() for k in existing_keywords]:
                self.keyword_list.addItem(keyword)
        
        # 入力欄をクリア
        self.keyword_input.clear()
    
    def on_remove_keywords(self):
        """選択されたキーワードを削除"""
        selected_items = self.keyword_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "削除", "削除するキーワードを選択してください。")
            return
        
        for item in selected_items:
            self.keyword_list.takeItem(self.keyword_list.row(item))
    
    def on_clear_keywords(self):
        """すべてのキーワードをクリア"""
        if self.keyword_list.count() == 0:
            return
        
        reply = QMessageBox.question(
            self,
            "すべてクリア",
            "すべてのキーワードを削除しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.keyword_list.clear()
    
    def load_settings(self):
        """現在の設定を読み込む"""
        # ディレクトリ設定
        dir_sections = {
            "WorkDir": "Paths",
            "MusicCenterDir": "Paths",
            "ExternalOutputDir": "Settings"
        }
        for key, edit in self.dir_edits.items():
            section = dir_sections.get(key, "Paths")
            value = self.config.config.get(section, key, fallback='')
            if value:
                edit.setText(value)
        
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
            for keyword in keywords:
                self.keyword_list.addItem(keyword)
    
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
            # ディレクトリ設定（必須チェック）
            required_dirs = ["WorkDir", "MusicCenterDir", "ExternalOutputDir"]
            missing_dirs = []
            
            for key in required_dirs:
                value = self.dir_edits[key].text().strip()
                if not value:
                    missing_dirs.append(key)
            
            if missing_dirs:
                QMessageBox.warning(
                    self,
                    "必須項目が未入力",
                    f"以下のディレクトリは必須です:\n\n" + "\n".join([f"- {d}" for d in missing_dirs])
                )
                return
            
            # ディレクトリ設定を保存
            dir_sections = {
                "WorkDir": "Paths",
                "MusicCenterDir": "Paths",
                "ExternalOutputDir": "Settings"
            }
            for key, edit in self.dir_edits.items():
                path = edit.text().strip()
                if path:
                    section = dir_sections.get(key, "Paths")
                    if section not in self.config.config:
                        self.config.config[section] = {}
                    self.config.config[section][key] = path
            
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
            
            # リストから全キーワードを取得してカンマ区切りで保存
            keywords = []
            for i in range(self.keyword_list.count()):
                keyword = self.keyword_list.item(i).text().strip()
                if keyword:
                    keywords.append(keyword)
            
            if keywords:
                self.config.config['Demucs']['SkipKeywords'] = ', '.join(keywords)
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

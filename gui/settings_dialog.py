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
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("設定")
        self.setMinimumWidth(820)
        self.setMinimumHeight(580)
        self.path_edits = {}
        self.dir_edits = {}
        self.status_labels = {}
        self.quality_spins = {}
        self.keyword_list = None
        self.keyword_input = None
        self.directories = [
            ("WorkDir", "作業フォルダ", "アルバムデータを管理する作業ディレクトリ"),
            ("MusicCenterDir", "Music Center フォルダ", "Music Center の取り込み先ディレクトリ"),
            ("ExternalOutputDir", "外部ツール出力先", "MediaHuman/foobar2000 の初期出力先"),
        ]
        self.tools = [
            ("Demucs", "Demucs実行ファイル (StemRoller等)"),
            ("Mp3Tag", "Mp3tag.exe"),
            ("MediaHuman", "MediaHuman Audio Converter.exe"),
            ("Foobar2000", "foobar2000.exe"),
            ("WinSCP", "WinSCP.exe"),
            ("FreeFileSync", "FreeFileSync.exe"),
            ("Flac", "flac.exe"),
            ("Metaflac", "metaflac.exe"),
            ("Magick", "magick.exe"),
        ]
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        title = QLabel("<h2>⚙️ 設定</h2>")
        layout.addWidget(title)
        tabs = QTabWidget()
        tab_dirs = self.create_directories_tab()
        tabs.addTab(tab_dirs, "📁 ディレクトリ")
        tab_tools = self.create_tools_tab()
        tabs.addTab(tab_tools, "🔧 ツールパス")
        tab_quality = self.create_quality_tab()
        tabs.addTab(tab_quality, "🎨 品質設定")
        tab_demucs = self.create_demucs_tab()
        tabs.addTab(tab_demucs, "🎵 Demucs設定")
        layout.addWidget(tabs)
        btn_layout = QHBoxLayout()
        btn_check_all = QPushButton("🔍 全てを一括確認")
        btn_check_all.setMinimumHeight(35)
        btn_check_all.clicked.connect(self.check_all_settings)
        btn_layout.addWidget(btn_check_all)
        btn_layout.addStretch()
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
        top_bar = QHBoxLayout()
        btn_check_dirs = QPushButton("🔍 ディレクトリを一括確認")
        btn_check_dirs.clicked.connect(lambda: self.check_all_directories(show_summary=True))
        top_bar.addWidget(btn_check_dirs)
        top_bar.addStretch()
        layout.addLayout(top_bar)
        form = QFormLayout()
        for key, label, tooltip in self.directories:
            row = QVBoxLayout()
            label_widget = QLabel(f"<b>{label}</b>")
            row.addWidget(label_widget)
            desc_widget = QLabel(tooltip)
            desc_widget.setStyleSheet("color: gray; font-size: 10px;")
            row.addWidget(desc_widget)
            input_row = QHBoxLayout()
            edit = QLineEdit()
            edit.setPlaceholderText(f"例: C:\\Users\\YourName\\{key}")
            self.dir_edits[key] = edit
            input_row.addWidget(edit, 1)
            btn_browse = QPushButton("📁 参照")
            btn_browse.setMaximumWidth(75)
            btn_browse.clicked.connect(lambda checked, k=key: self.on_browse_directory(k))
            input_row.addWidget(btn_browse)
            btn_check = QPushButton("🔍 確認")
            btn_check.setMaximumWidth(75)
            btn_check.clicked.connect(lambda checked, k=key, l=label: self.check_single_path(k, label=l, path_type='dir', show_popup=True))
            input_row.addWidget(btn_check)
            status_lbl = QLabel("未確認")
            status_lbl.setMinimumWidth(110)
            status_lbl.setStyleSheet("color: #888888;")
            self.status_labels[key] = status_lbl
            input_row.addWidget(status_lbl)
            row.addLayout(input_row)
            form.addRow(row)
        layout.addLayout(form)
        layout.addStretch()
        return widget
    
    def on_browse_directory(self, key: str):
        current = self.dir_edits[key].text().strip()
        start_dir = current if current and os.path.isdir(current) else ""
        path = QFileDialog.getExistingDirectory(
            self,
            f"{key} を選択",
            start_dir
        )
        if path:
            self.dir_edits[key].setText(os.path.normpath(path))
            self.check_single_path(key, path_type='dir', show_popup=False)
    
    def create_tools_tab(self) -> QWidget:
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
        top_bar = QHBoxLayout()
        btn_check_tools = QPushButton("🔍 ツールパスを一括確認")
        btn_check_tools.clicked.connect(lambda: self.check_all_tools(show_summary=True))
        top_bar.addWidget(btn_check_tools)
        top_bar.addStretch()
        layout.addLayout(top_bar)
        form = QFormLayout()
        for key, label in self.tools:
            row = QHBoxLayout()
            edit = QLineEdit()
            edit.setPlaceholderText(f"例: C:\\Program Files\\{label}")
            self.path_edits[key] = edit
            row.addWidget(edit, 1)
            btn_browse = QPushButton("📁 参照")
            btn_browse.setMaximumWidth(75)
            btn_browse.clicked.connect(lambda checked, k=key: self.on_browse_tool(k))
            row.addWidget(btn_browse)
            btn_check = QPushButton("🔍 確認")
            btn_check.setMaximumWidth(75)
            btn_check.clicked.connect(lambda checked, k=key, l=label: self.check_single_path(k, label=l, path_type='tool', show_popup=True))
            row.addWidget(btn_check)
            status_lbl = QLabel("未確認")
            status_lbl.setMinimumWidth(110)
            status_lbl.setStyleSheet("color: #888888;")
            self.status_labels[key] = status_lbl
            row.addWidget(status_lbl)
            form.addRow(f"{label}:", row)
        row_ffs_config = QHBoxLayout()
        edit_ffs_config = QLineEdit()
        edit_ffs_config.setPlaceholderText("例: C:\\Users\\...\\Sync-Files Music.ffs_gui")
        self.path_edits["FreeFileSync_Config"] = edit_ffs_config
        row_ffs_config.addWidget(edit_ffs_config, 1)
        btn_ffs_config_browse = QPushButton("📁 参照")
        btn_ffs_config_browse.setMaximumWidth(75)
        btn_ffs_config_browse.clicked.connect(lambda checked: self.on_browse_ffs_config())
        row_ffs_config.addWidget(btn_ffs_config_browse)
        btn_ffs_config_check = QPushButton("🔍 確認")
        btn_ffs_config_check.setMaximumWidth(75)
        btn_ffs_config_check.clicked.connect(lambda checked: self.check_single_path("FreeFileSync_Config", label="FreeFileSync設定ファイル", path_type='file', show_popup=True))
        row_ffs_config.addWidget(btn_ffs_config_check)
        status_lbl_ffs = QLabel("未確認")
        status_lbl_ffs.setMinimumWidth(110)
        status_lbl_ffs.setStyleSheet("color: #888888;")
        self.status_labels["FreeFileSync_Config"] = status_lbl_ffs
        row_ffs_config.addWidget(status_lbl_ffs)
        form.addRow("FreeFileSync設定ファイル:", row_ffs_config)
        layout.addLayout(form)
        layout.addStretch()
        return widget
    
    def create_quality_tab(self) -> QWidget:
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
        spin_jpeg = QSpinBox()
        spin_jpeg.setRange(1, 100)
        spin_jpeg.setValue(85)
        spin_jpeg.setSuffix(" %")
        self.quality_spins["JpegQuality"] = spin_jpeg
        form.addRow("JPEG 品質:", spin_jpeg)
        spin_webp = QSpinBox()
        spin_webp.setRange(1, 100)
        spin_webp.setValue(85)
        spin_webp.setSuffix(" %")
        self.quality_spins["WebpQuality"] = spin_webp
        form.addRow("WebP 品質:", spin_webp)
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
        list_label = QLabel("登録済みキーワード:")
        layout.addWidget(list_label)
        self.keyword_list = QListWidget()
        self.keyword_list.setMinimumHeight(250)
        self.keyword_list.setSelectionMode(QListWidget.MultiSelection)
        layout.addWidget(self.keyword_list)
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
        text = self.keyword_input.text().strip()
        if not text:
            return
        keywords = [kw.strip() for kw in text.split(',') if kw.strip()]
        existing_keywords = [self.keyword_list.item(i).text() 
                           for i in range(self.keyword_list.count())]
        for keyword in keywords:
            if keyword.lower() not in [k.lower() for k in existing_keywords]:
                self.keyword_list.addItem(keyword)
        self.keyword_input.clear()
    
    def on_remove_keywords(self):
        selected_items = self.keyword_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "削除", "削除するキーワードを選択してください。")
            return
        for item in selected_items:
            self.keyword_list.takeItem(self.keyword_list.row(item))
    
    def on_clear_keywords(self):
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
    
    def check_single_path(self, key: str, label: str = "", path_type: str = 'file', show_popup: bool = False) -> tuple[bool, str, str]:
        edit = self.dir_edits.get(key) or self.path_edits.get(key)
        path_text = edit.text().strip() if edit else ""
        name = label if label else key
        
        if not path_text:
            if path_type == 'dir':
                status = "⚠️ 未設定 (必須)"
                color = "#d9534f"
                msg = f"【{name}】\nディレクトリが設定されていません。（必須項目です）"
                is_ok = False
            else:
                status = "ℹ️ 未設定"
                color = "#6c757d"
                msg = f"【{name}】\nパスが設定されていません。"
                is_ok = False
        else:
            expanded = ConfigManager.expand_path(path_text)
            if path_type == 'dir':
                if os.path.isdir(expanded):
                    status = "✅ 存在"
                    color = "#28a745"
                    msg = f"【{name}】\nディレクトリが存在します。\n\nパス:\n{expanded}"
                    is_ok = True
                elif os.path.isfile(expanded):
                    status = "❌ ファイルです"
                    color = "#dc3545"
                    msg = f"【{name}】\nディレクトリではなくファイルが指定されています。\n\nパス:\n{expanded}"
                    is_ok = False
                else:
                    status = "❌ 存在しません"
                    color = "#dc3545"
                    msg = f"【{name}】\n指定されたディレクトリが見つかりません。\n\nパス:\n{expanded}"
                    is_ok = False
            else:
                if os.path.isfile(expanded) or (os.path.exists(expanded) and not os.path.isdir(expanded)):
                    status = "✅ 存在"
                    color = "#28a745"
                    msg = f"【{name}】\nファイルが存在します。\n\nパス:\n{expanded}"
                    is_ok = True
                elif os.path.isdir(expanded):
                    status = "❌ フォルダです"
                    color = "#dc3545"
                    msg = f"【{name}】\nファイルではなくフォルダが指定されています。\n\nパス:\n{expanded}"
                    is_ok = False
                else:
                    status = "❌ 存在しません"
                    color = "#dc3545"
                    msg = f"【{name}】\n指定されたファイルが見つかりません。\n\nパス:\n{expanded}"
                    is_ok = False
        
        lbl = self.status_labels.get(key)
        if lbl:
            lbl.setText(status)
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            lbl.setToolTip(msg)
        
        if show_popup:
            if is_ok or (not path_text and path_type != 'dir'):
                QMessageBox.information(self, f"{name} - 確認結果", msg)
            else:
                QMessageBox.warning(self, f"{name} - 確認結果", msg)
                
        return is_ok, status, msg
    
    def check_all_directories(self, show_summary: bool = True):
        results = []
        for key, label, _ in self.directories:
            is_ok, status, _ = self.check_single_path(key, label=label, path_type='dir', show_popup=False)
            edit = self.dir_edits.get(key)
            raw_path = edit.text().strip() if edit else ""
            results.append((label, raw_path, is_ok, status))
        if show_summary:
            self._show_summary_dialog("ディレクトリ存在確認結果", results)

    def check_all_tools(self, show_summary: bool = True):
        results = []
        for key, label in self.tools:
            is_ok, status, _ = self.check_single_path(key, label=label, path_type='tool', show_popup=False)
            edit = self.path_edits.get(key)
            raw_path = edit.text().strip() if edit else ""
            results.append((label, raw_path, is_ok, status))
        is_ok, status, _ = self.check_single_path("FreeFileSync_Config", label="FreeFileSync設定ファイル", path_type='file', show_popup=False)
        edit = self.path_edits.get("FreeFileSync_Config")
        raw_path = edit.text().strip() if edit else ""
        results.append(("FreeFileSync設定ファイル", raw_path, is_ok, status))
        if show_summary:
            self._show_summary_dialog("ツールパス存在確認結果", results)

    def check_all_settings(self):
        results = []
        for key, label, _ in self.directories:
            is_ok, status, _ = self.check_single_path(key, label=label, path_type='dir', show_popup=False)
            edit = self.dir_edits.get(key)
            raw_path = edit.text().strip() if edit else ""
            results.append((f"[ディレクトリ] {label}", raw_path, is_ok, status))
        for key, label in self.tools:
            is_ok, status, _ = self.check_single_path(key, label=label, path_type='tool', show_popup=False)
            edit = self.path_edits.get(key)
            raw_path = edit.text().strip() if edit else ""
            results.append((f"[ツール] {label}", raw_path, is_ok, status))
        is_ok, status, _ = self.check_single_path("FreeFileSync_Config", label="FreeFileSync設定ファイル", path_type='file', show_popup=False)
        edit = self.path_edits.get("FreeFileSync_Config")
        raw_path = edit.text().strip() if edit else ""
        results.append(("[設定ファイル] FreeFileSync設定ファイル", raw_path, is_ok, status))
        self._show_summary_dialog("全設定パス一括確認結果", results)

    def _show_summary_dialog(self, title: str, results: list[tuple[str, str, bool, str]]):
        total = len(results)
        ok_count = sum(1 for _, _, is_ok, _ in results if is_ok)
        empty_count = sum(1 for _, path, is_ok, _ in results if not path and not is_ok)
        error_count = total - ok_count - empty_count
        lines = [
            f"<h3>{title}</h3>",
            f"<p>合計: <b>{total}</b> 件 (✅ 存在: <b>{ok_count}</b> / ❌ 未存在: <b>{error_count}</b> / ℹ️ 未設定: <b>{empty_count}</b>)</p>",
            "<hr>",
            "<table border='1' cellpadding='4' cellspacing='0' style='border-collapse: collapse; width: 100%;'>",
            "<tr bgcolor='#f2f2f2'><th align='left'>項目</th><th align='center'>状態</th><th align='left'>パス</th></tr>"
        ]
        for label, raw_path, is_ok, status in results:
            expanded = ConfigManager.expand_path(raw_path) if raw_path else "（未設定）"
            lines.append(f"<tr><td><b>{label}</b></td><td align='center'>{status}</td><td style='font-size: 11px; color: #333;'>{expanded}</td></tr>")
        lines.append("</table>")
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText("".join(lines))
        if error_count > 0:
            msg_box.setIcon(QMessageBox.Warning)
        else:
            msg_box.setIcon(QMessageBox.Information)
        msg_box.exec()

    def load_settings(self):
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
        for key, edit in self.path_edits.items():
            if key == "FreeFileSync_Config":
                path = self.config.config.get('Paths', 'freefilesync_config', fallback='')
            else:
                path = self.config.get_tool_path(key) or self.config.config.get('Paths', key, fallback='')
            if path:
                edit.setText(path)
        self.quality_spins["JpegQuality"].setValue(int(self.config.get_setting("JpegQuality", "85")))
        self.quality_spins["WebpQuality"].setValue(int(self.config.get_setting("WebpQuality", "85")))
        self.quality_spins["ResizeWidth"].setValue(int(self.config.get_setting("ResizeWidth", "600")))
        keywords = self.config.get_demucs_keywords()
        if keywords:
            for keyword in keywords:
                self.keyword_list.addItem(keyword)
        self.check_all_directories(show_summary=False)
        self.check_all_tools(show_summary=False)
    
    def on_browse_tool(self, key: str):
        path, _ = QFileDialog.getOpenFileName(
            self,
            f"{key} を選択",
            "",
            "実行ファイル (*.exe);;すべてのファイル (*.*)"
        )
        if path:
            self.path_edits[key].setText(os.path.normpath(path))
            self.check_single_path(key, path_type='tool', show_popup=False)
    
    def on_browse_ffs_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "FreeFileSync設定ファイルを選択",
            "",
            "FreeFileSync設定 (*.ffs_gui);;すべてのファイル (*.*)"
        )
        if path:
            self.path_edits["FreeFileSync_Config"].setText(os.path.normpath(path))
            self.check_single_path("FreeFileSync_Config", label="FreeFileSync設定ファイル", path_type='file', show_popup=False)
    
    def on_save(self):
        try:
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
            for key, edit in self.path_edits.items():
                path = edit.text().strip()
                if key == "FreeFileSync_Config":
                    if path:
                        self.config.config['Paths']['freefilesync_config'] = path
                    else:
                        if 'freefilesync_config' in self.config.config['Paths']:
                            del self.config.config['Paths']['freefilesync_config']
                else:
                    if path:
                        self.config.config['Paths'][key] = path
                    else:
                        if key in self.config.config['Paths']:
                            del self.config.config['Paths'][key]
            if 'Artwork' not in self.config.config:
                self.config.config['Artwork'] = {}
            if 'Settings' not in self.config.config:
                self.config.config['Settings'] = {}
            jpeg_val = str(self.quality_spins["JpegQuality"].value())
            webp_val = str(self.quality_spins["WebpQuality"].value())
            width_val = str(self.quality_spins["ResizeWidth"].value())
            self.config.config['Artwork']['JpegQuality'] = jpeg_val
            self.config.config['Artwork']['WebpQuality'] = webp_val
            self.config.config['Artwork']['ResizeWidth'] = width_val
            self.config.config['Settings']['JpegQuality'] = jpeg_val
            self.config.config['Settings']['WebpQuality'] = webp_val
            self.config.config['Settings']['ResizeWidth'] = width_val
            if 'Demucs' not in self.config.config:
                self.config.config['Demucs'] = {}
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
            if self.config.save():
                QMessageBox.information(self, "保存完了", "設定を保存しました。")
                self.accept()
            else:
                QMessageBox.critical(self, "エラー", "設定の保存に失敗しました。")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"設定の保存中にエラーが発生しました:\n{e}")

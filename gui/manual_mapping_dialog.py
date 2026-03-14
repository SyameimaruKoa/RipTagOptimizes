"""
手動紐づけダイアログ - originalFile と currentFile の手動マッピング
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt


class ManualMappingDialog(QDialog):
    """手動紐づけダイアログ"""
    
    def __init__(self, tracks, actual_files, parent=None):
        super().__init__(parent)
        self.tracks = tracks.copy()  # トラック情報のコピー
        self.actual_files = actual_files  # 実際のファイル一覧
        
        self.setWindowTitle("手動紐づけ")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        
        self.init_ui()
        self.load_mappings()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel("<h2>🔗 手動紐づけ</h2>")
        layout.addWidget(title)
        
        # 説明
        desc = QLabel(
            "元のファイル名 (originalFile) と現在のファイル名 (currentFile) を手動で設定します。\n"
            "各行で現在のファイルを選択してください。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # テーブル
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["元のファイル名", "現在のファイル名", "トラックID"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        self.auto_match_button = QPushButton("自動マッチング")
        self.auto_match_button.setToolTip("ファイル名の類似度から自動で紐づけを試みます")
        self.auto_match_button.clicked.connect(self.on_auto_match)
        button_layout.addWidget(self.auto_match_button)
        
        button_layout.addStretch()
        
        self.save_button = QPushButton("保存")
        self.save_button.setMinimumHeight(35)
        self.save_button.clicked.connect(self.accept)
        button_layout.addWidget(self.save_button)
        
        self.cancel_button = QPushButton("キャンセル")
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_mappings(self):
        """現在の紐づけ情報をテーブルに読み込み"""
        self.table.setRowCount(len(self.tracks))
        
        for row, track in enumerate(self.tracks):
            # 元のファイル名
            original_file = track.get("originalFile", "")
            original_item = QTableWidgetItem(original_file)
            original_item.setFlags(original_item.flags() & ~Qt.ItemIsEditable)  # 編集不可
            self.table.setItem(row, 0, original_item)
            
            # 現在のファイル名（コンボボックス）
            current_combo = QComboBox()
            current_combo.addItem("")  # 空白オプション
            for file in self.actual_files:
                current_combo.addItem(file)
            
            # 既存の値を設定
            current_file = track.get("currentFile", "")
            index = current_combo.findText(current_file)
            if index >= 0:
                current_combo.setCurrentIndex(index)
            
            self.table.setCellWidget(row, 1, current_combo)
            
            # トラックID
            track_id = str(track.get("id", ""))
            id_item = QTableWidgetItem(track_id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)  # 編集不可
            self.table.setItem(row, 2, id_item)
    
    def on_auto_match(self):
        """自動マッチング - ファイル名の類似度から推測"""
        import difflib
        
        matched_count = 0
        
        for row in range(self.table.rowCount()):
            original_item = self.table.item(row, 0)
            if not original_item:
                continue
            
            original_file = original_item.text()
            
            # 拡張子を除いて正規化
            import re
            def normalize(s):
                base = re.sub(r'\.[^.]+$', '', s)  # 拡張子除去
                base = re.sub(r'^\d+[\s\-\.]*', '', base)  # トラック番号除去
                return base.strip().lower()
            
            original_norm = normalize(original_file)
            
            # 最も類似度の高いファイルを検索
            best_match = None
            best_ratio = 0.0
            
            # 親ウィジェット（Step3TaggingPanel）が _is_instrumental_by_name を持っているか確認
            is_inst_func = None
            if hasattr(self.parent(), "_is_instrumental_by_name"):
                is_inst_func = self.parent()._is_instrumental_by_name

            orig_is_inst = is_inst_func(original_file.lower()) if is_inst_func else False

            for actual_file in self.actual_files:
                # ボーカル曲に対してインストがマッチしないようにする（逆も然り）
                if is_inst_func:
                    actual_is_inst = is_inst_func(actual_file.lower())
                    if orig_is_inst != actual_is_inst:
                        continue

                    best_ratio = ratio
                    best_match = actual_file
            
            # 類似度が一定以上なら設定（閾値: 0.6）
            if best_match and best_ratio >= 0.6:
                combo = self.table.cellWidget(row, 1)
                if isinstance(combo, QComboBox):
                    index = combo.findText(best_match)
                    if index >= 0:
                        combo.setCurrentIndex(index)
                        matched_count += 1
        
        QMessageBox.information(
            self,
            "自動マッチング完了",
            f"{matched_count} 件のファイルを自動マッチングしました。\n\n"
            "必要に応じて手動で調整してください。"
        )
    
    def get_updated_tracks(self):
        """更新されたトラック情報を返す"""
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, 1)
            if isinstance(combo, QComboBox):
                current_file = combo.currentText()
                self.tracks[row]["currentFile"] = current_file
        
        return self.tracks

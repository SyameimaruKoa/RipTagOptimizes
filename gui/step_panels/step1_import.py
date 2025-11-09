"""
Step 1: 新規取り込みパネル
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QMessageBox, QProgressDialog
)
from PySide6.QtCore import Signal, QThread

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager
from logic.state_manager import StateManager
import shutil
from send2trash import send2trash


class ImportWorker(QThread):
    """取り込み処理を別スレッドで実行（FastCopy廃止、標準のshutil.moveを使用）"""
    finished = Signal(bool, str)  # success, message

    def __init__(self, source: str, dest_folder: str):
        super().__init__()
        self.source = source
        self.dest_folder = dest_folder

    def run(self):
        try:
            # 親ディレクトリを確実に作成
            os.makedirs(os.path.dirname(self.dest_folder), exist_ok=True)
            shutil.move(self.source, self.dest_folder)
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class Step1ImportPanel(QWidget):
    """Step 1: 新規取り込みパネル"""
    
    import_completed = Signal(str)  # album_folder
    
    def __init__(self, config: ConfigManager, workflow: WorkflowManager):
        super().__init__()
        self.config = config
        self.workflow = workflow
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel("<h2>Step 1: 新規取り込み</h2>")
        layout.addWidget(title)
        
        # 説明
        desc = QLabel(
            "Music Center からアルバムフォルダを選択し、作業フォルダに移動します。\n"
            "移動後、自動的に state.json が作成され、ワークフローが開始されます。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        # 選択されたフォルダ表示
        self.selected_folder_label = QLabel("選択: (なし)")
        layout.addWidget(self.selected_folder_label)
        
        layout.addSpacing(10)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("フォルダを選択")
        self.select_button.clicked.connect(self.on_select_folder)
        button_layout.addWidget(self.select_button)
        
        self.import_button = QPushButton("取り込み開始")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.on_import)
        button_layout.addWidget(self.import_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # 選択されたフォルダ
        self.selected_source = None
    
    def load_album(self, album_folder: str):
        """アルバムを読み込み（このパネルでは何もしない）"""
        # Step1は新規取り込み用なので、既存アルバムを読み込む必要はない
        pass
    
    def reset(self):
        """パネルの状態をリセット（新規取り込み開始時）"""
        self.selected_source = None
        self.selected_folder_label.setText("選択: (なし)")
        self.import_button.setEnabled(False)
    
    def on_select_folder(self):
        """フォルダ選択ボタンが押されたときの処理"""
        music_center_dir = self.config.get_directory("MusicCenterDir")
        
        folder = QFileDialog.getExistingDirectory(
            self,
            "取り込むアルバムフォルダを選択",
            music_center_dir if music_center_dir else ""
        )
        
        if not folder:
            return
        
        self.selected_source = folder
        self.selected_folder_label.setText(f"選択: {folder}")
        self.import_button.setEnabled(True)
    
    def on_import(self):
        """取り込み開始ボタンが押されたときの処理"""
        if not self.selected_source:
            return
        
        # パス解析: アーティスト名・アルバム名を取得
        # 想定パス: .../ArtistName/AlbumName
        album_name = os.path.basename(self.selected_source)
        artist_name = os.path.basename(os.path.dirname(self.selected_source))
        
        # 作業フォルダのパス
        work_dir = self.config.get_directory("WorkDir")
        if not work_dir:
            QMessageBox.warning(self, "エラー", "WorkDir が設定されていません。")
            return
        
        # work フォルダが存在しない場合は作成
        if not os.path.exists(work_dir):
            try:
                os.makedirs(work_dir)
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"作業フォルダの作成に失敗しました:\n{e}")
                return
        
        dest_folder = os.path.join(work_dir, album_name)
        
        # 競合チェック
        if os.path.exists(dest_folder):
            reply = QMessageBox.question(
                self,
                "競合",
                f"作業フォルダに既に '{album_name}' が存在します。\n\n"
                f"既存のフォルダをゴミ箱に移動して上書きしますか?\n"
                f"(※データが失われる可能性があります)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # ゴミ箱に移動
            try:
                send2trash(dest_folder)
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"既存フォルダの削除に失敗しました:\n{e}")
                return
        
        # プログレスダイアログ
        progress = QProgressDialog("移動中...", "キャンセル", 0, 0, self)
        progress.setWindowTitle("取り込み中")
        progress.setModal(True)
        progress.setCancelButton(None)
        progress.show()
        
        # ワーカースレッドで実行
        self.import_worker = ImportWorker(self.selected_source, dest_folder)
        self.import_worker.finished.connect(
            lambda success, msg: self.on_import_finished(success, msg, progress, dest_folder, album_name, artist_name)
        )
        self.import_worker.start()
    
    def on_import_finished(self, success, error_msg, progress, dest_folder, album_name, artist_name):
        """取り込み完了時の処理"""
        progress.close()
        
        if not success:
            QMessageBox.critical(self, "エラー", f"取り込みに失敗しました:\n{error_msg}")
            return
        
        # state.json を初期化
        # 取り込み直後の FLAC をサブフォルダ _flac_src に隔離
        flac_src_dir = os.path.join(dest_folder, "_flac_src")
        try:
            os.makedirs(flac_src_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"_flac_src フォルダ作成に失敗しました:\n{e}")
            return

        moved_count = 0
        try:
            for file in list(os.listdir(dest_folder)):
                if file.lower().endswith('.flac'):
                    src = os.path.join(dest_folder, file)
                    dst = os.path.join(flac_src_dir, file)
                    try:
                        os.replace(src, dst)
                        moved_count += 1
                    except Exception as e:
                        print(f"[WARN] FLAC移動失敗: {file}: {e}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"FLACファイル移動処理に失敗しました:\n{e}")
            return

        # _flac_src 内の .flac を列挙
        flac_files = []
        try:
            for file in os.listdir(flac_src_dir):
                if file.lower().endswith('.flac'):
                    flac_files.append(file)
            flac_files.sort()
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"_flac_src 内の FLAC 検索に失敗しました:\n{e}")
            return
        
        if not flac_files:
            QMessageBox.warning(self, "警告", "取り込んだフォルダに FLAC ファイルが見つかりませんでした。")
            return
        
        # StateManager で初期化（rawFlacSrc パスを保持済み）
        state = StateManager(dest_folder)
        if not state.initialize(album_name, artist_name, flac_files):
            QMessageBox.critical(self, "エラー", "state.json の作成に失敗しました。")
            return
        
        QMessageBox.information(
            self,
            "完了",
            f"取り込みが完了しました!\n\n"
            f"アルバム: {album_name}\n"
            f"トラック数: {len(flac_files)}\nFLAC隔離: {moved_count} ファイルを _flac_src へ移動"
        )
        
        # リセット
        self.selected_source = None
        self.selected_folder_label.setText("選択: (なし)")
        self.import_button.setEnabled(False)
        
        # 完了シグナルを発火
        self.import_completed.emit(dest_folder)

"""
Step 4: AAC 変換（MediaHuman連携）パネル
- ユーザー要望により、MediaHuman GUI に追加すべき入力フォルダのフルパスを提示
- 出力は MediaHuman 側で生成された m4a をマスターGUIが取り込み（_aac_output へ集約）
"""
from __future__ import annotations
import os
from typing import List, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Signal, QTimer

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager


class Step4AacPanel(QWidget):
    step_completed = Signal()

    def __init__(self, config: ConfigManager, workflow: WorkflowManager):
        super().__init__()
        self.config = config
        self.workflow = workflow
        # フィールド（実行時用。型注釈は付けずに環境依存の警告を回避）
        self.album_folder = None
        self.input_folder = None  # MediaHuman への入力（_flac_src 優先）
        self.init_ui()
        # MediaHuman 起動/監視
        self.mediahuman_proc = None
        self._mh_timer = QTimer(self)
        self._mh_timer.setInterval(1000)
        self._mh_timer.timeout.connect(self._check_mediahuman_status)

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("<h2>Step 4: AAC変換 (MediaHuman 連携)</h2>")
        layout.addWidget(title)

        desc = QLabel(
            "MediaHuman GUI に追加する『入力フォルダのフルパス』を下に一覧表示します。\n"
            "MediaHuman 側で変換実行後、[出力を取り込む] を押すと .m4a を _aac_output へ集約します。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(6)

        layout.addWidget(QLabel("<b>MediaHuman に追加するフォルダ:</b>"))
        self.folder_list = QListWidget()
        layout.addWidget(self.folder_list)

        btns = QHBoxLayout()
        self.btn_copy = QPushButton("リストをクリップボードへコピー")
        self.btn_copy.clicked.connect(self.on_copy_to_clipboard)
        btns.addWidget(self.btn_copy)

        self.btn_launch = QPushButton("MediaHuman を起動")
        self.btn_launch.clicked.connect(self.on_launch_mediahuman)
        btns.addWidget(self.btn_launch)

        btns.addStretch()
        layout.addLayout(btns)

        layout.addSpacing(6)

        layout.addWidget(QLabel("<b>変換結果の取り込み:</b>"))
        action = QHBoxLayout()
        self.btn_ingest = QPushButton("出力を取り込む（.m4a を _aac_output へ）")
        self.btn_ingest.clicked.connect(self.on_ingest_outputs)
        action.addWidget(self.btn_ingest)

        self.btn_complete = QPushButton("Step 4 完了")
        self.btn_complete.clicked.connect(self.on_complete)
        action.addWidget(self.btn_complete)
        action.addStretch()
        layout.addLayout(action)
        layout.addStretch()

    def load_album(self, album_folder: str):
        self.album_folder = album_folder
        # _flac_src を優先的に使う
        self.input_folder = self._resolve_input_folder(album_folder)
        self.refresh_folder_list()

    # ------------------------
    # actions
    # ------------------------
    def refresh_folder_list(self):
        """MediaHuman に追加すべき入力フォルダ（_flac_src 優先）を1件表示し、参考として対象ファイルも列挙。"""
        self.folder_list.clear()
        if (not self.workflow.state) or (not self.album_folder):
            return

        # 入力フォルダ: _flac_src 優先（無ければアルバムルート）
        add_path = self.input_folder or self.album_folder
        item = QListWidgetItem(add_path)
        item.setToolTip("このフォルダを MediaHuman GUI に追加してください")
        self.folder_list.addItem(item)

        # 参考: 変換対象ファイルリスト（finalFile / instrumentalFile）
        self.folder_list.addItem(QListWidgetItem("---- 参考: 変換対象候補 (この行は MediaHuman 追加には不要) ----"))
        list_files = []
        for t in (self.workflow.state.get_tracks() or []):
            ff = t.get("finalFile")
            if ff:
                list_files.append(ff)
            inst = t.get("instrumentalFile")
            if inst:
                list_files.append(inst)
        for f in sorted(set(list_files)):
            self.folder_list.addItem(QListWidgetItem(f"  - {f}"))

    def on_copy_to_clipboard(self):
        # クリップボードへフォルダパスをコピー
        from PySide6.QtGui import QGuiApplication
        if not self.album_folder:
            return
        target = self.input_folder or self.album_folder
        QGuiApplication.clipboard().setText(target)
        QMessageBox.information(self, "コピー", "入力フォルダのフルパスをコピーしました。\nMediaHuman に貼り付けてください。")

    def on_launch_mediahuman(self):
        # 起動時に自動で入力パスをコピー
        try:
            from PySide6.QtGui import QGuiApplication
            target = self.input_folder or self.album_folder
            if target:
                QGuiApplication.clipboard().setText(target)
        except Exception:
            pass
        exe = self.config.get_tool_path("MediaHuman")
        if not exe:
            QMessageBox.warning(self, "警告", "MediaHuman のパスが設定されていません (config.ini)。")
            return
        # 起動してプロセスを監視
        try:
            import subprocess
            # 既に起動中なら新規起動はせず状態監視のみ継続
            if self.mediahuman_proc is not None and self.mediahuman_proc.poll() is None:
                return
            self.mediahuman_proc = subprocess.Popen([exe])
            self._mh_timer.start()
        except Exception as e:
            QMessageBox.critical(self, "起動失敗", str(e))

    def on_ingest_outputs(self, init_dir: str | None = None):
        """MediaHuman の出力から .m4a を取り込み、_aac_output に集約する。
        - 想定: MediaHuman の出力先はユーザー側設定。
        - 取り込み方法: ダイアログで出力フォルダを選んでもらい、そこから .m4a をコピー。
        """
        from PySide6.QtWidgets import QFileDialog
        if not self.album_folder or not self.workflow.state:
            return

        # 既定の初期位置（設定で変更可）
        try:
            default_dir = self.config.get_setting("ExternalOutputDir", r"C:\\Users\\kouki\\Videos\\エンコード済み")
        except Exception:
            default_dir = r"C:\\Users\\kouki\\Videos\\エンコード済み"
        start_dir = init_dir or default_dir
        src = QFileDialog.getExistingDirectory(self, "MediaHuman の出力フォルダを選択", start_dir)
        if not src:
            return

        # 出力先
        aac_dir_name = self.workflow.state.get_path("aacOutput")
        dst = os.path.join(self.album_folder, aac_dir_name)
        os.makedirs(dst, exist_ok=True)

        import shutil
        count = 0
        for name in os.listdir(src):
            if name.lower().endswith(".m4a"):
                src_file = os.path.join(src, name)
                dst_file = os.path.join(dst, name)
                try:
                    if os.path.exists(dst_file):
                        # 既存ファイルは上書き前に削除
                        os.remove(dst_file)
                    shutil.move(src_file, dst_file)
                    count += 1
                except Exception as e:
                    print(f"[ERROR] move failed: {e}")
        self.folder_list.addItem(QListWidgetItem(f"取り込み (移動) 完了: {count} ファイル"))

    def on_complete(self):
        """Step4 完了: 取り込み数で簡易チェックし、次へ進む"""
        if not self.album_folder or not self.workflow.state:
            return
        dst = os.path.join(self.album_folder, self.workflow.state.get_path("aacOutput"))
        got = 0
        if os.path.exists(dst):
            got = len([f for f in os.listdir(dst) if f.lower().endswith('.m4a')])
        total = 0
        for t in self.workflow.state.get_tracks():
            if t.get("finalFile"): total += 1
            if t.get("instrumentalFile"): total += 1
        if got < total:
            # 不足はログだけ（モーダル削減）
            self.folder_list.addItem(QListWidgetItem(f"[WARN] AAC不足 {got}/{total}"))
            return
        self.step_completed.emit()

    # ------------------------
    # helpers
    # ------------------------
    def _resolve_input_folder(self, album_folder: str) -> str | None:
        """_flac_src を優先的に返す。無ければアルバムルート。"""
        try:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") if self.workflow and self.workflow.state else "_flac_src"
        except Exception:
            raw_dirname = "_flac_src"
        candidate = os.path.join(album_folder, raw_dirname)
        return candidate if os.path.isdir(candidate) else album_folder

    def _check_mediahuman_status(self):
        """MediaHuman の終了検出後、自動で取り込みダイアログを表示"""
        if self.mediahuman_proc is None:
            self._mh_timer.stop()
            return
        try:
            if self.mediahuman_proc.poll() is None:
                return  # 実行中
            # 終了
            self._mh_timer.stop()
            self.mediahuman_proc = None
            # 自動で取り込みダイアログを表示
            try:
                default_dir = self.config.get_setting("ExternalOutputDir", r"C:\\Users\\kouki\\Videos\\エンコード済み")
            except Exception:
                default_dir = r"C:\\Users\\kouki\\Videos\\エンコード済み"
            self.on_ingest_outputs(default_dir)
        except Exception:
            self._mh_timer.stop()
            self.mediahuman_proc = None

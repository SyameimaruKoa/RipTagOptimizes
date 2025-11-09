"""
Step 5: Opus変換 (foobar2000)

ユーザーは foobar2000 GUI を使って Opus へ変換し、その出力フォルダを本パネルで取り込み。
取り込み後、曲数検証に通れば完了ボタンで次ステップへ進む。
"""
from __future__ import annotations
import os
from typing import Optional
from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QMessageBox
)

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager


class Step5OpusPanel(QWidget):
    step_completed = Signal()

    def __init__(self, config: ConfigManager, workflow: WorkflowManager):
        super().__init__()
        self.config = config
        self.workflow = workflow
        self.album_folder: Optional[str] = None
        self.input_folder: Optional[str] = None  # foobar2000 に追加する実フォルダ（_flac_src 優先）
        self.foobar_proc = None
        self._proc_timer = QTimer(self)
        self._proc_timer.setInterval(1000)
        self._proc_timer.timeout.connect(self._check_foobar_status)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Step 5: Opus変換 (foobar2000)</h2>"))
        desc = QLabel(
            "1. アルバムフォルダを foobar2000 にドラッグして Opus へ変換してください。\n"
            "2. 変換後 [Opus出力取り込み] で .opus を _opus_output に集約。\n"
            "3. 曲数が揃ったら [Step 5 完了]。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addWidget(QLabel("<b>入力フォルダ（foobar2000に追加）:</b>"))
        self.album_label = QLabel("未選択")
        layout.addWidget(self.album_label)

        # foobar2000 起動/状態
        launch_row = QHBoxLayout()
        self.btn_launch = QPushButton("foobar2000 を起動")
        self.btn_launch.clicked.connect(self.on_launch_foobar)
        launch_row.addWidget(self.btn_launch)
        self.foobar_status = QLabel("未起動")
        launch_row.addWidget(self.foobar_status)
        launch_row.addStretch()
        layout.addLayout(launch_row)

        layout.addWidget(QLabel("<b>取り込みログ:</b>"))
        self.log_list = QListWidget()
        layout.addWidget(self.log_list)

        btn_row = QHBoxLayout()
        self.btn_copy_path = QPushButton("アルバムパスをコピー")
        self.btn_copy_path.clicked.connect(self.on_copy_path)
        btn_row.addWidget(self.btn_copy_path)

        self.btn_ingest = QPushButton("Opus出力取り込み")
        self.btn_ingest.clicked.connect(self.on_ingest)
        btn_row.addWidget(self.btn_ingest)

        self.btn_complete = QPushButton("Step 5 完了")
        self.btn_complete.clicked.connect(self.on_complete)
        btn_row.addWidget(self.btn_complete)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        layout.addStretch()

    def load_album(self, album_folder: str):
        if self.album_folder == album_folder:
            return
        self.album_folder = album_folder
        # foobar に渡す入力は _flac_src を優先
        flac_src = None
        try:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") if self.workflow and self.workflow.state else "_flac_src"
            candidate = os.path.join(album_folder, raw_dirname)
            if os.path.isdir(candidate):
                flac_src = candidate
        except Exception:
            flac_src = None
        self.input_folder = flac_src or album_folder
        self.album_label.setText(self.input_folder)
        self.log_list.clear()
        self.foobar_status.setText("未起動")

    def on_copy_path(self):
        from PySide6.QtGui import QGuiApplication
        if not self.input_folder:
            return
        QGuiApplication.clipboard().setText(self.input_folder)
        QMessageBox.information(self, "コピー", "アルバムフォルダパスをクリップボードへコピーしました。")

    def on_launch_foobar(self):
        import subprocess
        # 起動時に自動で入力パスをコピー
        try:
            from PySide6.QtGui import QGuiApplication
            if self.input_folder:
                QGuiApplication.clipboard().setText(self.input_folder)
        except Exception:
            pass
        exe = self.config.get_tool_path("Foobar2000")
        if not exe:
            QMessageBox.warning(self, "未設定", "config.ini の Paths.Foobar2000 に foobar2000 のパスを設定してください。")
            return
        try:
            # 既に起動中なら新規起動はせず状態表示のみ更新
            if self.foobar_proc is not None and self.foobar_proc.poll() is None:
                self.foobar_status.setText("起動中")
                return
            # 設定で /add を使って自動追加（既定: 有効）
            try:
                use_add = str(self.config.get_setting("FoobarUseAddSwitch", "1")).strip() not in ("0", "false", "False")
            except Exception:
                use_add = True
            args = [exe]
            if use_add and self.input_folder and os.path.isdir(self.input_folder):
                # フォルダを現在のプレイリストに追加し、即時追加遅延を抑制して表示
                args += ["/add", self.input_folder, "/immediate", "/show"]
                self.log_list.addItem(QListWidgetItem(f"/add で自動追加: {self.input_folder}"))
            self.foobar_proc = subprocess.Popen(args)
            self.foobar_status.setText("起動中…")
            self._proc_timer.start()
        except Exception as e:
            QMessageBox.critical(self, "起動失敗", str(e))

    def on_ingest(self, init_dir: Optional[str] = None):
        if not self.album_folder or not self.workflow.state:
            return
        start_dir = init_dir or self.album_folder
        src = QFileDialog.getExistingDirectory(self, "Opus出力フォルダを選択", start_dir)
        if not src:
            return
        dst_name = self.workflow.state.get_path("opusOutput")
        dst = os.path.join(self.album_folder, dst_name)
        os.makedirs(dst, exist_ok=True)
        import shutil
        count = 0
        for name in os.listdir(src):
            if name.lower().endswith('.opus'):
                src_file = os.path.join(src, name)
                dst_file = os.path.join(dst, name)
                try:
                    if os.path.exists(dst_file):
                        os.remove(dst_file)
                    shutil.move(src_file, dst_file)
                    count += 1
                except Exception as e:
                    self.log_list.addItem(QListWidgetItem(f"ERROR move {name}: {e}"))
        self.log_list.addItem(QListWidgetItem(f"取り込み (移動) 完了: {count} ファイル"))

    def _check_foobar_status(self):
        # 当パネルから起動した foobar2000 の終了検出
        if self.foobar_proc is None:
            self.foobar_status.setText("未起動")
            self._proc_timer.stop()
            return
        try:
            if self.foobar_proc.poll() is None:
                # 実行中
                self.foobar_status.setText("起動中")
            else:
                # 終了
                self.foobar_status.setText("終了しました")
                self._proc_timer.stop()
                self.foobar_proc = None
                # 終了後 自動取り込みダイアログ表示（初期ディレクトリは設定値）
                try:
                    init_dir = self.config.get_setting("ExternalOutputDir", r"C:\\Users\\kouki\\Videos\\エンコード済み")
                except Exception:
                    init_dir = r"C:\\Users\\kouki\\Videos\\エンコード済み"
                self.on_ingest(init_dir)
        except Exception:
            # プロセスハンドルが無効など
            self.foobar_status.setText("状態不明")
            self._proc_timer.stop()
            self.foobar_proc = None

    def on_complete(self):
        if not self.album_folder or not self.workflow.state:
            return
        dst_name = self.workflow.state.get_path("opusOutput")
        dst = os.path.join(self.album_folder, dst_name)
        got = 0
        if os.path.isdir(dst):
            got = len([f for f in os.listdir(dst) if f.lower().endswith('.opus')])
        track_count = len(self.workflow.state.get_tracks())
        if got < track_count:
            QMessageBox.warning(self, "不足", f"Opus が不足しています ({got}/{track_count})")
            return
        self.step_completed.emit()

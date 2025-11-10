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
            "1. foobar2000 を起動（入力パスは自動コピー済み）\n"
            "2. foobar2000 でファイルを追加して Opus 変換を実行\n"
            "3. 変換完了後 foobar2000 を閉じると自動で取り込みダイアログ表示"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(10)

        # メインアクション: 起動と完了（大きく目立たせる）
        main_btns = QHBoxLayout()
        self.btn_launch = QPushButton("▶ foobar2000 を起動")
        self.btn_launch.setMinimumHeight(40)
        self.btn_launch.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_launch.clicked.connect(self.on_launch_foobar)
        main_btns.addWidget(self.btn_launch)

        self.btn_complete = QPushButton("✓ Step 5 完了")
        self.btn_complete.setMinimumHeight(40)
        self.btn_complete.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_complete.clicked.connect(self.on_complete)
        main_btns.addWidget(self.btn_complete)
        layout.addLayout(main_btns)

        layout.addSpacing(6)

        # 状態表示
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("起動状態:"))
        self.foobar_status = QLabel("未起動")
        status_row.addWidget(self.foobar_status)
        status_row.addStretch()
        layout.addLayout(status_row)

        layout.addSpacing(10)

        # 詳細表示（折りたたみ可能なログ）
        layout.addWidget(QLabel("<b>取り込みログ（参考）:</b>"))
        self.log_list = QListWidget()
        self.log_list.setMaximumHeight(150)
        layout.addWidget(self.log_list)

        # 入力フォルダ表示（ログの後に移動して視覚的に下方へ）
        layout.addWidget(QLabel("<b>入力フォルダ:</b>"))
        self.album_label = QLabel("未選択")
        self.album_label.setStyleSheet("color: gray;")
        layout.addWidget(self.album_label)

        # 補助ボタン（小型化）
        helper_btns = QHBoxLayout()
        self.btn_copy_path = QPushButton("📋 パスをコピー")
        self.btn_copy_path.setMaximumWidth(120)
        self.btn_copy_path.clicked.connect(self.on_copy_path)
        helper_btns.addWidget(self.btn_copy_path)

        self.btn_ingest = QPushButton("📥 手動取り込み")
        self.btn_ingest.setMaximumWidth(120)
        self.btn_ingest.setToolTip("foobar2000終了後は自動取り込みされますが、手動で取り込む場合はこちら")
        self.btn_ingest.clicked.connect(self.on_ingest)
        helper_btns.addWidget(self.btn_ingest)

        helper_btns.addStretch()
        layout.addLayout(helper_btns)

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
        # ポップアップ廃止: ログへ通知
        self.log_list.addItem(QListWidgetItem(f"[コピー完了] {self.input_folder}"))

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
        total = 0
        for t in self.workflow.state.get_tracks():
            if t.get("finalFile"): total += 1
            if t.get("instrumentalFile"): total += 1
        
        if got < total:
            # ファイル数不足: 確認ダイアログで警告
            reply = QMessageBox.warning(
                self,
                "ファイル数不足",
                f"Opusファイル数が不足しています。\n\n"
                f"期待: {total}個\n"
                f"実際: {got}個\n\n"
                f"変換が完了しているか確認してください。\n"
                f"このまま次のステップに進みますか?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # ステップ完了フラグを設定
        self.workflow.state.mark_step_completed("step5_opus")
        print("[DEBUG] Step5: ステップ完了フラグを設定しました")
        
        self.step_completed.emit()
        print("[DEBUG] Step5: step_completed シグナルを発行しました")

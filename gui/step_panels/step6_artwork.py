"""
Step 6: アートワーク最適化 & Mp3tag 手直し パネル

AAC/Opus 変換後に実施。cover.jpg / cover.webp を生成し、
必要なら AAC へ埋め込み、Mp3tag で最終タグ調整を行う。
"""
from __future__ import annotations
import os
import subprocess
from typing import Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
)

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager
from logic import artwork_handler as ah


class Step6ArtworkPanel(QWidget):
    step_completed = Signal()

    def __init__(self, config: ConfigManager, workflow: WorkflowManager):
        super().__init__()
        self.config = config
        self.workflow = workflow
        self.album_folder: Optional[str] = None
        self.source_image: Optional[str] = None
        self.init_ui()

    def init_ui(self):
        """UI初期化（FLAC 埋め込み無し、安全版）"""
        layout = QVBoxLayout(self)

        # タイトルと説明
        layout.addWidget(QLabel("<h2>Step 6: アートワーク最適化 & Mp3tag 手直し</h2>"))
        desc = QLabel(
            "FLAC からアートワーク抽出、または画像選択→最適化（cover.jpg/webp）。\n"
            "任意で AAC にカバー埋め込み後 Mp3tag を開いて最終手直し。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # 1) ソース取得
        layout.addWidget(QLabel("<b>1) アートワーク元の取得</b>"))
        row1 = QHBoxLayout()
        self.btn_from_flac = QPushButton("FLAC から抽出")
        self.btn_from_flac.clicked.connect(self.on_extract_from_flac)
        row1.addWidget(self.btn_from_flac)

        self.btn_pick_image = QPushButton("画像ファイルを選択…")
        self.btn_pick_image.clicked.connect(self.on_pick_image)
        row1.addWidget(self.btn_pick_image)

        self.lbl_source = QLabel("（未選択）")
        row1.addWidget(self.lbl_source)
        row1.addStretch()
        layout.addLayout(row1)

        # 2) 最適化
        layout.addWidget(QLabel("<b>2) 最適化（cover.jpg / cover.webp 生成）</b>"))
        row2 = QHBoxLayout()
        self.btn_optimize = QPushButton("最適化を実行")
        self.btn_optimize.clicked.connect(self.on_optimize)
        row2.addWidget(self.btn_optimize)

        self.lbl_result = QLabel("")
        row2.addWidget(self.lbl_result)
        row2.addStretch()
        layout.addLayout(row2)

        # 3) AAC 埋め込み（任意）
        layout.addWidget(QLabel("<b>3) （任意）AAC にカバー埋め込み</b>"))
        row3 = QHBoxLayout()
        self.btn_embed_aac = QPushButton("AAC(.m4a) に埋め込み")
        self.btn_embed_aac.clicked.connect(self.on_embed_aac)
        row3.addWidget(self.btn_embed_aac)
        row3.addStretch()
        layout.addLayout(row3)

        # 4) Mp3tag
        layout.addWidget(QLabel("<b>4) Mp3tag を開く（手直し）</b>"))
        row4 = QHBoxLayout()
        self.btn_open_mp3tag_album = QPushButton("Mp3tag（アルバムルート）")
        self.btn_open_mp3tag_album.clicked.connect(self.on_open_mp3tag_album)
        row4.addWidget(self.btn_open_mp3tag_album)

        self.btn_open_mp3tag_aac = QPushButton("Mp3tag（_aac_output）")
        self.btn_open_mp3tag_aac.clicked.connect(self.on_open_mp3tag_aac)
        row4.addWidget(self.btn_open_mp3tag_aac)
        row4.addStretch()
        layout.addLayout(row4)

        # 5) 完了
        layout.addWidget(QLabel("<b>5) 完了</b>"))
        row5 = QHBoxLayout()
        self.btn_complete = QPushButton("Step 6 完了")
        self.btn_complete.clicked.connect(self.on_complete)
        row5.addWidget(self.btn_complete)
        row5.addStretch()
        layout.addLayout(row5)

        layout.addStretch()

    def load_album(self, album_folder: str):
        """アルバム変更時のみ初期化。自動リフレッシュによる再呼び出しで選択が消えないようにする。"""
        if self.album_folder == album_folder:
            return
        self.album_folder = album_folder
        self.source_image = None
        self.lbl_source.setText("（未選択）")
        self.lbl_result.setText("")

    # -------- actions ---------
    def on_extract_from_flac(self):
        if not self.album_folder:
            return
        target = ah.find_first_flac_with_artwork(self.album_folder)
        if not target:
            QMessageBox.warning(self, "見つからない", "アートワーク付き FLAC が見つかりません。")
            return
        tmp = os.path.join(self.album_folder, "_cover_src.jpg")
        if ah.extract_artwork_from_flac(target, tmp):
            self.source_image = tmp
            self.lbl_source.setText(f"抽出: {os.path.basename(target)} → {os.path.basename(tmp)}")
        else:
            QMessageBox.warning(self, "失敗", "抽出に失敗しました。")

    def on_pick_image(self):
        if not self.album_folder:
            return
        path, _ = QFileDialog.getOpenFileName(self, "画像選択", self.album_folder, "画像 (*.jpg *.jpeg *.png *.webp)")
        if path:
            self.source_image = path
            self.lbl_source.setText(f"選択: {os.path.basename(path)}")

    def on_optimize(self):
        if not self.album_folder:
            return
        if not self.source_image or not os.path.exists(self.source_image):
            QMessageBox.warning(self, "未選択", "先にアートワーク元を抽出/選択してください。")
            return
        magick = self.config.get_tool_path("Magick")
        if not magick:
            QMessageBox.warning(self, "未設定", "magick.exe のパスを config.ini に設定してください。")
            return
        width = int(self.config.get_setting("ResizeWidth", "600"))
        jpg_q = int(self.config.get_setting("JpegQuality", "85"))
        webp_q = int(self.config.get_setting("WebpQuality", "85"))
        ok, p1, p2 = ah.ensure_artwork_resized_outputs(self.album_folder, magick, self.source_image, width, jpg_q, webp_q)
        if not ok:
            QMessageBox.critical(self, "失敗", f"最適化失敗: {p1}")
            return
        self.lbl_result.setText(f"生成: {os.path.relpath(p1, self.album_folder)}, {os.path.relpath(p2, self.album_folder)}")
        if self.workflow.state:
            self.workflow.state.set_artwork(True)

    def _cover_jpg(self) -> Optional[str]:
        if not self.album_folder:
            return None
        p = os.path.join(self.album_folder, "_artwork_resized", "cover.jpg")
        return p if os.path.exists(p) else None

    def on_embed_aac(self):
        if not self.album_folder or not self.workflow.state:
            return
        img = self._cover_jpg()
        if not img:
            QMessageBox.warning(self, "未生成", "cover.jpg を生成してください。")
            return
        aac_dir = os.path.join(self.album_folder, self.workflow.state.get_path("aacOutput"))
        if not os.path.isdir(aac_dir):
            QMessageBox.warning(self, "未取り込み", "_aac_output が見つかりません。先に Step4 を完了してください。")
            return
        ok_cnt = 0
        err_cnt = 0
        for name in os.listdir(aac_dir):
            if not name.lower().endswith('.m4a'):
                continue
            path = os.path.join(aac_dir, name)
            ok, err = ah.embed_artwork_to_mp4(path, img)
            if ok: ok_cnt += 1
            else:
                err_cnt += 1
                print(f"[WARN] AAC embed failed: {name}: {err}")
        QMessageBox.information(self, "AAC 埋め込み", f"成功: {ok_cnt} / 失敗: {err_cnt}")

    def _launch_mp3tag(self, target_dir: str):
        exe = self.config.get_tool_path("Mp3Tag")
        if not exe:
            QMessageBox.warning(self, "未設定", "Mp3tag のパスが設定されていません。Paths.Mp3Tag を記入してください。")
            return
        try:
            subprocess.Popen([exe, target_dir])
        except Exception as e:
            QMessageBox.critical(self, "起動失敗", str(e))

    def on_open_mp3tag_album(self):
        if not self.album_folder: return
        self._launch_mp3tag(self.album_folder)

    def on_open_mp3tag_aac(self):
        if not self.album_folder or not self.workflow.state: return
        aac_dir = os.path.join(self.album_folder, self.workflow.state.get_path("aacOutput"))
        if not os.path.isdir(aac_dir):
            QMessageBox.warning(self, "未取り込み", "_aac_output がありません。Step4 で取り込み後に実行してください。")
            return
        self._launch_mp3tag(aac_dir)

    def on_complete(self):
        if not self.album_folder:
            return
        jpg = os.path.join(self.album_folder, "_artwork_resized", "cover.jpg")
        webp = os.path.join(self.album_folder, "_artwork_resized", "cover.webp")
        if not (os.path.exists(jpg) and os.path.exists(webp)):
            QMessageBox.warning(self, "不足", "cover.jpg / cover.webp を生成後に完了してください。")
            return
        if self.workflow.state:
            self.workflow.state.set_artwork(True)
        self.step_completed.emit()

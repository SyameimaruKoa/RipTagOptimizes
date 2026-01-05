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
        layout.addWidget(QLabel("<h2>Step 6: アートワーク最適化</h2>"))
        desc = QLabel(
            "1. FLAC からアートワーク抽出 → 最適化実行\n"
            "2. 必要に応じて Mp3tag でタグ調整\n"
            "※ AAC/Opus への埋め込みは不要（既にFLACから引き継がれています）"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(10)

        # ステップ1: ソース取得と最適化
        layout.addWidget(QLabel("<b>① ソース画像取得 & 最適化:</b>"))
        step1_btns = QHBoxLayout()
        
        self.btn_from_flac = QPushButton("📁 FLAC から抽出")
        self.btn_from_flac.setMinimumHeight(35)
        self.btn_from_flac.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.btn_from_flac.clicked.connect(self.on_extract_from_flac)
        step1_btns.addWidget(self.btn_from_flac)

        self.btn_pick_image = QPushButton("🖼️ 画像を選択")
        self.btn_pick_image.setMinimumHeight(35)
        self.btn_pick_image.setStyleSheet("font-size: 13px;")
        self.btn_pick_image.clicked.connect(self.on_pick_image)
        step1_btns.addWidget(self.btn_pick_image)

        self.btn_optimize = QPushButton("🎨 最適化実行")
        self.btn_optimize.setMinimumHeight(35)
        self.btn_optimize.setStyleSheet("font-size: 13px; font-weight: bold; background-color: #4CAF50; color: white;")
        self.btn_optimize.clicked.connect(self.on_optimize)
        step1_btns.addWidget(self.btn_optimize)

        layout.addLayout(step1_btns)

        # ステータス表示
        status_layout = QVBoxLayout()
        status_row1 = QHBoxLayout()
        status_row1.addWidget(QLabel("ソース:"))
        self.lbl_source = QLabel("（未選択）")
        self.lbl_source.setStyleSheet("color: gray;")
        status_row1.addWidget(self.lbl_source)
        status_row1.addStretch()
        status_layout.addLayout(status_row1)

        status_row2 = QHBoxLayout()
        status_row2.addWidget(QLabel("結果:"))
        self.lbl_result = QLabel("")
        self.lbl_result.setStyleSheet("color: gray;")
        status_row2.addWidget(self.lbl_result)
        status_row2.addStretch()
        status_layout.addLayout(status_row2)
        layout.addLayout(status_layout)

        layout.addSpacing(10)

        # ステップ2: Mp3tag（任意）
        layout.addWidget(QLabel("<b>② タグ調整（任意）:</b>"))
        step3_btns = QHBoxLayout()
        
        self.btn_open_mp3tag_album = QPushButton("�️ Mp3tag（ルート）")
        self.btn_open_mp3tag_album.setMaximumWidth(160)
        self.btn_open_mp3tag_album.clicked.connect(self.on_open_mp3tag_album)
        step3_btns.addWidget(self.btn_open_mp3tag_album)

        self.btn_open_mp3tag_aac = QPushButton("🏷️ Mp3tag（AAC）")
        self.btn_open_mp3tag_aac.setMaximumWidth(160)
        self.btn_open_mp3tag_aac.clicked.connect(self.on_open_mp3tag_aac)
        step3_btns.addWidget(self.btn_open_mp3tag_aac)

        self.btn_open_mp3tag_opus = QPushButton("🏷️ Mp3tag（Opus）")
        self.btn_open_mp3tag_opus.setMaximumWidth(160)
        self.btn_open_mp3tag_opus.clicked.connect(self.on_open_mp3tag_opus)
        step3_btns.addWidget(self.btn_open_mp3tag_opus)

        step3_btns.addStretch()
        layout.addLayout(step3_btns)

        layout.addSpacing(10)

        # 完了ボタン
        complete_btn_layout = QHBoxLayout()
        self.btn_complete = QPushButton("✓ Step 6 完了")
        self.btn_complete.setMinimumHeight(40)
        self.btn_complete.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_complete.clicked.connect(self.on_complete)
        complete_btn_layout.addWidget(self.btn_complete)
        layout.addLayout(complete_btn_layout)

        layout.addStretch()

    def load_album(self, album_folder: str):
        """アルバム変更時のみ初期化。自動リフレッシュによる再呼び出しで選択が消えないようにする。"""
        if self.album_folder == album_folder:
            return
        self.album_folder = album_folder
        self.source_image = None
        self.lbl_source.setText("（未選択）")
        self.lbl_result.setText("")
        
        # hasArtwork チェック: false の場合はスキップ案内を表示
        if self.workflow.state and self.workflow.state.has_artwork() == False:
            self._show_no_artwork_message()

    # -------- actions ---------
    def on_extract_from_flac(self):
        if not self.album_folder:
            return
        album_name = self.workflow.state.get_album_name() if self.workflow.state else None
        target = ah.find_first_flac_with_artwork(self.album_folder, album_name)
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
        
        # 初期ディレクトリ（config.iniから取得、なければアルバムフォルダ）
        default_dir = self.config.get_default_directory('artwork_select')
        if not default_dir or not os.path.isdir(default_dir):
            default_dir = self.album_folder
        
        path, _ = QFileDialog.getOpenFileName(self, "画像選択", default_dir, "画像 (*.jpg *.jpeg *.png *.webp)")
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
        
        # 最適化完了後、自動的にAAC/Opusに埋め込む
        self._auto_embed_artwork()

    def _cover_jpg(self) -> Optional[str]:
        if not self.album_folder:
            return None
        p = os.path.join(self.album_folder, "_artwork_resized", "cover.jpg")
        return p if os.path.exists(p) else None

    def _cover_webp(self) -> Optional[str]:
        if not self.album_folder:
            return None
        p = os.path.join(self.album_folder, "_artwork_resized", "cover.webp")
        return p if os.path.exists(p) else None

    def _auto_embed_artwork(self):
        """最適化完了後に自動的にAAC/Opusへアートワークを埋め込む"""
        if not self.album_folder or not self.workflow.state:
            return
        
        results = []
        
        # AAC に JPG を埋め込み
        jpg_img = self._cover_jpg()
        if jpg_img:
            album_name = self.workflow.state.get_album_name()
            sanitized_album_name = self._sanitize_foldername(album_name)
            aac_base = os.path.join(self.album_folder, self.workflow.state.get_path("aacOutput"))
            aac_dir = os.path.join(aac_base, sanitized_album_name)
            
            if os.path.isdir(aac_dir):
                aac_ok = 0
                aac_err = 0
                for name in os.listdir(aac_dir):
                    if not name.lower().endswith('.m4a'):
                        continue
                    path = os.path.join(aac_dir, name)
                    ok, err = ah.embed_artwork_to_mp4(path, jpg_img)
                    if ok:
                        aac_ok += 1
                    else:
                        aac_err += 1
                        print(f"[WARN] AAC embed failed: {name}: {err}")
                results.append(f"AAC (JPG): {aac_ok}成功 / {aac_err}失敗")
            else:
                print(f"[INFO] AAC出力フォルダが存在しません: {aac_dir}")
        
        # Opus に WebP を埋め込み
        webp_img = self._cover_webp()
        if webp_img:
            album_name = self.workflow.state.get_album_name()
            sanitized_album_name = self._sanitize_foldername(album_name)
            opus_base = os.path.join(self.album_folder, self.workflow.state.get_path("opusOutput"))
            opus_dir = os.path.join(opus_base, sanitized_album_name)
            
            if os.path.isdir(opus_dir):
                opus_ok = 0
                opus_err = 0
                for name in os.listdir(opus_dir):
                    if not name.lower().endswith('.opus'):
                        continue
                    path = os.path.join(opus_dir, name)
                    ok, err = ah.embed_artwork_to_opus(path, webp_img)
                    if ok:
                        opus_ok += 1
                    else:
                        opus_err += 1
                        print(f"[WARN] Opus embed failed: {name}: {err}")
                results.append(f"Opus (WebP): {opus_ok}成功 / {opus_err}失敗")
            else:
                print(f"[INFO] Opus出力フォルダが存在しません: {opus_dir}")
        
        # 結果をユーザーに通知
        if results:
            result_msg = "\n".join(results)
            QMessageBox.information(self, "アートワーク埋め込み完了", 
                                  f"最適化ファイルを自動埋め込みしました:\n\n{result_msg}")

    def on_embed_aac(self):
        if not self.album_folder or not self.workflow.state:
            return
        img = self._cover_jpg()
        if not img:
            QMessageBox.warning(self, "未生成", "cover.jpg を生成してください。")
            return
        
        # アルバム名とアーティスト名を取得してサニタイズ
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        artist_name = self.workflow.state.get_artist_name()
        sanitized_artist_name = self._sanitize_foldername(artist_name)
        
        # _aac_output/アーティスト名/アルバム名/
        aac_base = os.path.join(self.album_folder, self.workflow.state.get_path("aacOutput"))
        aac_dir = os.path.join(aac_base, sanitized_artist_name, sanitized_album_name)
        
        if not os.path.isdir(aac_dir):
            QMessageBox.warning(self, "未取り込み", f"_aac_output/{sanitized_artist_name}/{sanitized_album_name} が見つかりません。先に Step4 を完了してください。")
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

    def on_embed_opus(self):
        """Opus ファイルにカバー画像を埋め込む（WebP形式を優先使用）"""
        if not self.album_folder or not self.workflow.state:
            return
        # Opus には WebP を優先的に埋め込む（ファイルサイズ削減）
        img = self._cover_webp()
        if not img:
            QMessageBox.warning(self, "未生成", "cover.webp を生成してください。")
            return
        
        # アルバム名とアーティスト名を取得してサニタイズ
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        artist_name = self.workflow.state.get_artist_name()
        sanitized_artist_name = self._sanitize_foldername(artist_name)
        
        # _opus_output/アーティスト名/アルバム名/
        opus_base = os.path.join(self.album_folder, self.workflow.state.get_path("opusOutput"))
        opus_dir = os.path.join(opus_base, sanitized_artist_name, sanitized_album_name)
        
        if not os.path.isdir(opus_dir):
            QMessageBox.warning(self, "未取り込み", f"_opus_output/{sanitized_artist_name}/{sanitized_album_name} が見つかりません。先に Step5 を完了してください。")
            return
        ok_cnt = 0
        err_cnt = 0
        for name in os.listdir(opus_dir):
            if not name.lower().endswith('.opus'):
                continue
            path = os.path.join(opus_dir, name)
            ok, err = ah.embed_artwork_to_opus(path, img)
            if ok: ok_cnt += 1
            else:
                err_cnt += 1
                print(f"[WARN] Opus embed failed: {name}: {err}")
        QMessageBox.information(self, "Opus 埋め込み", f"WebP埋め込み 成功: {ok_cnt} / 失敗: {err_cnt}")

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
        
        # アルバム名とアーティスト名を取得してサニタイズ
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        artist_name = self.workflow.state.get_artist_name()
        sanitized_artist_name = self._sanitize_foldername(artist_name)
        
        # _aac_output/アーティスト名/アルバム名/
        aac_base = os.path.join(self.album_folder, self.workflow.state.get_path("aacOutput"))
        aac_dir = os.path.join(aac_base, sanitized_artist_name, sanitized_album_name)
        
        if not os.path.isdir(aac_dir):
            QMessageBox.warning(self, "未取り込み", f"_aac_output/{sanitized_artist_name}/{sanitized_album_name} がありません。Step4 で取り込み後に実行してください。")
            return
        self._launch_mp3tag(aac_dir)

    def on_open_mp3tag_opus(self):
        """Opus 出力フォルダで Mp3tag を開く"""
        if not self.album_folder or not self.workflow.state: return
        
        # アルバム名とアーティスト名を取得してサニタイズ
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        artist_name = self.workflow.state.get_artist_name()
        sanitized_artist_name = self._sanitize_foldername(artist_name)
        
        # _opus_output/アーティスト名/アルバム名/
        opus_base = os.path.join(self.album_folder, self.workflow.state.get_path("opusOutput"))
        opus_dir = os.path.join(opus_base, sanitized_artist_name, sanitized_album_name)
        
        if not os.path.isdir(opus_dir):
            QMessageBox.warning(self, "未取り込み", f"_opus_output/{sanitized_artist_name}/{sanitized_album_名} がありません。Step5 で取り込み後に実行してください。")
            return
        self._launch_mp3tag(opus_dir)

    def on_complete(self):
        if not self.album_folder:
            return
        
        # hasArtwork == false の場合はスキップ確認
        if self.workflow.state and self.workflow.state.has_artwork() == False:
            reply = QMessageBox.question(
                self,
                "アートワークなし",
                "このアルバムにはアートワークが埋め込まれていません。\n\n"
                "Step 6 をスキップして次のステップへ進みますか?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                # スキップ時もステップ完了フラグを設定
                if self.workflow.state:
                    self.workflow.state.mark_step_completed("step6_artwork")
                    print("[DEBUG] Step6: アートワークなしでスキップ、ステップ完了フラグを設定しました")
                self.step_completed.emit()
                print("[DEBUG] Step6: step_completed シグナルを発行しました（スキップ）")
            return
        
        jpg = os.path.join(self.album_folder, "_artwork_resized", "cover.jpg")
        webp = os.path.join(self.album_folder, "_artwork_resized", "cover.webp")
        if not (os.path.exists(jpg) and os.path.exists(webp)):
            QMessageBox.warning(self, "不足", "cover.jpg / cover.webp を生成後に完了してください。")
            return
        
        # ステップ完了フラグを設定
        if self.workflow.state:
            self.workflow.state.set_artwork(True)
            self.workflow.state.mark_step_completed("step6_artwork")
            print("[DEBUG] Step6: ステップ完了フラグを設定しました")
        
        self.step_completed.emit()
        print("[DEBUG] Step6: step_completed シグナルを発行しました")
    
    def _show_no_artwork_message(self):
        """アートワークなしの案内を表示"""
        QMessageBox.information(
            self,
            "アートワークなし",
            "このアルバムには FLAC にアートワークが埋め込まれていません。\n\n"
            "Step 6 の処理は不要です。\n"
            "「Step 6 完了」ボタンを押してスキップしてください。"
        )
    
    def _sanitize_foldername(self, name: str) -> str:
        """フォルダ名に使用できない文字を全角等に置換"""
        replacements = {
            '\\': '¥',
            '/': '／',
            ':': '：',
            '*': '＊',
            '?': '？',
            '"': '"',
            '<': '＜',
            '>': '＞',
            '|': '｜'
        }
        for char, replacement in replacements.items():
            name = name.replace(char, replacement)
        return name

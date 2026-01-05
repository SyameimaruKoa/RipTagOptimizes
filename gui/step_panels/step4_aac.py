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

        title = QLabel("<h2>Step 4: AAC変換 (MediaHuman)</h2>")
        layout.addWidget(title)

        desc = QLabel(
            "1. MediaHuman を起動（入力パスは自動コピー済み）\n"
            "2. MediaHuman でフォルダを追加して AAC 変換を実行\n"
            "   ⚠️ 出力先: 設定で 変換MediaHuman フォルダに指定してください\n"
            "3. 変換完了後 MediaHuman を閉じると自動で取り込みダイアログ表示"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addSpacing(10)

        # メインアクション: 起動と完了（大きく目立たせる）
        main_btns = QHBoxLayout()
        self.btn_launch = QPushButton("▶ MediaHuman を起動")
        self.btn_launch.setMinimumHeight(40)
        self.btn_launch.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_launch.clicked.connect(self.on_launch_mediahuman)
        main_btns.addWidget(self.btn_launch)

        self.btn_complete = QPushButton("✓ Step 4 完了")
        self.btn_complete.setMinimumHeight(40)
        self.btn_complete.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.btn_complete.clicked.connect(self.on_complete)
        main_btns.addWidget(self.btn_complete)
        layout.addLayout(main_btns)

        layout.addSpacing(10)

        # MediaHuman 出力先設定の案内
        external_output = self.config.get_setting('ExternalOutputDir', '%USERPROFILE%\\Videos\\エンコード済み')
        config_hint = QLabel(
            "<b>⚙️ MediaHuman設定（初回のみ）:</b><br>"
            "「オプション」→「フォルダ」で 出力フォルダ を以下に設定してください:<br>"
            f"<code>{external_output}/変換MediaHuman</code>"
        )
        config_hint.setWordWrap(True)
        config_hint.setStyleSheet("background-color: #fffacd; color: #333; padding: 8px; border-radius: 4px; font-weight: normal;")
        layout.addWidget(config_hint)

        layout.addSpacing(10)

        # 詳細表示（折りたたみ可能なリスト）
        layout.addWidget(QLabel("<b>入力フォルダ（参考）:</b>"))
        self.folder_list = QListWidget()
        self.folder_list.setMaximumHeight(150)
        layout.addWidget(self.folder_list)

        # 補助ボタン（小型化）
        helper_btns = QHBoxLayout()
        self.btn_copy = QPushButton("📋 パスをコピー")
        self.btn_copy.setMaximumWidth(120)
        self.btn_copy.clicked.connect(self.on_copy_to_clipboard)
        helper_btns.addWidget(self.btn_copy)

        self.btn_ingest = QPushButton("📥 手動取り込み")
        self.btn_ingest.setMaximumWidth(120)
        self.btn_ingest.setToolTip("MediaHuman終了後は自動取り込みされますが、手動で取り込む場合はこちら")
        self.btn_ingest.clicked.connect(self.on_ingest_outputs)
        helper_btns.addWidget(self.btn_ingest)

        helper_btns.addStretch()
        layout.addLayout(helper_btns)

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
        # クリップボードへフォルダパスをコピー（モーダル削減: サイレント動作）
        from PySide6.QtGui import QGuiApplication
        if not self.album_folder:
            return
        target = self.input_folder or self.album_folder
        QGuiApplication.clipboard().setText(target)
        # ポップアップ廃止: リストに通知を追加
        self.folder_list.addItem(QListWidgetItem(f"[コピー完了] {target}"))

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
                QMessageBox.information(
                    self,
                    "MediaHuman 実行中",
                    "MediaHuman は既に起動しています。\n\n"
                    "フォルダを追加して AAC 変換を実行してください。\n"
                    "変換完了後、MediaHuman を閉じてください。"
                )
                return
            self.mediahuman_proc = subprocess.Popen([exe])
            self._mh_timer.start()
            QMessageBox.information(
                self,
                "MediaHuman 起動中",
                "MediaHuman を起動しました。\n\n"
                "入力パスはクリップボードにコピー済みです。\n"
                "オプション → フォルダで 出力フォルダを設定し、\n"
                "フォルダを追加して AAC 変換を実行してください。\n\n"
                "変換完了後、MediaHuman を閉じてください。"
            )
        except Exception as e:
            QMessageBox.critical(self, "起動失敗", str(e))

    def on_ingest_outputs(self, init_dir: str | None = None):
        """MediaHuman の出力から .m4a を取り込み、_aac_output/アルバム名/ に集約する。
        - 想定: MediaHuman の出力先はユーザー側設定（ExternalOutputDir/aac_output に設定させる）。
        - 取り込み方法: ダイアログで出力フォルダを選んでもらい、そこから .m4a をコピー。
        - ファイル名を finalFile/instrumentalFile に基づいてリネーム（拡張子を .m4a に変更）
        """
        from PySide6.QtWidgets import QFileDialog
        if not self.album_folder or not self.workflow.state:
            return

        # 既定の初期位置（ExternalOutputDir/aac_output を優先）
        if init_dir:
            start_dir = init_dir
        else:
            # ExternalOutputDir + aac_output フォルダ名を組み合わせる
            external_dir = self.config.get_setting("ExternalOutputDir")
            aac_folder_name = self.config.get_directory_name('aac_output')  # フォルダ名のみを取得
            if external_dir and aac_folder_name:
                external_dir = self.config.expand_path(external_dir)
                candidate = os.path.join(external_dir, aac_folder_name)
                # フォルダが存在する場合はそれを使用、存在しない場合は ExternalOutputDir を使用
                if os.path.isdir(candidate):
                    start_dir = candidate
                else:
                    start_dir = external_dir
            elif external_dir:
                external_dir = self.config.expand_path(external_dir)
                start_dir = external_dir
            else:
                # フォールバック: ダウンロードフォルダ
                start_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        
        src = QFileDialog.getExistingDirectory(self, "MediaHuman の出力フォルダを選択", start_dir)
        if not src:
            return

        # アルバム名とアーティスト名を取得してサニタイズ
        album_name = self.workflow.state.get_album_name()
        album_name = self._sanitize_foldername(album_name)
        artist_name = self.workflow.state.get_artist_name()
        artist_name = self._sanitize_foldername(artist_name)
        
        # 出力先: _aac_output/アーティスト名/アルバム名/
        aac_dir_name = self.workflow.state.get_path("aacOutput")
        dst_base = os.path.join(self.album_folder, aac_dir_name)
        dst = os.path.join(dst_base, artist_name, album_name)
        os.makedirs(dst, exist_ok=True)

        # トラック情報から期待されるファイル名マッピングを作成
        tracks = self.workflow.state.get_tracks()
        expected_files = {}  # {元のトラック番号: 最終ファイル名}
        
        import re
        for track in tracks:
            final_file = track.get("finalFile", "")
            inst_file = track.get("instrumentalFile", "")
            
            # トラック番号を抽出
            if final_file:
                m = re.match(r"^(?:Disc \d+-)?(\d{2,3})", final_file)
                if m:
                    track_num = m.group(1)
                    # 拡張子を .m4a に変更
                    base_name = os.path.splitext(final_file)[0]
                    expected_files[track_num] = base_name + ".m4a"
            
            if inst_file:
                m = re.match(r"^(?:Disc \d+-)?(\d{2,3})", inst_file)
                if m:
                    track_num = m.group(1)
                    base_name = os.path.splitext(inst_file)[0]
                    # Instの場合は別のキーで保存（番号+Inst識別子）
                    expected_files[track_num + "_inst"] = base_name + ".m4a"

        import shutil
        count = 0
        for name in os.listdir(src):
            if name.lower().endswith(".m4a"):
                src_file = os.path.join(src, name)
                
                # 元のファイル名からトラック番号を抽出してマッピング
                m = re.match(r"^(\d{2,3})", name)
                if m:
                    track_num = m.group(1)
                    # Instかどうかを判定
                    is_inst = "(inst)" in name.lower() or "instrumental" in name.lower()
                    
                    # 期待されるファイル名を取得
                    key = track_num + "_inst" if is_inst else track_num
                    expected_name = expected_files.get(key)
                    
                    if expected_name:
                        dst_file = os.path.join(dst, expected_name)
                    else:
                        # マッピングが見つからない場合は元の名前を使用
                        dst_file = os.path.join(dst, name)
                else:
                    # トラック番号が抽出できない場合は元の名前を使用
                    dst_file = os.path.join(dst, name)
                
                try:
                    if os.path.exists(dst_file):
                        # 既存ファイルは上書き前に削除
                        os.remove(dst_file)
                    shutil.move(src_file, dst_file)
                    count += 1
                except Exception as e:
                    print(f"[ERROR] move failed: {e}")
        self.folder_list.addItem(QListWidgetItem(f"取り込み (移動) 完了: {count} ファイル → {dst}"))
    
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

    def on_complete(self):
        """Step4 完了: 取り込み数で簡易チェックし、次へ進む"""
        if not self.album_folder or not self.workflow.state:
            return
        
        # アルバム名とアーティスト名を含めたパス
        album_name = self._sanitize_foldername(self.workflow.state.get_album_name())
        artist_name = self._sanitize_foldername(self.workflow.state.get_artist_name())
        dst_base = os.path.join(self.album_folder, self.workflow.state.get_path("aacOutput"))
        dst = os.path.join(dst_base, artist_name, album_name)
        
        got = 0
        if os.path.exists(dst):
            got = len([f for f in os.listdir(dst) if f.lower().endswith('.m4a')])
        
        # 期待ファイル数をカウント（ユニークなファイル名のみ）
        expected_files = set()
        for t in self.workflow.state.get_tracks():
            final = t.get("finalFile")
            inst = t.get("instrumentalFile")
            if final:
                expected_files.add(final)
            if inst:
                expected_files.add(inst)
        total = len(expected_files)
        
        if got < total:
            # ファイル数不足: 確認ダイアログで警告
            reply = QMessageBox.warning(
                self,
                "ファイル数不足",
                f"AACファイル数が不足しています。\n\n"
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
        self.workflow.state.mark_step_completed("step4_aac")
        print("[DEBUG] Step4: ステップ完了フラグを設定しました")
        
        self.step_completed.emit()
        print("[DEBUG] Step4: step_completed シグナルを発行しました")

    # ------------------------
    # helpers
    # ------------------------
    def _resolve_input_folder(self, album_folder: str) -> str | None:
        """_flac_src/アルバム名 を優先的に返す。無ければアルバムルート。"""
        try:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") if self.workflow and self.workflow.state else "_flac_src"
        except Exception:
            raw_dirname = "_flac_src"
        
        # アルバム名を取得してサブフォルダパスを生成
        album_name = "Unknown"
        if self.workflow and self.workflow.state:
            album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        
        candidate = os.path.join(album_folder, raw_dirname, sanitized_album_name)
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

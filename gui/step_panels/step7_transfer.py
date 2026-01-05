"""
Step 7: 最終転送パネル
各ファイル形式ごとに専用の転送フローを提供
"""
import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QGroupBox
)
from PySide6.QtCore import Signal

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager


class Step7TransferPanel(QWidget):
    """Step 7: 最終転送パネル（3つのサブステップ）"""
    
    step_completed = Signal()
    
    def __init__(self, config: ConfigManager, workflow: WorkflowManager):
        super().__init__()
        self.config = config
        self.workflow = workflow
        self.album_folder = None
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel("<h2>Step 7: 最終転送（3つのサブステップ）</h2>")
        layout.addWidget(title)
        
        # 説明
        desc = QLabel(
            "各ファイル形式ごとに適切な転送先に移動します。\n"
            "各サブステップを順番に実行してください。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(15)
        
        # === サブステップ 1: FLAC転送 ===
        self.create_flac_section(layout)
        
        layout.addSpacing(15)
        
        # === サブステップ 2: AAC転送 ===
        self.create_aac_section(layout)
        
        layout.addSpacing(15)
        
        # === サブステップ 3: Opus転送 ===
        self.create_opus_section(layout)
        
        layout.addSpacing(20)
        
        # === 最終完了ボタン ===
        complete_layout = QHBoxLayout()
        self.btn_complete = QPushButton("✓ Step 7 完了（全転送完了）")
        self.btn_complete.setMinimumHeight(50)
        self.btn_complete.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #4CAF50; color: white;")
        self.btn_complete.clicked.connect(self.on_complete)
        complete_layout.addWidget(self.btn_complete)
        layout.addLayout(complete_layout)
        
        layout.addStretch()
    
    def create_flac_section(self, parent_layout):
        """サブステップ1: FLAC転送セクション"""
        group = QGroupBox("📀 サブステップ 7-1: FLAC転送")
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; }")
        layout = QVBoxLayout()
        group.setLayout(layout)
        
        # 手順説明
        instructions = QLabel(
            "① YouTube Music にアップロード<br>"
            "② WinSCP で NAS にアップロード<br>"
            "<span style='color: gray;'>対象: _final_flac フォルダ（_flac_src から自動移動済み）</span>"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addSpacing(8)
        
        # アップロードボタン
        btn_layout = QHBoxLayout()
        
        btn_open_final = QPushButton("📁 _final_flac を開く")
        btn_open_final.setMinimumHeight(35)
        btn_open_final.clicked.connect(self.on_open_final_flac_folder)
        btn_layout.addWidget(btn_open_final)
        
        btn_ytmusic = QPushButton("🎵 YouTube Music を開く")
        btn_ytmusic.setMinimumHeight(35)
        btn_ytmusic.setToolTip("ブラウザでYouTube Musicのアップロードページを開きます")
        btn_ytmusic.clicked.connect(self.on_open_youtube_music)
        btn_layout.addWidget(btn_ytmusic)
        
        btn_winscp = QPushButton("🌐 WinSCP を起動")
        btn_winscp.setMinimumHeight(35)
        btn_winscp.clicked.connect(self.on_launch_winscp)
        btn_layout.addWidget(btn_winscp)
        
        layout.addLayout(btn_layout)
        
        parent_layout.addWidget(group)
    
    def create_aac_section(self, parent_layout):
        """サブステップ2: AAC転送セクション"""
        group = QGroupBox("🎧 サブステップ 7-2: AAC転送")
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; }")
        layout = QVBoxLayout()
        group.setLayout(layout)
        
        # 手順説明
        instructions = QLabel(
            "① iTunes（ミュージック）に取り込み<br>"
            "② 取り込み完了後 → 役目終了（削除OK）<br>"
            "<span style='color: gray;'>対象: _aac_output フォルダ</span>"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addSpacing(8)
        
        # ボタン（3つ横並びで統一）
        btn_layout = QHBoxLayout()
        
        btn_open_aac = QPushButton("📁 AACフォルダを開く")
        btn_open_aac.setMinimumHeight(35)
        btn_open_aac.clicked.connect(self.on_open_aac_folder)
        btn_layout.addWidget(btn_open_aac)
        
        btn_itunes = QPushButton("🎵 iTunes/ミュージック を起動")
        btn_itunes.setMinimumHeight(35)
        btn_itunes.setToolTip("Windows版iTunesまたはミュージックアプリを起動します")
        btn_itunes.clicked.connect(self.on_launch_itunes)
        btn_layout.addWidget(btn_itunes)
        
        # ダミーボタン（3つ横並び統一のため）
        btn_dummy = QPushButton("")
        btn_dummy.setMinimumHeight(35)
        btn_dummy.setEnabled(False)
        btn_dummy.setVisible(False)
        btn_layout.addWidget(btn_dummy)
        
        layout.addLayout(btn_layout)
        
        parent_layout.addWidget(group)
    
    def create_opus_section(self, parent_layout):
        """サブステップ3: Opus転送セクション"""
        group = QGroupBox("🎼 サブステップ 7-3: Opus転送")
        group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 13px; }")
        layout = QVBoxLayout()
        group.setLayout(layout)
        
        # 手順説明
        instructions = QLabel(
            "① ユーザーの Music フォルダの任意の場所に移動<br>"
            "② FreeFileSync で NAS と同期<br>"
            "③ 同期完了後 → 役目終了（削除OK）<br>"
            "<span style='color: gray;'>対象: _opus_output フォルダ</span>"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        layout.addSpacing(8)
        
        # ボタン
        btn_layout = QHBoxLayout()
        
        btn_open_opus = QPushButton("📁 Opusフォルダを開く")
        btn_open_opus.setMinimumHeight(35)
        btn_open_opus.clicked.connect(self.on_open_opus_folder)
        btn_layout.addWidget(btn_open_opus)
        
        btn_music_folder = QPushButton("📂 Musicフォルダを開く")
        btn_music_folder.setMinimumHeight(35)
        btn_music_folder.setToolTip("ユーザーのMusicフォルダを開きます")
        btn_music_folder.clicked.connect(self.on_open_music_folder)
        btn_layout.addWidget(btn_music_folder)
        
        btn_freefilesync = QPushButton("🔄 FreeFileSync を起動")
        btn_freefilesync.setMinimumHeight(35)
        btn_freefilesync.clicked.connect(self.on_launch_freefilesync)
        btn_layout.addWidget(btn_freefilesync)
        
        layout.addLayout(btn_layout)
        
        parent_layout.addWidget(group)
    
    def load_album(self, album_folder: str):
        """アルバムを読み込み"""
        self.album_folder = album_folder
        # アルバム読み込み時に自動的にFLACを_final_flacに移動
        self._auto_move_flac_to_final()
    
    def _auto_move_flac_to_final(self):
        """FLACファイルを自動的に_final_flac/アーティスト名/アルバム名フォルダに移動（内部処理）"""
        if not self.album_folder or not self.workflow.state:
            return
        
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        artist_name = self.workflow.state.get_artist_name()
        sanitized_artist_name = self._sanitize_foldername(artist_name)
        
        flac_src = os.path.join(self.album_folder, "_flac_src", sanitized_album_name)
        final_flac_base = os.path.join(self.album_folder, "_final_flac")
        final_flac = os.path.join(final_flac_base, sanitized_artist_name, sanitized_album_name)
        
        # _flac_src/アルバム名が存在しない、または_final_flac/アーティスト名/アルバム名が既に存在する場合はスキップ
        if not os.path.exists(flac_src):
            return
        
        if os.path.exists(final_flac):
            return  # 既に移動済み
        
        # 親フォルダを作成してから移動
        try:
            import shutil
            os.makedirs(final_flac_base, exist_ok=True)
            # アーティスト名フォルダを作成
            artist_dir = os.path.join(final_flac_base, sanitized_artist_name)
            os.makedirs(artist_dir, exist_ok=True)
            shutil.move(flac_src, final_flac)
        except Exception as e:
            # エラーが発生してもUIには表示せず、ログに記録するのみ
            print(f"[Step7] FLAC自動移動エラー: {e}")
    
    # === サブステップ1: FLAC関連 ===
    def on_move_flac_to_final(self):
        """FLACファイルを_final_flac/アーティスト名/アルバム名フォルダに移動（手動実行）"""
        if not self.album_folder or not self.workflow.state:
            QMessageBox.warning(self, "エラー", "アルバムが選択されていません。")
            return
        
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        artist_name = self.workflow.state.get_artist_name()
        sanitized_artist_name = self._sanitize_foldername(artist_name)
        
        flac_src = os.path.join(self.album_folder, "_flac_src", sanitized_album_name)
        final_flac_base = os.path.join(self.album_folder, "_final_flac")
        final_flac = os.path.join(final_flac_base, sanitized_artist_name, sanitized_album_name)
        
        # _final_flac/アーティスト名/アルバム名が既に存在する場合
        if os.path.exists(final_flac):
            QMessageBox.information(
                self,
                "確認",
                f"FLACは既に _final_flac/{sanitized_artist_name}/{sanitized_album_name} に移動済みです。\n\n{final_flac}"
            )
            return
        
        # _flac_src/アルバム名が存在しない場合
        if not os.path.exists(flac_src):
            QMessageBox.warning(self, "エラー", f"FLACフォルダが見つかりません:\n{flac_src}")
            return
        
        # 親フォルダを作成してから移動
        try:
            import shutil
            os.makedirs(final_flac_base, exist_ok=True)
            # アーティスト名フォルダを作成
            artist_dir = os.path.join(final_flac_base, sanitized_artist_name)
            os.makedirs(artist_dir, exist_ok=True)
            shutil.move(flac_src, final_flac)
            QMessageBox.information(
                self,
                "完了",
                f"FLACファイルを _final_flac/{sanitized_artist_name}/{sanitized_album_name} に移動しました。\n\n"
                f"移動先: {final_flac}"
            )
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"FLACの移動に失敗しました:\n{e}")
    
    def on_open_final_flac_folder(self):
        """_final_flac/アーティスト名/アルバム名フォルダを開く"""
        if not self.album_folder or not self.workflow.state:
            QMessageBox.warning(self, "エラー", "アルバムが選択されていません。")
            return
        
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        artist_name = self.workflow.state.get_artist_name()
        sanitized_artist_name = self._sanitize_foldername(artist_name)
        final_flac = os.path.join(self.album_folder, "_final_flac", sanitized_artist_name, sanitized_album_name)
        
        if not os.path.exists(final_flac):
            QMessageBox.warning(
                self, 
                "エラー", 
                f"_final_flac/{sanitized_artist_name}/{sanitized_album_name} フォルダが見つかりません。\n\n"
                f"先に「⓪ FLACを_final_flacに移動」ボタンを実行してください。\n\n"
                f"期待されるパス: {final_flac}"
            )
            return
        
        try:
            os.startfile(final_flac)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"フォルダを開けませんでした:\n{e}")
    
    def on_open_youtube_music(self):
        """YouTube Musicのアップロードページをブラウザで開く"""
        import webbrowser
        webbrowser.open("https://music.youtube.com/upload")
    
    def on_launch_winscp(self):
        """WinSCPを起動"""
        winscp_path = self.config.get_tool_path("WinSCP")
        
        if not winscp_path or not os.path.exists(winscp_path):
            QMessageBox.information(
                self,
                "WinSCP未設定",
                "WinSCPのパスが設定されていないか、ファイルが見つかりません。\n\n"
                "config.ini の [Paths] セクションに\n"
                "WinSCP = C:\\Program Files (x86)\\WinSCP\\WinSCP.exe\n"
                "のように設定してください。"
            )
            return
        
        try:
            subprocess.Popen([winscp_path])
            QMessageBox.information(
                self,
                "WinSCP 起動中",
                "WinSCP を起動しました。\n\n"
                "NAS/サーバーに接続して、FLAC ファイルをアップロードしてください。\n"
                "アップロード完了後、WinSCP を閉じてください。"
            )
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"WinSCPの起動に失敗しました:\n{e}")
    
    # === サブステップ2: AAC関連 ===
    def on_open_aac_folder(self):
        """AACフォルダを開く"""
        if not self.album_folder:
            QMessageBox.warning(self, "エラー", "アルバムが選択されていません。")
            return
        
        # アーティスト名/アルバム名の構成を優先
        if self.workflow.state:
            album_name = self.workflow.state.get_album_name()
            sanitized_album_name = self._sanitize_foldername(album_name)
            artist_name = self.workflow.state.get_artist_name()
            sanitized_artist_name = self._sanitize_foldername(artist_name)
            aac_folder_specific = os.path.join(self.album_folder, "_aac_output", sanitized_artist_name, sanitized_album_name)
            
            # 具体的なアルバムフォルダが存在する場合はそちらを開く
            if os.path.exists(aac_folder_specific):
                try:
                    os.startfile(aac_folder_specific)
                    return
                except Exception as e:
                    QMessageBox.critical(self, "エラー", f"フォルダを開けませんでした:\n{e}")
                    return
        
        # フォールバック: _aac_output全体を開く
        aac_folder = os.path.join(self.album_folder, "_aac_output")
        if not os.path.exists(aac_folder):
            QMessageBox.warning(self, "エラー", f"AACフォルダが見つかりません:\n{aac_folder}")
            return
        
        try:
            os.startfile(aac_folder)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"フォルダを開けませんでした:\n{e}")
    
    def on_launch_itunes(self):
        """iTunes.exeを起動"""
        itunes_path = self.config.get_tool_path("iTunes")
        
        if not itunes_path or not os.path.exists(itunes_path):
            QMessageBox.information(
                self,
                "iTunes未設定",
                "iTunesのパスが設定されていないか、ファイルが見つかりません。\n\n"
                "config.ini の [Paths] セクションに\n"
                "iTunes = C:\\Program Files\\iTunes\\iTunes.exe\n"
                "のように設定してください。\n\n"
                "または、AACフォルダから手動でiTunesにドラッグ&ドロップしてください。"
            )
            return
        
        try:
            subprocess.Popen([itunes_path])
            QMessageBox.information(
                self,
                "iTunes 起動中",
                "iTunes を起動しました。\n\n"
                "AACフォルダからファイルをドラッグ&ドロップするか、\n"
                "手動で AAC ファイルをライブラリに追加してください。\n\n"
                "追加完了後、iTunes を閉じてください。"
            )
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"iTunesの起動に失敗しました:\n{e}")
    
    # === サブステップ3: Opus関連 ===
    def on_open_opus_folder(self):
        """Opusフォルダを開く"""
        if not self.album_folder:
            QMessageBox.warning(self, "エラー", "アルバムが選択されていません。")
            return
        
        # アーティスト名/アルバム名の構成を優先
        if self.workflow.state:
            album_name = self.workflow.state.get_album_name()
            sanitized_album_name = self._sanitize_foldername(album_name)
            artist_name = self.workflow.state.get_artist_name()
            sanitized_artist_name = self._sanitize_foldername(artist_name)
            opus_folder_specific = os.path.join(self.album_folder, "_opus_output", sanitized_artist_name, sanitized_album_name)
            
            # 具体的なアルバムフォルダが存在する場合はそちらを開く
            if os.path.exists(opus_folder_specific):
                try:
                    os.startfile(opus_folder_specific)
                    return
                except Exception as e:
                    QMessageBox.critical(self, "エラー", f"フォルダを開けませんでした:\n{e}")
                    return
        
        # フォールバック: _opus_output全体を開く
        opus_folder = os.path.join(self.album_folder, "_opus_output")
        if not os.path.exists(opus_folder):
            QMessageBox.warning(self, "エラー", f"Opusフォルダが見つかりません:\n{opus_folder}")
            return
        
        try:
            os.startfile(opus_folder)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"フォルダを開けませんでした:\n{e}")
    
    def on_open_music_folder(self):
        """ユーザーのMusicフォルダを開く"""
        music_folder = os.path.join(os.path.expanduser("~"), "Music")
        
        if not os.path.exists(music_folder):
            QMessageBox.warning(self, "エラー", f"Musicフォルダが見つかりません:\n{music_folder}")
            return
        
        try:
            os.startfile(music_folder)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"フォルダを開けませんでした:\n{e}")
    
    def on_launch_freefilesync(self):
        """FreeFileSyncを起動（設定ファイルを指定）"""
        ffs_path = self.config.get_tool_path("FreeFileSync")
        
        if not ffs_path or not os.path.exists(ffs_path):
            QMessageBox.information(
                self,
                "FreeFileSync未設定",
                "FreeFileSyncのパスが設定されていないか、ファイルが見つかりません。\n\n"
                "config.ini の [Paths] セクションに\n"
                "FreeFileSync = C:\\Program Files\\FreeFileSync\\FreeFileSync.exe\n"
                "のように設定してください。"
            )
            return
        
        # 設定ファイルパスを取得（オプション）
        config_file = None
        try:
            config_file = self.config.get_setting("freefilesync_config")
            if config_file:
                # 環境変数を展開
                config_file = self.config.expand_path(config_file)
        except Exception:
            pass
        
        try:
            if config_file and os.path.exists(config_file):
                # 設定ファイルを指定して起動
                subprocess.Popen([ffs_path, config_file])
            else:
                # 設定ファイルが無い場合は通常起動
                subprocess.Popen([ffs_path])
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"FreeFileSyncの起動に失敗しました:\n{e}")
    
    # === 最終完了 ===
    def on_complete(self):
        """全転送完了ボタン"""
        reply = QMessageBox.question(
            self,
            "確認",
            "Step 7（全サブステップ）を完了しますか?\n\n"
            "✓ FLAC → YouTube Music & NAS\n"
            "✓ AAC → iTunes取り込み済み\n"
            "✓ Opus → Music移動 & NAS同期済み\n\n"
            "全ての転送が完了したことを確認してください。\n\n"
            "⚠ 完了後、このアルバムの作業フォルダは削除されます。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # ステップ完了フラグを設定
            if self.workflow.state:
                self.workflow.state.mark_step_completed("step7_transfer")
                print("[DEBUG] Step7: ステップ完了フラグを設定しました")
            
            # 作業フォルダを削除
            self._delete_work_folder()
            
            # Step完了シグナルを発行
            self.step_completed.emit()
            print("[DEBUG] Step7: step_completed シグナルを発行しました")
    
    def _delete_work_folder(self):
        """作業フォルダを削除（内部処理）- send2trash でゴミ箱へ"""
        if not self.album_folder or not os.path.exists(self.album_folder):
            return
        
        try:
            from send2trash import send2trash
            send2trash(self.album_folder)
            print(f"[Step7] 作業フォルダをゴミ箱へ移動しました: {self.album_folder}")
            QMessageBox.information(
                self,
                "完了",
                f"作業フォルダをゴミ箱へ移動しました。\n\n"
                f"フォルダ: {os.path.basename(self.album_folder)}"
            )
        except Exception as e:
            # send2trash 失敗時は shutil.rmtree でフォールバック
            print(f"[Step7] send2trash 失敗、shutil.rmtree でリトライ: {e}")
            try:
                import shutil
                shutil.rmtree(self.album_folder)
                print(f"[Step7] 作業フォルダを削除しました（shutil.rmtree）: {self.album_folder}")
                QMessageBox.information(
                    self,
                    "完了",
                    f"作業フォルダを削除しました。\n\n"
                    f"フォルダ: {os.path.basename(self.album_folder)}"
                )
            except Exception as e2:
                # 両方失敗の場合のみユーザーに通知
                print(f"[Step7] 作業フォルダの削除に失敗: {e2}")
                QMessageBox.warning(
                    self,
                    "警告",
                    f"作業フォルダの削除に失敗しました。\n\n"
                    f"手動で削除してください:\n{self.album_folder}\n\n"
                    f"エラー: {e2}"
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

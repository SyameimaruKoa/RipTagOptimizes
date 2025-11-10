"""
Step 3: Mp3Tag (FLAC完成・タグ付け・リネーム)パネル
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QListWidget, QListWidgetItem, QGroupBox
)
from PySide6.QtCore import Signal, Qt

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager
from logic.external_tools import ExternalToolRunner
from logic.artwork_handler import check_album_has_artwork


class Step3TaggingPanel(QWidget):
    """Step 3: Mp3Tag (FLAC完成)パネル"""
    
    step_completed = Signal()
    
    def __init__(self, config: ConfigManager, workflow: WorkflowManager):
        super().__init__()
        self.config = config
        self.workflow = workflow
        self.album_folder = None
        self.tool_runner = None
        # 自動リフレッシュでも確認画面が消えないように維持フラグ
        self._force_show_mapping = False
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel("<h2>Step 3: FLAC完成 (タグ・リネーム)</h2>")
        layout.addWidget(title)
        
        # 説明
        desc = QLabel(
            "Mp3tag でFLACファイルのメタデータとファイル名を完成させます。\n"
            "Mp3tag を起動し、タグ編集とリネームを行ってください。\n"
            "完了後、ファイルの紐づけとアートワーク検査を行います。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # Mp3tag起動ボタン
        self.launch_button = QPushButton("Mp3tag を起動")
        self.launch_button.clicked.connect(self.on_launch_mp3tag)
        layout.addWidget(self.launch_button)

        # 直接再スキャンボタン（Mp3tagを使わずに紐づけのみ更新）
        self.rescan_button = QPushButton("ファイル再スキャン（紐づけを更新）")
        self.rescan_button.clicked.connect(self.on_rescan)
        layout.addWidget(self.rescan_button)
        
        # 手動紐づけボタン
        self.manual_mapping_button = QPushButton("手動紐づけ")
        self.manual_mapping_button.setToolTip("自動紐づけが失敗した場合に手動で設定します")
        self.manual_mapping_button.clicked.connect(self.on_manual_mapping)
        layout.addWidget(self.manual_mapping_button)

        layout.addSpacing(10)
        
        # ファイル紐づけエリア（Mp3tag終了後に表示）
        self.mapping_widget = QWidget()
        mapping_layout = QVBoxLayout()
        self.mapping_widget.setLayout(mapping_layout)
        self.mapping_widget.setVisible(False)
        
        mapping_label = QLabel("<b>ファイル紐づけ:</b>")
        mapping_layout.addWidget(mapping_label)
        
        mapping_desc = QLabel(
            "元のファイル名と現在のファイル名が自動的に更新されます。\n"
            "問題がなければ「完了」ボタンを押してください。"
        )
        mapping_desc.setWordWrap(True)
        mapping_layout.addWidget(mapping_desc)
        
        self.mapping_list = QListWidget()
        mapping_layout.addWidget(self.mapping_list)

        layout.addWidget(self.mapping_widget)
        # 余白を広げて下部行をボトムに固定
        layout.addStretch()

    # 下部: 左に手順ガイド、右に完了ボタン（左下に常時表示）
        bottom_row = QHBoxLayout()

        # 手順ガイド（左下に常時表示）
        self.hint_group = QGroupBox("やること（Mp3tag操作手順）")
        hint_v = QVBoxLayout()
        self.hint_label = QLabel()
        self.hint_label.setWordWrap(True)
        self.hint_label.setText(
            """
            <ol style='margin:0 0 0 16px; padding:0;'>
              <li>Mp3Tag起動</li>
              <li>インストを選択</li>
              <li>アクション: ジャンル「Instrumental」変更 → タイトル「Instrumental」追記 → タイトル「StemRoller」追記</li>
              <li>変換 → 自動ナンバリングウィザード（トラック番号を末尾追加）</li>
              <li>変換 → タグ→ファイル名</li>
              <li>%Track% %title% でリネーム</li>
              <li>終わり</li>
            </ol>
            """
        )
        hint_v.addWidget(self.hint_label)
        self.hint_group.setLayout(hint_v)
        bottom_row.addWidget(self.hint_group, 1)

        # 右側: 完了ボタン
        right_box = QHBoxLayout()
        self.complete_button = QPushButton("完了")
        self.complete_button.setEnabled(False)
        self.complete_button.clicked.connect(self.on_complete)
        right_box.addWidget(self.complete_button)
        right_box.addStretch()
        bottom_row.addLayout(right_box)

        layout.addLayout(bottom_row)
    
    def load_album(self, album_folder: str):
        """アルバムをロード"""
        self.album_folder = album_folder
        
        # 紐づけUIは非表示のまま（Mp3tag完了時のみ表示）
        self.mapping_widget.setVisible(False)
        self.complete_button.setEnabled(True)
    
    def on_launch_mp3tag(self):
        """Mp3tag を起動"""
        mp3tag_path = self.config.get_tool_path("Mp3Tag")
        
        if not mp3tag_path:
            QMessageBox.warning(
                self,
                "警告",
                "Mp3tag.exe が見つかりません。\n"
                "config.ini で Mp3Tag のパスを設定してください。"
            )
            return
        
        if not self.album_folder:
            QMessageBox.warning(self, "エラー", "アルバムフォルダが選択されていません。")
            return
        
        # Mp3tag を起動（FLAC はサブフォルダ _flac_src/アルバム名 を対象）
        self.tool_runner = ExternalToolRunner(self)
        self.tool_runner.finished.connect(self.on_mp3tag_finished)
        self.tool_runner.error_occurred.connect(self.on_mp3tag_error)
        
        target_dir = self.album_folder
        if self.workflow.state:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
            album_name = self.workflow.state.get_album_name()
            sanitized_album_name = self._sanitize_foldername(album_name)
            candidate = os.path.join(self.album_folder, raw_dirname, sanitized_album_name)
            if os.path.isdir(candidate):
                target_dir = candidate
        
        # 絶対パスに変換（相対パスの場合）
        target_dir = os.path.abspath(target_dir)
        
        # パスが存在するか確認
        if not os.path.exists(target_dir):
            QMessageBox.warning(
                self,
                "エラー",
                f"対象フォルダが存在しません:\n{target_dir}"
            )
            return
        
        print(f"[DEBUG] Mp3tag起動: target_dir = {target_dir}")

        success = self.tool_runner.run_gui_tool(
            mp3tag_path,
            [target_dir],
            target_dir
        )
        
        if success:
            self.launch_button.setEnabled(False)
            # 起動ポップは省略（ユーザー要望）
    
    def on_mp3tag_finished(self, exit_code, exit_status):
        """Mp3tag 終了時の処理"""
        self.launch_button.setEnabled(True)
        
        if exit_code != 0:
            QMessageBox.warning(
                self,
                "警告",
                f"Mp3tag が異常終了しました (Exit Code: {exit_code})"
            )
            return
        
        # ファイル紐づけを更新
        self.update_file_mapping()
        
        # アートワーク検査
        self.check_artwork()
        
        # 紐づけUIを表示（維持フラグON）
        self._force_show_mapping = True
        self.mapping_widget.setVisible(True)
        self.complete_button.setEnabled(True)
    
    def on_mp3tag_error(self, error_msg):
        """Mp3tag エラー時の処理"""
        self.launch_button.setEnabled(True)
        QMessageBox.critical(self, "エラー", f"Mp3tag の起動に失敗しました:\n{error_msg}")
    
    def update_file_mapping(self):
        """ファイル紐づけを更新"""
        if not self.album_folder or not self.workflow.state:
            return
        
        self.mapping_list.clear()

        # 現在のFLACファイルを取得（サブフォルダ _flac_src/アルバム名 優先）
        current_flac_files = []
        try:
            base_dir = self.album_folder
            if self.workflow.state:
                raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
                album_name = self.workflow.state.get_album_name()
                sanitized_album_name = self._sanitize_foldername(album_name)
                candidate = os.path.join(self.album_folder, raw_dirname, sanitized_album_name)
                if os.path.isdir(candidate):
                    base_dir = candidate
            for file in os.listdir(base_dir):
                if file.lower().endswith('.flac'):
                    current_flac_files.append(file)
        except Exception as e:
            print(f"[ERROR] FLACファイルの取得に失敗: {e}")
            return

        # 1) 先頭のトラック番号で紐づけ辞書を作る (最優先)
        #    同じトラック番号で「(Inst)」と通常版が両方ある場合は Inst を優先
        import re
        by_tracknum: dict[int, str] = {}

        def prefer_inst(existing: str | None, candidate: str) -> str:
            # 既存がInstなら維持、候補がInstなら置換、どちらも同等なら候補で上書き
            if existing:
                ex_is_inst = self._is_instrumental_by_name(existing.lower())
            else:
                ex_is_inst = False
            cand_is_inst = self._is_instrumental_by_name(candidate.lower())
            if ex_is_inst:
                return existing  # 既にInstを採用済み
            if cand_is_inst:
                return candidate  # Instを優先して採用
            return candidate      # どちらも通常なら最後のもの

        for fname in current_flac_files:
            m = re.match(r"^(\d{1,3})\s*[-．\. ]?\s*", fname)
            if m:
                try:
                    idx = int(m.group(1))
                    prev = by_tracknum.get(idx)
                    by_tracknum[idx] = prefer_inst(prev, fname)
                except ValueError:
                    pass

        # 2) トラック番号が無い/重複時のフォールバック: タイトル正規化での一致
        def norm_title(name: str, remove_version_info: bool = False) -> str:
            """
            ファイル名を正規化してマッチングに使用
            remove_version_info: Trueの場合はバージョン情報も削除（インスト検索用）
            """
            base = re.sub(r"\.[^.]+$", "", name)            # 拡張子除去
            base = re.sub(r"^(\d{1,3})\s*[-．\. ]?\s*", "", base)  # 先頭番号除去
            # インスト関連の括弧を除去
            base = re.sub(r"\s*\((?i:inst|off\s*vocal|instrumental|stemroller)\)\s*", "", base)
            
            if remove_version_info:
                # バージョン情報も削除（M@STER VERSION, GAME VERSION, オリジナル・カラオケなど）
                base = re.sub(r"\s*\((?i:m@ster\s*version|game\s*version|original\s*version|オリジナル[・・]カラオケ|カラオケ)\)\s*", "", base)
                # その他の末尾括弧も削除
                base = re.sub(r"\s*(\([^)]*\)\s*)+$", "", base)
            
            return base.strip().lower()

        by_title: dict[str, str] = {}
        by_title_inst: dict[str, str] = {}
        
        # 元曲ファイル名からトラック番号なしのタイトルへのマッピング
        # 例: "02-虹.flac" -> "虹"
        original_to_title_map: dict[str, str] = {}
        
        for f in current_flac_files:
            # 通常マッチング: バージョン情報を保持
            key = norm_title(f, remove_version_info=False)
            prev = by_title.get(key)
            by_title[key] = prefer_inst(prev, f)
            
            # Inst専用マップ: バージョン情報を削除して広くマッチング
            if self._is_instrumental_by_name(f.lower()):
                key_no_ver = norm_title(f, remove_version_info=True)
                # 複数のインストファイルがある場合、最新のものを使用
                if key_no_ver not in by_title_inst:
                    by_title_inst[key_no_ver] = f
                    print(f"[DEBUG] Instマップに追加: '{key_no_ver}' -> '{f}'")
                else:
                    # 既存のファイルと比較して、より適切な方を選択
                    existing = by_title_inst[key_no_ver]
                    # "02-虹 (Inst).flac" よりも "2 虹 (Instrumental) (StemRoller).flac" を優先
                    # 判定: より長いファイル名、または (StemRoller) を含む方を優先
                    if "(StemRoller)" in f or len(f) > len(existing):
                        by_title_inst[key_no_ver] = f
                        print(f"[DEBUG] Instマップを更新: '{key_no_ver}' -> '{f}' (旧: '{existing}')")
            else:
                # 元曲の場合、トラック番号なしのタイトルをマッピング
                key_no_ver = norm_title(f, remove_version_info=True)
                original_to_title_map[key_no_ver] = f
        
        # トラック情報を更新
        tracks = self.workflow.state.get_tracks()
        
        # 既存のoriginalFileを記録（インストファイルの重複登録を防ぐ）
        existing_original_files = {track.get("originalFile", "") for track in tracks}
        # 処理済みの物理ファイルを記録
        processed_files = set()

        for i, track in enumerate(tracks):
            original_file = track.get("originalFile", "")
            orig_norm = norm_title(original_file, remove_version_info=False)
            orig_norm_no_ver = norm_title(original_file, remove_version_info=True)
            
            # originalFileがインストファイルそのものの場合、紐づけをスキップして独立表示
            if self._is_instrumental_by_name(original_file.lower()):
                # 物理ファイルとして存在するか確認
                if original_file in current_flac_files:
                    final_filename = self._generate_final_filename(original_file)
                    track["finalFile"] = final_filename
                    track["currentFile"] = original_file
                    track["isInstrumental"] = True
                    processed_files.add(original_file)
                    
                    # 独立インストトラックとして表示
                    self._append_mapping_row_inst_only(original_file, final_filename)
                    print(f"[DEBUG] 独立インストトラック: {original_file} -> {final_filename}")
                else:
                    # 物理ファイルが存在しない場合は未検出として表示
                    self._append_mapping_row_not_found(original_file)
                continue
            
            # 先頭番号でマッチ（ボーカル入りトラック用）
            m = re.match(r"^(\d{1,3})", original_file)
            new_file = None
            if m:
                try:
                    idx = int(m.group(1))
                    candidate = by_tracknum.get(idx)
                    # トラック番号だけが変わった場合に誤紐づけしないよう、タイトル正規化で一致確認
                    if candidate is not None:
                        cand_norm = norm_title(candidate, remove_version_info=False)
                        # 候補がインストファイルの場合は除外（ボーカル入りを優先）
                        if not self._is_instrumental_by_name(candidate.lower()) and (cand_norm == orig_norm or not orig_norm):
                            new_file = candidate
                        else:
                            # 番号マッチは不一致と見なし、タイトルで改めて探す
                            new_file = None
                except ValueError:
                    new_file = None
            # タイトル正規化でマッチ（インストファイルを除外）
            if not new_file:
                candidate = by_title.get(norm_title(original_file, remove_version_info=False))
                if candidate and not self._is_instrumental_by_name(candidate.lower()):
                    new_file = candidate

            # マッチしない場合は、従来の安全策: 同名が存在すればそれを使う
            if not new_file and original_file in current_flac_files:
                if not self._is_instrumental_by_name(original_file.lower()):
                    new_file = original_file

            # それでも無ければスキップ（ユーザーに後で表示）
            if not new_file:
                # 未検出の行
                self._append_mapping_row_not_found(original_file)
                continue
            
            processed_files.add(new_file)

            # 同タイトルのInstパートナーを探す
            # 優先順位: 1) 自動検出（最新版優先）, 2) state.jsonに記録済みのinstrumentalFile
            inst_partner = None
            # まず自動検出を試す（Demucsで新しく生成されたファイルを優先）
            auto_detected = by_title_inst.get(orig_norm_no_ver)
            if auto_detected:
                inst_partner = auto_detected
                print(f"[DEBUG] 自動検出でinstrumentalFileを発見: {original_file} -> {inst_partner}")
            else:
                # 自動検出できない場合、state.jsonに記録済みのinstrumentalFileを使用
                existing_inst = track.get("instrumentalFile")
                if existing_inst and existing_inst in current_flac_files:
                    inst_partner = existing_inst
                    print(f"[DEBUG] 既存のinstrumentalFileを使用: {original_file} -> {inst_partner}")
                else:
                    print(f"[DEBUG] インストファイルが見つかりません: {original_file} (normalized: '{orig_norm_no_ver}')")

            # FLACファイルからタグ情報を読み取り、最終ファイル名を生成
            final_filename = self._generate_final_filename(new_file)
            
            # new_file がインストかどうか判定
            is_new_file_inst = self._is_instrumental_by_name(new_file.lower())
            
            # 通常ケース: new_file を最終成果物とし、Instが別にあれば派生として表示
            track["finalFile"] = final_filename
            track["isInstrumental"] = is_new_file_inst
            
            # インストファイルの表示判定
            # new_fileがインストの場合は、inst_partnerは表示しない（自分自身がインスト）
            if inst_partner and inst_partner != new_file and not is_new_file_inst:
                # インストゥルメンタル版のファイル名（現在のファイル名をそのまま使用）
                inst_display_name = inst_partner
                # state.jsonには最終ファイル名を記録
                inst_final_filename = self._generate_final_filename(inst_partner)
                track["instrumentalFile"] = inst_final_filename
                track["hasInstrumental"] = True
                track["currentFile"] = new_file
                processed_files.add(inst_partner)
                
                print(f"[DEBUG] 表示に追加: {original_file} -> {final_filename} + Inst: {inst_display_name}")
                
                # 表示: 親トラック + 子インスト
                self._append_mapping_row_with_inst(
                    original_file,
                    final_filename,
                    inst_display_name  # 生のファイル名を表示
                )
                
                # インストファイルを独立したトラックとしても追加（state.jsonに既に存在しない場合のみ）
                if inst_partner not in existing_original_files:
                    new_track = {
                        "id": f"track_{len(tracks) + 1:03d}",
                        "originalFile": inst_partner,
                        "finalFile": inst_final_filename,
                        "currentFile": inst_partner,
                        "demucsTarget": False,
                        "isInstrumental": True,
                        "hasInstrumental": False
                    }
                    tracks.append(new_track)
                    print(f"[DEBUG] 新規インストトラックを追加: {inst_partner}")
            else:
                # new_file 自体が Inst の場合はバッジ表示、それ以外は通常表示
                track["currentFile"] = new_file
                if track["isInstrumental"]:
                    self._append_mapping_row_inst_only(
                        original_file,
                        final_filename
                    )
                else:
                    self._append_mapping_row_normal(
                        original_file,
                        final_filename
                    )
        
        # 未処理のインストファイル（state.jsonに存在しない新規Demucs生成ファイル）を独立トラックとして追加
        for flac_file in current_flac_files:
            if flac_file not in processed_files and self._is_instrumental_by_name(flac_file.lower()):
                # 新規インストトラックとして追加
                final_filename = self._generate_final_filename(flac_file)
                new_track = {
                    "id": f"track_{len(tracks) + 1:03d}",
                    "originalFile": flac_file,
                    "finalFile": final_filename,
                    "currentFile": flac_file,
                    "demucsTarget": False,
                    "isInstrumental": True,
                    "hasInstrumental": False
                }
                tracks.append(new_track)
                processed_files.add(flac_file)
                
                # 表示に追加
                self._append_mapping_row_inst_only(flac_file, final_filename)
                print(f"[DEBUG] 未処理の新規インストトラックを追加: {flac_file} -> {final_filename}")
        
        # state.json に保存
        self.workflow.state.state["tracks"] = tracks
        self.workflow.state.save()

    # ------------------------
    # internal helpers
    # ------------------------
    def _append_mapping_row_normal(self, original: str, final: str):
        """通常トラック（インストなし）の表示"""
        item = QListWidgetItem()
        row = QWidget()
        lay = QHBoxLayout()
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)
        
        # アイコン
        icon = QLabel("🎵")
        icon.setFixedWidth(24)
        lay.addWidget(icon)
        
        # メインテキスト
        lbl = QLabel(f"{original}  →  {final}")
        lay.addWidget(lbl)
        
        lay.addStretch()
        row.setLayout(lay)
        item.setSizeHint(row.sizeHint())
        self.mapping_list.addItem(item)
        self.mapping_list.setItemWidget(item, row)
    
    def _append_mapping_row_inst_only(self, original: str, final: str):
        """インストのみのトラック表示"""
        item = QListWidgetItem()
        row = QWidget()
        lay = QHBoxLayout()
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)
        
        # アイコン
        icon = QLabel("🎹")
        icon.setFixedWidth(24)
        lay.addWidget(icon)
        
        # メインテキスト
        lbl = QLabel(f"{original}  →  {final}")
        lay.addWidget(lbl)
        
        # バッジ
        badge = QLabel("[Inst]")
        badge.setStyleSheet(
            "color: rgb(100, 200, 255); "
            "font-weight: 700; "
            "padding: 2px 6px; "
            "border: 1px solid rgb(100, 200, 255); "
            "border-radius: 3px;"
        )
        badge.setToolTip("インストゥルメンタル版")
        lay.addWidget(badge)
        
        lay.addStretch()
        row.setLayout(lay)
        item.setSizeHint(row.sizeHint())
        self.mapping_list.addItem(item)
        self.mapping_list.setItemWidget(item, row)
    
    def _append_mapping_row_with_inst(self, original: str, final: str, inst_final: str):
        """親トラック + 子インストの階層表示"""
        # 親トラック（通常版）
        parent_item = QListWidgetItem()
        parent_row = QWidget()
        parent_lay = QHBoxLayout()
        parent_lay.setContentsMargins(8, 4, 8, 4)
        parent_lay.setSpacing(8)
        
        # 親アイコン
        parent_icon = QLabel("🎵")
        parent_icon.setFixedWidth(24)
        parent_lay.addWidget(parent_icon)
        
        # 親テキスト
        parent_lbl = QLabel(f"{original}  →  {final}")
        parent_lay.addWidget(parent_lbl)
        
        parent_lay.addStretch()
        parent_row.setLayout(parent_lay)
        parent_item.setSizeHint(parent_row.sizeHint())
        self.mapping_list.addItem(parent_item)
        self.mapping_list.setItemWidget(parent_item, parent_row)
        
        # 子トラック（インスト）- インデントして表示
        child_item = QListWidgetItem()
        child_row = QWidget()
        child_lay = QHBoxLayout()
        child_lay.setContentsMargins(8, 2, 8, 4)
        child_lay.setSpacing(8)
        
        # インデント用スペース
        spacer = QLabel("    ")
        spacer.setFixedWidth(24)
        child_lay.addWidget(spacer)
        
        # 子アイコン
        child_icon = QLabel("└ 🎹")
        child_icon.setFixedWidth(48)
        child_icon.setStyleSheet("color: rgb(150, 150, 150);")
        child_lay.addWidget(child_icon)
        
        # 子テキスト
        child_lbl = QLabel(inst_final)
        child_lbl.setStyleSheet("color: rgb(100, 200, 255);")
        child_lay.addWidget(child_lbl)
        
        # バッジ
        badge = QLabel("インスト版")
        badge.setStyleSheet(
            "color: rgb(100, 200, 255); "
            "font-weight: 700; "
            "font-size: 10px; "
            "padding: 2px 6px; "
            "border: 1px solid rgb(100, 200, 255); "
            "border-radius: 3px;"
        )
        badge.setToolTip("このトラックから自動生成されたインストゥルメンタル版")
        child_lay.addWidget(badge)
        
        child_lay.addStretch()
        child_row.setLayout(child_lay)
        child_item.setSizeHint(child_row.sizeHint())
        self.mapping_list.addItem(child_item)
        self.mapping_list.setItemWidget(child_item, child_row)
    
    def _append_mapping_row_not_found(self, original: str):
        """未検出トラックの表示"""
        item = QListWidgetItem()
        row = QWidget()
        lay = QHBoxLayout()
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(8)
        
        # アイコン
        icon = QLabel("⚠️")
        icon.setFixedWidth(24)
        lay.addWidget(icon)
        
        # メインテキスト
        lbl = QLabel(f"{original}  →  ")
        lay.addWidget(lbl)
        
        # 未検出バッジ
        badge = QLabel("未検出")
        badge.setStyleSheet(
            "color: rgb(255, 150, 100); "
            "font-weight: 700; "
            "padding: 2px 6px; "
            "border: 1px solid rgb(255, 150, 100); "
            "border-radius: 3px;"
        )
        badge.setToolTip("対応するファイルが見つかりません。手動紐づけを使用してください。")
        lay.addWidget(badge)
        
        lay.addStretch()
        row.setLayout(lay)
        item.setSizeHint(row.sizeHint())
        self.mapping_list.addItem(item)
        self.mapping_list.setItemWidget(item, row)

    def _is_instrumental(self, filepath: str, filename: str) -> bool:
        """ファイル名/タグからインストかどうかを推定"""
        name = (filename or "").lower()
        if self._is_instrumental_by_name(name):
            return True
        try:
            if filepath and os.path.exists(filepath):
                from mutagen.flac import FLAC
                flac = FLAC(filepath)
                # genre / comment などに Instrumental を含むか
                def contains_key(key: str) -> bool:
                    try:
                        vals = flac.get(key, [])
                        return any("instrumental" in str(v).lower() for v in vals)
                    except Exception:
                        return False
                if contains_key("genre") or contains_key("comment") or contains_key("description"):
                    return True
        except Exception:
            pass
        return False

    def _is_instrumental_by_name(self, lower_name: str) -> bool:
        """ファイル名だけで簡易判定（小文字を渡す）"""
        keywords = [k.lower() for k in (self.config.get_demucs_keywords() or [])]
        keywords += ["inst", "instrumental", "off vocal", "off-vocal", "カラオケ"]
        return any(k in lower_name for k in keywords if k)

    def _generate_final_filename(self, current_filename: str) -> str:
        """FLACファイルからタグ情報を読み取り、最終的なファイル名を生成する
        形式: (Disc N-)トラック番号 タイトル.flac
        ディスク番号が1の場合または存在しない場合はディスク番号を省略
        """
        if not self.album_folder or not self.workflow.state:
            return current_filename
        
        # FLACファイルのパスを特定（_flac_src/アルバム名 内を優先）
        base_dir = self.album_folder
        raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        candidate = os.path.join(self.album_folder, raw_dirname, sanitized_album_name)
        if os.path.isdir(candidate):
            base_dir = candidate
        
        flac_path = os.path.join(base_dir, current_filename)
        if not os.path.exists(flac_path):
            # フォールバック: アルバムルート直下も確認
            flac_path = os.path.join(self.album_folder, current_filename)
            if not os.path.exists(flac_path):
                return current_filename
        
        try:
            from mutagen.flac import FLAC
            audio = FLAC(flac_path)
            
            # タグから情報取得
            track_num = audio.get("tracknumber", [""])[0]
            disc_num = audio.get("discnumber", ["1"])[0]
            title = audio.get("title", ["Unknown"])[0]
            
            # トラック番号を整形（分数形式の場合は最初の数値のみ、0埋め2桁）
            if "/" in str(track_num):
                track_num = str(track_num).split("/")[0]
            track_num_str = str(track_num).zfill(2) if track_num else "00"
            
            # ディスク番号を整形（分数形式の場合は最初の数値のみ）
            if "/" in str(disc_num):
                disc_num = str(disc_num).split("/")[0]
            try:
                disc_int = int(disc_num) if disc_num else 1
            except (ValueError, TypeError):
                disc_int = 1
            
            # ファイル名生成: ディスク番号が2以上の場合のみ接頭辞を追加
            if disc_int >= 2:
                new_filename = f"Disc {disc_int}-{track_num_str} {title}.flac"
            else:
                new_filename = f"{track_num_str} {title}.flac"
            
            # ファイル名禁止文字をサニタイズ
            new_filename = self._sanitize_filename(new_filename)
            
            return new_filename
            
        except Exception as e:
            print(f"[WARN] タグ読み取り失敗: {current_filename}: {e}")
            return current_filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """ファイル名に使用できない文字を全角等に置換"""
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
            filename = filename.replace(char, replacement)
        return filename

    def on_rescan(self):
        """Mp3tagを使わずに紐づけを再構築"""
        # Demucsスキップ時は再紐づけを無効化
        if self.workflow.state and self.workflow.state.get_flag("step2_skipped"):
            QMessageBox.warning(
                self,
                "再紐づけ不可",
                "Demucs処理をスキップした場合、自動再紐づけは使用できません。\n\n"
                "インストゥルメンタル版が作成されていないため、\n"
                "ファイル紐づけが不安定になる可能性があります。\n\n"
                "手動紐づけボタンを使用してください。"
            )
            return
        
        self.update_file_mapping()
        self.check_artwork()
        self._force_show_mapping = True
        self.mapping_widget.setVisible(True)
        self.complete_button.setEnabled(True)
    
    def check_artwork(self):
        """アートワーク検査"""
        if not self.album_folder or not self.workflow.state:
            return

        album_name = self.workflow.state.get_album_name()
        has_artwork = check_album_has_artwork(self.album_folder, album_name)
        self.workflow.state.set_artwork(has_artwork)
        # OKポップは不要（検査結果は state のみ更新）
    
    def on_complete(self):
        """完了ボタン - ReplayGain 自動適用後に次へ"""
        reply = QMessageBox.question(
            self,
            "確認",
            "Step 3 を完了しますか?\n\n"
            "ファイルの紐づけとアートワーク検査が完了しました。\n"
            "完了後、FLAC へ ReplayGain タグを自動付与します。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # ReplayGain 自動実行（設定で有効時のみ）
            self._apply_replaygain_if_enabled()
            # 完了後は維持フラグを解除
            self._force_show_mapping = False
            self.step_completed.emit()

    def _apply_replaygain_if_enabled(self):
        """ReplayGain を foobar2000 で測定（アルバムゲイン含む、config.ini 設定に基づく）"""
        try:
            enabled = str(self.config.get_setting("AutoReplayGain", "1")).strip() not in ("0", "false", "False")
        except Exception:
            enabled = True
        if not enabled:
            return

        foobar_path = self.config.get_tool_path("Foobar2000")
        if not foobar_path or not os.path.exists(foobar_path):
            print("[WARN] foobar2000 が見つかりません。ReplayGain をスキップします。")
            return

        if not self.workflow.state or not self.album_folder:
            return

        # _flac_src/アルバム名 配下の全 FLAC へ適用
        try:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
        except Exception:
            raw_dirname = "_flac_src"
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        flac_src_dir = os.path.join(self.album_folder, raw_dirname, sanitized_album_name)
        if not os.path.isdir(flac_src_dir):
            return

        flac_files = [os.path.join(flac_src_dir, f) for f in os.listdir(flac_src_dir) if f.lower().endswith('.flac')]
        if not flac_files:
            return

        # foobar2000 で ReplayGain スキャン実行
        # コマンド: foobar2000.exe /playlist_command:"ReplayGain/Scan per-file track gain" <files>
        import subprocess
        try:
            # まずファイルをfoobarへ追加してReplayGainスキャン
            args = [foobar_path, "/add"] + flac_files + ["/immediate"]
            subprocess.Popen(args)
            
            # ユーザーへ案内ダイアログ表示
            QMessageBox.information(
                self,
                "ReplayGain 測定",
                f"foobar2000 を起動しました。\n\n"
                f"手動で以下の操作を行ってください:\n"
                f"1. 追加された {len(flac_files)} ファイルを選択\n"
                f"2. 右クリック → ReplayGain → Scan per-file track gain\n"
                f"3. (アルバムゲインも必要なら) Scan as albums (by tags)\n\n"
                f"測定完了後、foobar2000 を閉じてください。"
            )
            print(f"[INFO] foobar2000 で ReplayGain 測定を開始しました（{len(flac_files)} ファイル）")
        except Exception as e:
            print(f"[WARN] ReplayGain 測定起動に失敗（非致命）: {e}")
    
    def on_manual_mapping(self):
        """手動紐づけダイアログを表示"""
        if not self.workflow.state or not self.album_folder:
            QMessageBox.warning(self, "エラー", "アルバムが読み込まれていません。")
            return
        
        from gui.manual_mapping_dialog import ManualMappingDialog
        
        # 現在のトラック情報を取得
        tracks = self.workflow.state.get_tracks()
        
        # _flac_src/アルバム名 ディレクトリから実際のファイル一覧を取得
        try:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
        except Exception:
            raw_dirname = "_flac_src"
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        flac_src_dir = os.path.join(self.album_folder, raw_dirname, sanitized_album_name)
        
        if not os.path.isdir(flac_src_dir):
            QMessageBox.warning(self, "エラー", f"{raw_dirname}/{sanitized_album_name} フォルダが見つかりません。")
            return
        
        actual_files = sorted([f for f in os.listdir(flac_src_dir) if f.lower().endswith('.flac')])
        
        print(f"[DEBUG] 手動紐づけダイアログ用ファイル一覧: {len(actual_files)} 個")
        for f in actual_files:
            print(f"[DEBUG]   - {f}")
        
        if not actual_files:
            QMessageBox.warning(self, "エラー", "FLACファイルが見つかりません。")
            return
        
        # ダイアログを表示
        dialog = ManualMappingDialog(tracks, actual_files, self)
        if dialog.exec():
            # 更新されたトラック情報を保存
            updated_tracks = dialog.get_updated_tracks()
            self.workflow.state.state["tracks"] = updated_tracks
            self.workflow.state.save()
            
            # UIを更新
            self.update_file_mapping()
            self._force_show_mapping = True
            self.mapping_widget.setVisible(True)
            
            QMessageBox.information(self, "完了", "ファイル紐づけを手動で更新しました。")
    
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

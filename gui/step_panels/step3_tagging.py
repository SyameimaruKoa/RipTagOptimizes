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
from logic.utils import sanitize_foldername, sanitize_filename


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
        
        # インスト同期ボタン
        self.sync_inst_button = QPushButton("インストを一括同期 (タグ・リネーム)")
        self.sync_inst_button.setToolTip("手動タグ付けした原曲からメタデータをインストへコピーし、ファイル名も同期します")
        self.sync_inst_button.setStyleSheet("font-weight: bold; color: #2b78e4;")
        self.sync_inst_button.clicked.connect(self.on_sync_instrumental)
        layout.addWidget(self.sync_inst_button)
        
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
              <li>原曲のタグ編集と %Track%-%title% でリネームをして保存</li>
              <li>Mp3Tagを閉じる</li>
              <li>「インストを一括同期」ボタンを押す<br>
                  <span style='font-size:10px; color:#888;'>(自動でタグと画像コピー、Genre・Titleの(Inst)(StemRoller)付与、名前変更が行われます)</span>
              </li>
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
            
        import glob
        all_flac_files = glob.glob(os.path.join(target_dir, "*.flac"))
        
        generated_inst_files = set()
        if self.workflow.state:
            for track in self.workflow.state.get_tracks():
                inst = track.get("currentInstFile") or track.get("instrumentalFile")
                if inst:
                    generated_inst_files.add(inst.lower())
                    
        target_files = []
        for f in all_flac_files:
            fname = os.path.basename(f).lower()
            # 親トラックに紐づいている（＝生成された）インストゥルメンタルファイルのみを除外
            if fname in generated_inst_files:
                continue
            target_files.append(f)
            
        if not target_files:
            target_files = [target_dir]
            args = target_files
        else:
            # オリジナルファイルのみを対象とするプレイリストを作成
            playlist_path = os.path.join(target_dir, "_mp3tag_target.m3u8")
            try:
                with open(playlist_path, 'w', encoding='utf-8') as f:
                    for filepath in target_files:
                        f.write(filepath + "\n")
                args = [playlist_path]
            except Exception as e:
                print(f"[ERROR] プレイリスト作成失敗: {e}")
                args = [target_dir]
        
        print(f"[DEBUG] Mp3tag起動: target_dir = {target_dir}")

        success = self.tool_runner.run_gui_tool(
            mp3tag_path,
            args,
            target_dir
        )
        
        if success:
            self.launch_button.setEnabled(False)
            # Mp3tag起動確認ダイアログ
            QMessageBox.information(
                self,
                "Mp3tag 起動中",
                "Mp3tag を起動しました。\n\n"
                "ファイルのメタデータ編集とリネームを行ってください。\n"
                "作業が完了したら、Mp3tag を閉じてください。\n\n"
                "⏱️ 自動検出：Mp3tag の終了を監視中..."
            )
    
    def on_mp3tag_finished(self, exit_code, exit_status):
        """Mp3tag 終了時の処理"""
        self.launch_button.setEnabled(True)
        self._cleanup_playlist()
        
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
        self._cleanup_playlist()
        QMessageBox.critical(self, "エラー", f"Mp3tag の起動に失敗しました:\n{error_msg}")
        
    def _cleanup_playlist(self):
        """Mp3tag用の一時プレイリストファイルを削除"""
        if not self.album_folder or not self.workflow.state:
            return
        try:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
            album_name = self.workflow.state.get_album_name()
            sanitized_album_name = self._sanitize_foldername(album_name)
            target_dir = os.path.join(self.album_folder, raw_dirname, sanitized_album_name)
            playlist_path = os.path.join(target_dir, "_mp3tag_target.m3u8")
            if os.path.exists(playlist_path):
                os.remove(playlist_path)
                print(f"[DEBUG] クリーンアップ: {playlist_path} を削除しました")
        except Exception as e:
            print(f"[WARN] プレイリストのクリーンアップに失敗: {e}")
    
    def update_file_mapping(self):
        """ファイル紐づけを更新"""
        if not self.album_folder or not self.workflow.state:
            return
        
        self.mapping_list.clear()

        # 現在のFLACファイルを取得（サブフォルダ _flac_src/アルバム名 優先）
        current_flac_files = []
        base_dir = self.album_folder
        try:
            if self.workflow.state:
                raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
                album_name = self.workflow.state.get_album_name()
                sanitized_album_name = self._sanitize_foldername(album_name)
                candidate = os.path.join(self.album_folder, raw_dirname, sanitized_album_name)
                if os.path.isdir(candidate):
                    base_dir = candidate
                    
            # 再帰的に検索して相対パスを保存（demucs_ignore などは除外）
            for root, dirs, files in os.walk(base_dir):
                if 'demucs_ignore' in dirs:
                    dirs.remove('demucs_ignore')
                for file in files:
                    if file.lower().endswith('.flac'):
                        rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                        rel_path = rel_path.replace('\\', '/')
                        current_flac_files.append(rel_path)
        except Exception as e:
            print(f"[ERROR] FLACファイルの取得に失敗: {e}")
            return

        current_flac_files.sort()
        print(f"[DEBUG][Step3] update_file_mapping 開始: album_folder={self.album_folder}, base_dir={base_dir}, flac_count={len(current_flac_files)}")
        for idx, flac_path in enumerate(current_flac_files, start=1):
            print(f"[DEBUG][Step3]   SCAN[{idx:02d}] {flac_path}")

        def _get_basename(fpath: str) -> str:
            return os.path.basename(fpath)

        def _find_by_basename(filename: str) -> str | None:
            if filename in current_flac_files:
                return filename
            target = _get_basename(filename)
            matches = [f for f in current_flac_files if _get_basename(f) == target]
            return matches[0] if len(matches) == 1 else None

        import re
        import difflib

        def track_key(name):
            match = re.match(r"^(?:Disc\s+(\d+)-)?(\d{1,3})(?=\D|$)", _get_basename(name), re.I)
            return (int(match.group(1) or 1), int(match.group(2))) if match else None

        # バージョン違いを区別したタイトル正規化。
        def norm_title(name: str) -> str:
            """曲番号とインスト表記を除去し、バージョン名は保持する。"""
            base = _get_basename(name)
            base = re.sub(r"\.[^.]+$", "", base)            # 拡張子除去
            base = re.sub(r"^(?:Disc\s+\d+-)?(\d{1,3})\s*[-．\. ]?\s*", "", base, flags=re.I)  # 先頭番号除去
            # インスト関連の括弧を除去
            base = re.sub(r"\s*\((?i:inst|off\s*vocal|instrumental|stemroller)\)\s*", "", base)
            
            return base.strip().lower()

        by_tracknum = {}
        by_title = {}
        by_title_inst = {}
        for name in current_flac_files:
            if self._is_instrumental_by_name(name.lower()):
                by_title_inst.setdefault(norm_title(name), []).append(name)
            else:
                by_title.setdefault(norm_title(name), []).append(name)
                key = track_key(name)
                if key is not None:
                    by_tracknum.setdefault(key, []).append(name)

        # トラック情報を更新
        tracks = self.workflow.state.get_tracks()
        print(f"[DEBUG][Step3] state tracks 読込: track_count={len(tracks)}")
        
        used_track_ids = {track.get("id") for track in tracks}
        processed_files = set()
        assigned_vocal_files = set()
        assigned_inst_files = set()
        final_tracks = []

        # 有効な既存対応を先に予約し、別の曲の自動推測で奪わない。
        vocal_owners = {}
        inst_owners = {}
        for track in tracks:
            for keys, owners in [(("currentFile", "originalFile"), vocal_owners),
                                 (("currentInstFile", "instrumentalFile"), inst_owners)]:
                for key in keys:
                    stored = track.get(key)
                    found = _find_by_basename(stored) if stored else None
                    if found:
                        owners.setdefault(found, set()).add(id(track))
                        break

        def available(track, candidate, assigned, owners):
            return candidate is not None and candidate not in assigned and (
                not owners.get(candidate) or owners[candidate] == {id(track)}
            )

        def is_vocal_candidate_available(track, candidate):
            return available(track, candidate, assigned_vocal_files, vocal_owners) and not self._is_instrumental_by_name(candidate.lower())

        def same_disc(original, candidate):
            first, second = track_key(original), track_key(candidate)
            return first is None or second is None or first[0] == second[0]

        # 1. ボーカル曲（非インスト曲）トラックを優先して紐づけ処理
        vocal_track_items = [t for t in tracks if not self._is_instrumental_by_name(t.get("originalFile", "").lower())]
        inst_track_items = [t for t in tracks if self._is_instrumental_by_name(t.get("originalFile", "").lower())]

        for track in vocal_track_items:
            original_file = track.get("originalFile", "")
            orig_norm = norm_title(original_file)
            original_track_num = track_key(original_file)
            new_file = None
            strategy = "not-found"
            for key in ("currentFile", "originalFile"):
                stored = track.get(key)
                candidate = _find_by_basename(stored) if stored else None
                if is_vocal_candidate_available(track, candidate):
                    new_file, strategy = candidate, key
                    break

            if new_file is None and original_track_num is not None:
                candidates = [name for name in by_tracknum.get(original_track_num, [])
                              if is_vocal_candidate_available(track, name) and
                              (norm_title(name) == orig_norm or
                               difflib.SequenceMatcher(None, norm_title(name), orig_norm).ratio() >= 0.85)]
                if len(candidates) == 1:
                    new_file, strategy = candidates[0], "tracknum-unique"

            if new_file is None:
                candidates = [name for name in by_title.get(orig_norm, [])
                              if is_vocal_candidate_available(track, name) and same_disc(original_file, name)]
                if len(candidates) == 1:
                    new_file, strategy = candidates[0], "title-unique"

            # 番号がない場合の軽微なタイポのみ。複数の近い候補がある場合は保留。
            if new_file is None and original_track_num is None:
                ranked = sorted(
                    [(difflib.SequenceMatcher(None, title, orig_norm).ratio(), name)
                     for title, names in by_title.items() for name in names
                     if is_vocal_candidate_available(track, name)], reverse=True
                )
                if ranked and ranked[0][0] >= 0.85 and (len(ranked) == 1 or ranked[0][0] - ranked[1][0] >= 0.1):
                    new_file, strategy = ranked[0][1], "fuzzy-unique"
            print(f"[DEBUG][Step3][MATCH] strategy={strategy} original='{original_file}' candidate='{new_file}'")

            # それでも無ければスキップ（ユーザーに後で表示）
            if not new_file:
                # 未検出の行
                self._append_mapping_row_not_found(original_file)
                print(f"[WARN][Step3][MATCH] strategy=not-found original='{original_file}'")
                track["currentFile"] = ""
                track["finalFile"] = ""
                track["hasInstrumental"] = False
                track.pop("isInstrumental", None)
                track.pop("instrumentalFile", None)
                track.pop("currentInstFile", None)
                final_tracks.append(track)
                continue
            
            assigned_vocal_files.add(new_file)
            processed_files.add(new_file)
            print(f"[DEBUG][Step3][MATCH] selected original='{original_file}' -> current='{new_file}'")

            # 明示済みの対応、次に一意なタイトル一致だけを採用する。
            # 同じインストの複数原曲への割当と、低い類似度による誤同期を防ぐ。
            inst_partner = None
            for key in ("currentInstFile", "instrumentalFile"):
                existing = track.get(key)
                found = _find_by_basename(existing) if existing else None
                if available(track, found, assigned_inst_files, inst_owners) and self._is_instrumental_by_name(found.lower()):
                    inst_partner = found
                    break
            if inst_partner is None:
                candidates = set(by_title_inst.get(norm_title(new_file), []))
                if not candidates:
                    candidates = set(by_title_inst.get(orig_norm, []))
                candidates = {name for name in candidates if available(track, name, assigned_inst_files, inst_owners) and same_disc(new_file, name)}
                if len(candidates) == 1:
                    inst_partner = candidates.pop()

            # FLACファイルからタグ情報を読み取り、最終ファイル名を生成
            final_filename = self._generate_final_filename(new_file)
            
            # new_file がインストかどうか判定
            is_new_file_inst = self._is_instrumental_by_name(new_file.lower())
            
            track["finalFile"] = final_filename
            track["isInstrumental"] = is_new_file_inst
            
            if inst_partner and inst_partner != new_file and not is_new_file_inst:
                inst_display_name = inst_partner
                inst_final_filename = self._generate_final_filename(inst_partner)
                track["instrumentalFile"] = inst_final_filename
                track["currentInstFile"] = inst_partner
                track["hasInstrumental"] = True
                track["currentFile"] = new_file
                processed_files.add(inst_partner)
                assigned_inst_files.add(inst_partner)
                
                print(f"[DEBUG][Step3][UI] 表示に追加: {original_file} -> {final_filename} + Inst: {inst_display_name}")
                
                self._append_mapping_row_with_inst(
                    original_file,
                    final_filename,
                    inst_display_name
                )
            else:
                track["currentFile"] = new_file
                track["hasInstrumental"] = False
                track.pop("instrumentalFile", None)
                track.pop("currentInstFile", None)
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
            final_tracks.append(track)
        
        # 2. 元々state.jsonに存在したインストトラックの処理
        for track in inst_track_items:
            original_file = track.get("originalFile", "")
            found_original = _find_by_basename(track.get("currentFile") or original_file)
            if not found_original:
                found_original = _find_by_basename(original_file)
            
            if (found_original and found_original in assigned_inst_files) or (original_file in assigned_inst_files):
                print(f"[DEBUG][Step3][INST] インストトラック '{original_file}' はボーカル曲のインストとして紐づけ済みのため独立トラックから除外")
                continue
            
            if found_original and found_original in processed_files:
                print(f"[DEBUG][Step3][INST] インストファイル '{found_original}' は既に処理済みのため独立トラックから除外")
                continue

            if found_original:
                final_filename = self._generate_final_filename(found_original)
                track["finalFile"] = final_filename
                track["currentFile"] = found_original
                track["isInstrumental"] = True
                track["hasInstrumental"] = False
                track.pop("instrumentalFile", None)
                track.pop("currentInstFile", None)
                processed_files.add(found_original)

                self._append_mapping_row_inst_only(found_original, final_filename)
                print(f"[DEBUG] 独立インストトラック: {found_original} -> {final_filename}")
                final_tracks.append(track)
            else:
                self._append_mapping_row_not_found(original_file)
                track["currentFile"] = ""
                track["finalFile"] = ""
                track["hasInstrumental"] = False
                final_tracks.append(track)

        # 3. 未処理のインストファイル（state.jsonに存在しない新規Demucs生成ファイル等）を独立トラックとして追加
        for flac_file in current_flac_files:
            if flac_file not in processed_files and self._is_instrumental_by_name(flac_file.lower()):
                final_filename = self._generate_final_filename(flac_file)
                next_id = 1
                while f"track_{next_id:03d}" in used_track_ids:
                    next_id += 1
                track_id = f"track_{next_id:03d}"
                used_track_ids.add(track_id)
                new_track = {
                    "id": track_id,
                    "originalFile": flac_file,
                    "finalFile": final_filename,
                    "currentFile": flac_file,
                    "demucsTarget": False,
                    "isInstrumental": True,
                    "hasInstrumental": False
                }
                final_tracks.append(new_track)
                processed_files.add(flac_file)
                
                self._append_mapping_row_inst_only(flac_file, final_filename)
                print(f"[DEBUG][Step3][INST] 未処理の新規インストトラックを追加: {flac_file} -> {final_filename}")
        
        # 再スキャンでは既存音源の番号・ディスクを変更しない。
        # 生成インストの採番は実ファイルのタグも更新する同期処理で行う。

        print(f"[DEBUG][Step3] update_file_mapping 完了: assigned_vocal={len(assigned_vocal_files)}, processed_files={len(processed_files)}, final_tracks={len(final_tracks)}")
        
        # 5. state.json に保存
        self.workflow.state.state["tracks"] = final_tracks
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
                        vals = flac.get(key)
                        if not vals:
                            return False
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
        import re
        name = os.path.basename(lower_name.replace('\\', '/'))
        english = r"\b(?:inst(?:rumental)?|off[ -]?vocal|backing track|karaoke|voiceless|minus one)\b"
        japanese = ("オリジナル・カラオケ", "インスト", "オフボーカル", "オフボ", "カラオケ", "歌無し")
        return bool(re.search(english, name, re.IGNORECASE)) or any(k in name for k in japanese)

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
        return sanitize_filename(filename)

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

    def on_sync_instrumental(self):
        """原曲のタグとファイル名をインストゥルメンタルファイルに同期させる"""
        if not self.workflow.state or not self.album_folder:
            QMessageBox.warning(self, "エラー", "アルバムが読み込まれていません。")
            return
            
        reply = QMessageBox.question(
            self,
            "確認",
            "手動でタグ付けされた原曲のメタデータを、生成されたインストへ自動コピーします。\n\n"
            "※インストのタグと名前を更新します。別の音源と名前が衝突する場合は更新しません。\n"
            "実行しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if reply != QMessageBox.Yes:
            return

        # 最新のファイル紐づけ状態を反映させる
        self.update_file_mapping()

        try:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
        except Exception:
            raw_dirname = "_flac_src"
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        flac_src_dir = os.path.join(self.album_folder, raw_dirname, sanitized_album_name)

        if not os.path.isdir(flac_src_dir):
            QMessageBox.warning(self, "エラー", f"フォルダが見つかりません:\n{flac_src_dir}")
            return

        tracks = self.workflow.state.get_tracks()
        success_count = 0
        error_count = 0

        from mutagen.flac import FLAC
        import shutil

        # ディスクごとの最大トラック番号と、生成されるインストの数を事前計算する
        max_track_per_disc = {}
        inst_count_per_disc = {}
        inst_index_map = {}
        inst_candidates = {}
        for track in tracks:
            # CDに含まれる独立インストも既存のトラック番号として数える。
            orig_filename = track.get("currentFile") or track.get("originalFile")
            if orig_filename:
                orig_path = os.path.join(flac_src_dir, orig_filename)
                if os.path.exists(orig_path):
                    try:
                        tmp_flac = FLAC(orig_path)
                        t_num = str(tmp_flac.get("tracknumber", ["0"])[0])
                        if "/" in t_num:
                            t_num = t_num.split("/")[0]
                            
                        d_num = str(tmp_flac.get("discnumber", ["1"])[0])
                        if "/" in d_num:
                            d_num = d_num.split("/")[0]
                            
                        if t_num.isdigit():
                            max_track_per_disc[d_num] = max(max_track_per_disc.get(d_num, 0), int(t_num))
                            
                        if track.get("demucsTarget") and track.get("hasInstrumental"):
                            inst_count_per_disc[d_num] = inst_count_per_disc.get(d_num, 0) + 1
                            inst_candidates.setdefault(d_num, []).append((int(t_num), track["id"]))
                    except Exception:
                        pass
        
        for candidates in inst_candidates.values():
            for index, (_, track_id) in enumerate(sorted(candidates), 1):
                inst_index_map[track_id] = index

        if not max_track_per_disc:
            max_track_per_disc["1"] = len([t for t in tracks if not t.get("isInstrumental")])

        for track in tracks:
            # Demucs対象であり、かつインストファイルが生成されているものを対象
            if not track.get("demucsTarget") or not track.get("hasInstrumental"):
                continue

            orig_filename = track.get("currentFile") or track.get("originalFile")
            # 最新のパスはcurrentInstFileに入っている。なければ後方互換でinstrumentalFileから拾う
            inst_filename = track.get("currentInstFile") or track.get("instrumentalFile")

            if not orig_filename or not inst_filename:
                continue

            orig_path = os.path.join(flac_src_dir, orig_filename)
            inst_path = os.path.join(flac_src_dir, inst_filename)

            if not os.path.exists(orig_path) or not os.path.exists(inst_path):
                print(f"[WARN] ファイルが見つかりません。orig: {orig_path}, inst: {inst_path}")
                continue

            try:
                # 1. メタデータの全コピー
                orig_flac = FLAC(orig_path)
                inst_flac = FLAC(inst_path)

                inst_flac.clear()  # メモリ上だけでタグを置換
                for k, v in (orig_flac.tags or {}).items():
                    inst_flac[k] = v

                inst_flac.clear_pictures()
                for pic in orig_flac.pictures:
                    inst_flac.add_picture(pic)

                # 2. ジャンル変更
                inst_flac["genre"] = ["Instrumental"]

                # 3. タイトルに「Instrumental」「StemRoller」を追記
                original_title = orig_flac.get("title", [""])[0] if "title" in orig_flac else ""
                new_title = original_title
                if "Instrumental" not in new_title:
                    new_title += " (Instrumental)"
                if "StemRoller" not in new_title:
                    new_title += " (StemRoller)"
                inst_flac["title"] = [new_title]

                # 4. トラック番号の連番化 (そのディスクの最後のトラック番号の次から付与)
                orig_track_num = orig_flac.get("tracknumber", ["0"])[0]
                if "/" in str(orig_track_num):
                    orig_track_num = str(orig_track_num).split("/")[0]
                    
                orig_disc_num = orig_flac.get("discnumber", ["1"])[0]
                if "/" in str(orig_disc_num):
                    orig_disc_num = str(orig_disc_num).split("/")[0]
                
                max_original_for_disc = max_track_per_disc.get(str(orig_disc_num), 1)
                
                inst_idx = inst_index_map.get(track.get("id"))
                if inst_idx is not None:
                    new_track_int = max_original_for_disc + inst_idx
                else:
                    new_track_int = max_original_for_disc + 1

                inst_flac["tracknumber"] = [str(new_track_int)]
                
                # 合わせて全体のトラック数(tracktotal/totaltracks)も更新する
                inst_adds = inst_count_per_disc.get(str(orig_disc_num), 0)
                if "tracktotal" in inst_flac:
                    orig_total = str(inst_flac["tracktotal"][0])
                    if orig_total.isdigit():
                        inst_flac["tracktotal"] = [str(int(orig_total) + inst_adds)]
                if "totaltracks" in inst_flac:
                    orig_total = str(inst_flac["totaltracks"][0])
                    if orig_total.isdigit():
                        inst_flac["totaltracks"] = [str(int(orig_total) + inst_adds)]

                # 5. ファイル名のリネーム
                ext = os.path.splitext(orig_filename)[1]
                track_num_str = str(new_track_int).zfill(2)

                # "%Track%-%title%" の形式にする
                disc_prefix = f"Disc {orig_disc_num}-" if str(orig_disc_num).isdigit() and int(orig_disc_num) > 1 else ""
                new_inst_basename = f"{disc_prefix}{track_num_str}-{new_title}{ext}"
                new_inst_basename = self._sanitize_filename(new_inst_basename)

                # サブフォルダには留めず、直下に移動させる
                new_inst_filename = new_inst_basename
                
                new_inst_path = os.path.join(flac_src_dir, new_inst_filename)

                from logic.instrumental_import import save_synced_instrumental
                save_synced_instrumental(inst_path, new_inst_path, inst_flac)
                track["instrumentalFile"] = new_inst_filename
                track["currentInstFile"] = new_inst_filename

                success_count += 1

            except Exception as e:
                print(f"[ERROR] インスト同期エラー ({orig_filename}): {e}")
                error_count += 1
                
        # stateを保存
        self.workflow.state.state["tracks"] = tracks
        self.workflow.state.save()

        # UIを再更新
        self.update_file_mapping()
        self._force_show_mapping = True
        self.mapping_widget.setVisible(True)

        QMessageBox.information(
            self,
            "同期完了",
            f"{success_count} 曲のインストゥルメンタルメタデータを同期しました。\n"
            f"(失敗: {error_count} 曲)"
        )

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
            # 完了時にサブフォルダ内ファイルを直下へ移動し、フラットな状態にする
            self._flatten_flac_dir()

            self.update_file_mapping()
            if not self.workflow.state or not self.workflow.state.get_tracks() or any(
                not t.get("currentFile") or not t.get("finalFile")
                for t in self.workflow.state.get_tracks()
            ):
                QMessageBox.warning(self, "未検出の曲があります", "ファイルの紐づけを確認してから完了してください。")
                return
            if not self.workflow.state.save():
                QMessageBox.warning(self, "保存エラー", "紐づけの保存に失敗しました。")
                return
            
            # ReplayGain 自動実行（設定で有効時のみ）
            self._apply_replaygain_if_enabled()
            # 完了後は維持フラグを解除
            self._force_show_mapping = False
            self.step_completed.emit()

    def _flatten_flac_dir(self):
        """FLACディレクトリ内のサブフォルダにあるファイルを直下へ移動し、空のサブフォルダを削除する"""
        if not self.workflow.state or not self.album_folder:
            return

        try:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
        except Exception:
            raw_dirname = "_flac_src"
        
        album_name = self.workflow.state.get_album_name()
        sanitized_album_name = self._sanitize_foldername(album_name)
        flac_src_dir = os.path.join(self.album_folder, raw_dirname, sanitized_album_name)

        if not os.path.isdir(flac_src_dir):
            return

        import shutil
        moved_any = False
        
        # サブフォルダ内のファイルを直下に移動
        for root, dirs, files in os.walk(flac_src_dir, topdown=False):
            if root == flac_src_dir:
                continue
                
            for file in files:
                if file.lower().endswith('.flac'):
                    src_path = os.path.join(root, file)
                    dst_path = os.path.join(flac_src_dir, file)
                    
                    # 万が一被る場合はリネームして退避
                    if os.path.exists(dst_path):
                        base, ext = os.path.splitext(file)
                        dst_path = os.path.join(flac_src_dir, f"{base}_moved_{os.urandom(4).hex()}{ext}")
                    
                    try:
                        shutil.move(src_path, dst_path)
                        moved_any = True
                    except Exception as e:
                        print(f"[WARN] ファイル移動失敗: {src_path} -> {dst_path} ({e})")
            
            # 空ならフォルダを削除
            try:
                if not os.listdir(root):
                    os.rmdir(root)
            except Exception:
                pass
        
        if moved_any:
            print("[INFO] サブフォルダのFLACファイルを直下に配置しました。")
            # 配置変更を state に反映させるため、改めて再マッピングを実行
            self.update_file_mapping()

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

        # サブフォルダ含めてファイル一覧を取得
        actual_files = []
        for root, dirs, files in os.walk(flac_src_dir):
            if 'demucs_ignore' in dirs:
                dirs.remove('demucs_ignore')
            for f in files:
                if f.lower().endswith('.flac'):
                    rel_path = os.path.relpath(os.path.join(root, f), flac_src_dir)
                    rel_path = rel_path.replace('\\', '/')
                    actual_files.append(rel_path)
        actual_files.sort()

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
            previous_tracks = self.workflow.state.get_tracks()
            self.workflow.state.state["tracks"] = updated_tracks
            if not self.workflow.state.save():
                self.workflow.state.state["tracks"] = previous_tracks
                QMessageBox.warning(self, "保存エラー", "手動紐づけを保存できませんでした。")
                return
            
            # UIを更新
            self.update_file_mapping()
            self._force_show_mapping = True
            self.mapping_widget.setVisible(True)
            
            QMessageBox.information(self, "完了", "ファイル紐づけを手動で更新しました。")
    
    def _sanitize_foldername(self, name: str) -> str:
        return sanitize_foldername(name)

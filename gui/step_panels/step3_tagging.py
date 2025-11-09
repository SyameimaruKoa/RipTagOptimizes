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
        
        # Step 3 開始時は常にフォルダ内の全ファイルをスキャンして紐づけを更新
        # (Demucs で作成された Inst ファイルを検出するため)
        self.update_file_mapping()
        
        # ユーザーが明示的に表示を開始した後は、完了が押されるまで消さない
        if self._force_show_mapping:
            self.mapping_widget.setVisible(True)
            self.complete_button.setEnabled(True)
        else:
            # 紐づけ結果があれば表示
            self.mapping_widget.setVisible(True)
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
        
        # Mp3tag を起動（FLAC はサブフォルダ _flac_src を対象）
        self.tool_runner = ExternalToolRunner(self)
        self.tool_runner.finished.connect(self.on_mp3tag_finished)
        self.tool_runner.error_occurred.connect(self.on_mp3tag_error)
        
        target_dir = self.album_folder
        if self.workflow.state:
            raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
            candidate = os.path.join(self.album_folder, raw_dirname)
            if os.path.isdir(candidate):
                target_dir = candidate

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

        # 現在のFLACファイルを取得（サブフォルダ _flac_src 優先）
        current_flac_files = []
        try:
            base_dir = self.album_folder
            if self.workflow.state:
                raw_dirname = self.workflow.state.get_path("rawFlacSrc") or "_flac_src"
                candidate = os.path.join(self.album_folder, raw_dirname)
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
        def norm_title(name: str) -> str:
            base = re.sub(r"\.[^.]+$", "", name)            # 拡張子除去
            base = re.sub(r"^(\d{1,3})\s*[-．\. ]?\s*", "", base)  # 先頭番号除去
            # インスト関連の括弧を除去
            base = re.sub(r"\s*\((?i:inst|off\s*vocal|instrumental)\)\s*", "", base)
            # 末尾に連続する任意の括弧表記を丸ごと除去（例: (StemRoller) 等）
            base = re.sub(r"\s*(\([^)]*\)\s*)+$", "", base)
            return base.strip().lower()

        by_title: dict[str, str] = {}
        by_title_inst: dict[str, str] = {}
        for f in current_flac_files:
            key = norm_title(f)
            prev = by_title.get(key)
            by_title[key] = prefer_inst(prev, f)
            # Inst専用マップ（番号が違っても拾えるように）
            if self._is_instrumental_by_name(f.lower()):
                # 既に登録があればそのまま（どちらでもInstなので優先不要）
                by_title_inst.setdefault(key, f)
        
        # トラック情報を更新
        tracks = self.workflow.state.get_tracks()

        for i, track in enumerate(tracks):
            original_file = track.get("originalFile", "")
            orig_norm = norm_title(original_file)
            # 先頭番号でマッチ
            m = re.match(r"^(\d{1,3})", original_file)
            new_file = None
            if m:
                try:
                    idx = int(m.group(1))
                    candidate = by_tracknum.get(idx)
                    # トラック番号だけが変わった場合に誤紐づけしないよう、タイトル正規化で一致確認
                    if candidate is not None:
                        cand_norm = norm_title(candidate)
                        if cand_norm == orig_norm or not orig_norm:
                            new_file = candidate
                        else:
                            # 番号マッチは不一致と見なし、タイトルで改めて探す
                            new_file = None
                except ValueError:
                    new_file = None
            # タイトル正規化でマッチ
            if not new_file:
                new_file = by_title.get(norm_title(original_file))

            # マッチしない場合は、従来の安全策: 同名が存在すればそれを使う
            if not new_file and original_file in current_flac_files:
                new_file = original_file

            # それでも無ければスキップ（ユーザーに後で表示）
            if not new_file:
                # シンプル行
                self._append_mapping_row(f"{original_file}  →  (未検出)")
                continue

            # 同タイトルのInstパートナーを探す（番号が異なっても検出）
            inst_partner = by_title_inst.get(orig_norm)

            # 通常ケース: new_file を最終成果物とし、Instが別にあれば派生として表示
            track["finalFile"] = new_file
            track["isInstrumental"] = self._is_instrumental_by_name(new_file.lower())
            if inst_partner and inst_partner != new_file:
                track["instrumentalFile"] = inst_partner
                track["hasInstrumental"] = True
                # 表示: 原曲(or最終) → 最終 | (+Inst生成: inst)
                self._append_mapping_row(
                    f"{original_file}  →  {new_file}",
                    f"(+Inst生成: {inst_partner})",
                    "このトラックからインストゥルメンタル版を派生生成しました"
                )
            else:
                # new_file 自体が Inst の場合はバッジ表示、それ以外は通常表示
                if track["isInstrumental"]:
                    self._append_mapping_row(
                        f"{original_file}  →  {new_file}",
                        "[Inst]",
                        "Instrumental（インストゥルメンタル）"
                    )
                else:
                    self._append_mapping_row(f"{original_file}  →  {new_file}")
        
        # state.json に保存
        self.workflow.state.state["tracks"] = tracks
        self.workflow.state.save()

    # ------------------------
    # internal helpers
    # ------------------------
    def _append_mapping_row(self, main_text: str, extra_text: str | None = None, extra_tooltip: str | None = None):
        """マッピング行をリッチ表示で追加する。
        - main_text: 左側の通常テキスト
        - extra_text: 右側に付ける強調テキスト（Inst 派生など）
        - extra_tooltip: 強調テキストのツールチップ
        """
        item = QListWidgetItem()
        row = QWidget()
        lay = QHBoxLayout()
        lay.setContentsMargins(4, 0, 4, 0)
        lay.setSpacing(6)
        lbl_main = QLabel(main_text)
        lay.addWidget(lbl_main)
        if extra_text:
            lbl_extra = QLabel(extra_text)
            # 強調: 金色 + 太字（他行への色漏れなし）
            lbl_extra.setStyleSheet("color: rgb(255, 215, 0); font-weight: 700;")
            if extra_tooltip:
                lbl_extra.setToolTip(extra_tooltip)
            lay.addWidget(lbl_extra)
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

    def on_rescan(self):
        """Mp3tagを使わずに紐づけを再構築"""
        self.update_file_mapping()
        self.check_artwork()
        self._force_show_mapping = True
        self.mapping_widget.setVisible(True)
        self.complete_button.setEnabled(True)
    
    def check_artwork(self):
        """アートワーク検査"""
        if not self.album_folder or not self.workflow.state:
            return

        has_artwork = check_album_has_artwork(self.album_folder)
        self.workflow.state.set_artwork(has_artwork)
        # OKポップは不要（検査結果は state のみ更新）
    
    def on_complete(self):
        """完了ボタン"""
        reply = QMessageBox.question(
            self,
            "確認",
            "Step 3 を完了しますか?\n\n"
            "ファイルの紐づけとアートワーク検査が完了しました。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 完了後は維持フラグを解除
            self._force_show_mapping = False
            self.step_completed.emit()

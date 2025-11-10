"""
Step 2: Demucs処理パネル
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QCheckBox
)
from PySide6.QtCore import Signal, Qt

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager
from logic.demucs_detector import detect_demucs_targets, extract_instrumental_files
from logic.external_tools import ExternalToolRunner


class Step2DemucsPanel(QWidget):
    """Step 2: Demucs処理パネル"""
    
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
        title = QLabel("<h2>Step 2: Demucs処理 (音源分離)</h2>")
        layout.addWidget(title)
        
        # 説明
        desc = QLabel(
            "ボーカル入りの曲からインストゥルメンタル版を作成します。\n"
            "処理対象の曲を選択し、外部でDemucsを実行してください。\n"
            "完了後、出力フォルダを指定すると自動的にFLACへ変換・移動します。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(10)
        
        # --- ▼ Colab誘導の追加 ▼ ---
        colab_info_label = QLabel(
            '<h3>🚀 Google Colabでの実行を推奨します</h3>'
            'ローカル（このPC）でのDemucs実行は、NVIDIA GPU搭載PCでのみ動作し、環境設定も必要です。<br><br>'
            '<b>スペックや設定に不安がある場合は、Colab（無料）の利用を強く推奨します:</b><br>'
            '1. <a href="https://colab.research.google.com/gist/SyameimaruKoa/8b9c42bd3ddccfe8512376e8a43a7633">ハイブリッド Demucs Colab を開く</a><br>'
            '2. Colab側で <code>RipTagOptimize_mode = True</code> に設定して実行する。<br>'
            '3. 処理後にZIPをダウンロードし、解凍したフォルダを <b>Step 1</b> で指定し直してください。',
            self
        )
        colab_info_label.setOpenExternalLinks(True)
        colab_info_label.setStyleSheet(
            "font-size: 11px; "
            "padding: 12px; "
            "margin-top: 5px; "
            "margin-bottom: 5px; "
            "background-color: #f0f9ff; "
            "border: 1px solid #bcecfd; "
            "border-left-width: 5px; "
            "border-left-color: #38bdf8; "
            "border-radius: 6px;"
        )
        layout.addWidget(colab_info_label)

        # --- (区切り線) ---
        local_run_label = QLabel("<b>または、ローカルで実行（上級者向け）:</b>", self)
        local_run_label.setStyleSheet("margin-top: 10px; font-size: 12px;")
        layout.addWidget(local_run_label)
        # --- ▲ Colab誘導の追加 ▲ ---

        # トラックリスト（チェックボックス式）
        list_label = QLabel("<b>処理対象の曲を選択 (チェック):</b>")
        layout.addWidget(list_label)

        self.track_list = QListWidget()
        # 選択ハイライトは使わない（チェックで管理）
        self.track_list.setSelectionMode(QListWidget.NoSelection)
        # チェック状態が変更されたら自動保存
        self.track_list.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.track_list)
        
        # 一括操作ボタン
        bulk_layout = QHBoxLayout()
        
        self.select_all_button = QPushButton("全選択")
        self.select_all_button.clicked.connect(self.on_select_all)
        bulk_layout.addWidget(self.select_all_button)
        
        self.deselect_all_button = QPushButton("全解除")
        self.deselect_all_button.clicked.connect(self.on_deselect_all)
        bulk_layout.addWidget(self.deselect_all_button)
        
        self.auto_detect_button = QPushButton("自動検出")
        self.auto_detect_button.clicked.connect(self.on_auto_detect)
        bulk_layout.addWidget(self.auto_detect_button)

        # 📁 フォルダを開く（ここに移動）
        self.open_folder_button = QPushButton("📁 フォルダを開く")
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.clicked.connect(self.on_open_folder)
        bulk_layout.addWidget(self.open_folder_button)

        bulk_layout.addStretch()

        layout.addLayout(bulk_layout)

        layout.addSpacing(10)

        # アクションボタン
        action_layout = QHBoxLayout()

        self.demucs_button = QPushButton("Demucs実行 (外部)")
        self.demucs_button.setEnabled(False)
        self.demucs_button.clicked.connect(self.on_demucs_execute)
        action_layout.addWidget(self.demucs_button)
        
        self.completed_button = QPushButton("Demucs完了")
        self.completed_button.setEnabled(False)
        self.completed_button.clicked.connect(self.on_demucs_completed)
        action_layout.addWidget(self.completed_button)
        
        self.skip_button = QPushButton("このステップをスキップ")
        self.skip_button.clicked.connect(self.on_skip)
        action_layout.addWidget(self.skip_button)
        
        action_layout.addStretch()
        
        layout.addLayout(action_layout)
        layout.addStretch()
    
    def load_album(self, album_folder: str):
        """アルバムを読み込み"""
        print("[DEBUG] Step2: load_album called")
        self.album_folder = album_folder

        # 既存アルバムで root 直下に .flac が残っている場合は _flac_src へ自動移行
        try:
            self._ensure_flac_src_migration()
        except Exception as e:
            print(f"[WARN] _flac_src への自動移行に失敗: {e}")
        
        # シグナルを一時的にブロック（load中の誤保存を防ぐ）
        self.track_list.blockSignals(True)
        self.track_list.clear()
        
        if not self.workflow.state:
            self.track_list.blockSignals(False)
            return
        
        # トラック情報を取得
        tracks = self.workflow.state.get_tracks()
        
        for track in tracks:
            original_file = track.get("originalFile", "")
            demucs_target = track.get("demucsTarget", True)
            
            item = QListWidgetItem(original_file)
            item.setData(Qt.UserRole, track.get("id"))
            # チェックボックス有効化
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked if demucs_target else Qt.Unchecked)
            
            print(f"[DEBUG] Load: {original_file} -> demucsTarget={demucs_target}")
            
            self.track_list.addItem(item)
        
        # シグナルを再有効化
        self.track_list.blockSignals(False)
        
        self.demucs_button.setEnabled(True)
        self.open_folder_button.setEnabled(True)
    
    def on_item_changed(self, item: QListWidgetItem):
        """チェック状態が変更されたときに state.json に保存"""
        if not self.workflow.state:
            return
        track_id = item.data(Qt.UserRole)
        checked = (item.checkState() == Qt.Checked)
        tracks = self.workflow.state.get_tracks()
        for t in tracks:
            if t.get("id") == track_id:
                t["demucsTarget"] = checked
                print(f"[DEBUG] Change: {t.get('originalFile')} -> demucsTarget={checked}")
                break
        self.workflow.state.state["tracks"] = tracks
        self.workflow.state.save()
    
    def on_select_all(self):
        """全選択"""
        self.track_list.blockSignals(True)
        for i in range(self.track_list.count()):
            self.track_list.item(i).setCheckState(Qt.Checked)
        self.track_list.blockSignals(False)
        # 保存
        self.on_bulk_save()
    
    def on_deselect_all(self):
        """全解除"""
        self.track_list.blockSignals(True)
        for i in range(self.track_list.count()):
            self.track_list.item(i).setCheckState(Qt.Unchecked)
        self.track_list.blockSignals(False)
        # 保存
        self.on_bulk_save()

    def on_bulk_save(self):
        """現在のチェック状態を一括保存"""
        if not self.workflow.state:
            return
        tracks = self.workflow.state.get_tracks()
        for i in range(self.track_list.count()):
            item = self.track_list.item(i)
            track_id = item.data(Qt.UserRole)
            for t in tracks:
                if t.get("id") == track_id:
                    t["demucsTarget"] = (item.checkState() == Qt.Checked)
                    break
        self.workflow.state.state["tracks"] = tracks
        self.workflow.state.save()
    
    def on_auto_detect(self):
        """自動検出"""
        if not self.workflow.state:
            return
        
        # キーワード取得
        keywords = self.config.get_demucs_keywords()
        
        # トラック名リスト取得
        tracks = self.workflow.state.get_tracks()
        track_names = [t.get("originalFile", "") for t in tracks]
        
        # 自動検出実行
        target_flags = detect_demucs_targets(track_names, keywords)
        
        # シグナルを一時的にブロック（自動検出中の誤保存を防ぐ）
        self.track_list.blockSignals(True)
        
        # UI に反映 & state.json に保存
        for i in range(self.track_list.count()):
            item = self.track_list.item(i)
            filename = item.text()
            should_select = target_flags.get(filename, True)
            item.setCheckState(Qt.Checked if should_select else Qt.Unchecked)
            
            # state.json にも反映
            track_id = item.data(Qt.UserRole)
            for track in tracks:
                if track.get("id") == track_id:
                    track["demucsTarget"] = should_select
                    break
        
        # 保存
        self.workflow.state.state["tracks"] = tracks
        self.workflow.state.save()
        
        # シグナルを再有効化
        self.track_list.blockSignals(False)
        
        QMessageBox.information(
            self,
            "自動検出完了",
            f"インストゥルメンタル曲とそのペア原曲を自動検出しました。\n"
            f"検出されたキーワード数: {len(keywords)}"
        )
    
    def on_demucs_execute(self):
        """Demucs実行ボタン"""
        # チェックされた項目を集計
        checked_names = []
        for i in range(self.track_list.count()):
            item = self.track_list.item(i)
            if item.checkState() == Qt.Checked:
                checked_names.append(item.text())

        if not checked_names:
            QMessageBox.warning(self, "警告", "処理対象の曲が選択されていません。")
            return
        
        msg = QMessageBox.information(
            self,
            "Demucs実行",
            f"以下の {len(checked_names)} 曲を外部でDemucs処理してください:\n\n"
            + "\n".join(checked_names) + "\n\n"
            "完了したら「Demucs完了」ボタンを押してください。",
            QMessageBox.Ok
        )
        
        # 完了ボタンを有効化
        self.completed_button.setEnabled(True)
    
    def on_demucs_completed(self):
        """Demucs完了ボタン"""
        # Demucs出力フォルダを選択
        folder = QFileDialog.getExistingDirectory(
            self,
            "Demucs出力フォルダを選択",
            self.album_folder if self.album_folder else ""
        )
        
        if not folder:
            return

        # インストファイルを抽出
        inst_files = extract_instrumental_files(folder)

        if not inst_files:
            QMessageBox.warning(
                self,
                "エラー",
                "指定されたフォルダ内に no_vocals.wav または minus_vocals.flac が見つかりませんでした。"
            )
            return

        # FLAC変換・移動処理
        success_count = 0
        flac_path = self.config.get_tool_path("Flac")

        if not flac_path:
            QMessageBox.warning(
                self,
                "警告",
                "flac.exe が見つかりません。\n"
                "config.ini でパスを設定してください。"
            )
            return
        
        for song_folder, inst_file in inst_files:
            # 元のファイル名を推定
            song_name = os.path.basename(song_folder)
            
            # 出力FLACファイル名
            if not self.album_folder:
                print("[ERROR] album_folder が未設定のため処理を中断")
                break
            # 出力先は root ではなく _flac_src を優先
            flac_src_dir = self._get_flac_src_dir()
            os.makedirs(flac_src_dir, exist_ok=True)
            output_flac = os.path.join(flac_src_dir, f"{song_name} (Inst).flac")
            
            # WAVの場合はFLACに変換
            if inst_file.lower().endswith('.wav'):
                # flac -8 input.wav -o output.flac
                runner = ExternalToolRunner()
                success, stdout, stderr = runner.run_cli_tool(
                    flac_path,
                    ["-8", inst_file, "-o", output_flac],
                    self.album_folder
                )
                
                if not success:
                    print(f"[ERROR] FLAC変換失敗: {stderr}")
                    continue
            else:
                # 既にFLACの場合は移動（重複時は上書き）
                import shutil
                try:
                    if os.path.exists(output_flac):
                        os.remove(output_flac)
                    shutil.move(inst_file, output_flac)
                except Exception as e:
                    print(f"[ERROR] ファイル移動失敗: {e}")
                    continue
            
            # 元のトラックのタグをコピーし、ジャンルのみ "Instrumental" に変更
            try:
                from mutagen.flac import FLAC
                orig_path = self._find_original_for_song(song_name)
                dest = FLAC(output_flac)
                if orig_path and os.path.exists(orig_path):
                    src = FLAC(orig_path)
                    # 既存タグをクリアしてコピー
                    dest.delete()
                    for k, v in src.tags.items():
                        dest[k] = v
                    # 画像もコピー
                    dest.clear_pictures()
                    for pic in src.pictures:
                        dest.add_picture(pic)
                # ジャンルだけ上書き
                dest["genre"] = ["Instrumental"]
                dest.save()
                success_count += 1
            except Exception as e:
                print(f"[ERROR] タグコピー失敗: {e}")
        
        if success_count > 0:
            # state.json を更新（インストトラックを追加）
            # TODO: トラック情報に追加
            
            # サイレント化（ログとして一覧に表示する方針ならここで別UI要素に追加予定）
            self.step_completed.emit()
        else:
            QMessageBox.warning(self, "エラー", "インストゥルメンタル版の作成に失敗しました。")
    
    def on_skip(self):
        """スキップボタン"""
        reply = QMessageBox.question(
            self,
            "確認",
            "Step 2 (Demucs処理) をスキップしますか?\n\n"
            "スキップした場合、インストゥルメンタル版は作成されません。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # フラグを設定
            if self.workflow.state:
                self.workflow.state.set_flag("step2_skipped", True)
            
            self.step_completed.emit()

    def on_open_folder(self):
        """エクスプローラーでアルバムフォルダを開く"""
        if not self.album_folder or not os.path.exists(self.album_folder):
            QMessageBox.warning(self, "エラー", "アルバムフォルダが見つかりません。")
            return

        # Windowsのエクスプローラーでフォルダを開く
        os.startfile(self.album_folder)

    # ==========================================================
    # 内部ヘルパー
    # ==========================================================
    def _find_original_for_song(self, song_name: str) -> str | None:
        """Demucsサブフォルダ名から対応する原曲FLACファイルを推定しパスを返す。
        - トラック番号/拡張子/インストキーワードを除去して正規化し比較
        """
        if not self.workflow.state or not self.album_folder:
            return None

        import re, os
        keywords = self.config.get_demucs_keywords() or []
        # 正規化関数
        def norm(s: str) -> str:
            base = re.sub(r'\.[^.]+$', '', s)
            base = re.sub(r'^\d+[\s\-\.]*', '', base)
            # キーワード除去
            for kw in keywords:
                base = re.sub(fr'(?i)\s*[\(\[\-]?{re.escape(kw)}[\)\]\-]?','', base)
            return base.strip().lower()

        target_norm = norm(song_name)
        if not target_norm:
            return None

        for track in self.workflow.state.get_tracks():
            orig = track.get("originalFile")
            if not orig:
                continue
            if norm(orig) == target_norm:
                # _flac_src を優先的に探索
                flac_src_dir = self._get_flac_src_dir()
                candidate1 = os.path.join(flac_src_dir, orig)
                candidate2 = os.path.join(self.album_folder, orig)
                if os.path.exists(candidate1):
                    return candidate1
                if os.path.exists(candidate2):
                    return candidate2
        return None

    def _get_flac_src_dir(self) -> str:
        """FLAC のソース置き場 (_flac_src) の実パスを返す。state の設定があればそれを使う。"""
        raw_dirname = None
        try:
            if self.workflow and self.workflow.state:
                raw_dirname = self.workflow.state.get_path("rawFlacSrc")
        except Exception:
            raw_dirname = None
        raw_dirname = raw_dirname or "_flac_src"
        return os.path.join(self.album_folder or "", raw_dirname)

    def _ensure_flac_src_migration(self):
        """アルバム直下にある .flac を _flac_src へ移動する。
        - 既に _flac_src にあるものは無視
        - サブフォルダは走査しない（トップレベルのみ）
        """
        if not self.album_folder:
            return
        flac_src_dir = self._get_flac_src_dir()
        os.makedirs(flac_src_dir, exist_ok=True)
        moved = 0
        for name in os.listdir(self.album_folder):
            src_path = os.path.join(self.album_folder, name)
            if not os.path.isfile(src_path):
                continue
            if name.lower().endswith('.flac'):
                dst_path = os.path.join(flac_src_dir, name)
                # 既に同名がある場合はスキップ（上書きしない）
                if os.path.abspath(src_path) == os.path.abspath(dst_path):
                    continue
                try:
                    import shutil
                    shutil.move(src_path, dst_path)
                    moved += 1
                    print(f"[INFO] Moved FLAC to _flac_src: {name}")
                except Exception as e:
                    print(f"[WARN] 移動失敗: {name}: {e}")
        if moved:
            print(f"[INFO] root 直下の FLAC {moved} 件を _flac_src へ移動しました")

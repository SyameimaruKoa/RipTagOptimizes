"""
Step 1: 新規取り込みパネル
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QMessageBox, QProgressDialog
)
from PySide6.QtCore import Signal, QThread

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager
from logic.state_manager import StateManager
from logic.log_manager import get_logger
import shutil
from send2trash import send2trash


class ImportWorker(QThread):
    """取り込み処理を別スレッドで実行（コピー→削除の2段階処理で安全性確保）"""
    finished = Signal(bool, str)  # success, message

    def __init__(self, source: str, dest_folder: str):
        super().__init__()
        self.source = source
        self.dest_folder = dest_folder

    def run(self):
        try:
            # 親ディレクトリを確実に作成
            os.makedirs(os.path.dirname(self.dest_folder), exist_ok=True)
            
            # 既に存在する場合はエラー
            if os.path.exists(self.dest_folder):
                self.finished.emit(False, f"コピー先が既に存在します")
                return
            
            # 安全性のため2段階処理: コピー → 元を削除
            # 1. まずコピー
            shutil.copytree(self.source, self.dest_folder, dirs_exist_ok=False)
            
            # 2. コピー成功後のみ元フォルダを削除
            try:
                # 存在確認
                if not os.path.exists(self.source):
                    self.finished.emit(False, f"元フォルダが見つかりません (既に移動済み？)")
                    return
                
                # send2trashがProcessLookupErrorを起こす場合があるので、
                # 失敗時はshutil.rmtreeで直接削除
                try:
                    send2trash(self.source)
                except (ProcessLookupError, OSError):
                    # send2trash失敗時は直接削除（安全性は既にコピー完了しているので問題なし）
                    shutil.rmtree(self.source)
            except Exception as del_err:
                # 削除失敗 = 失敗扱い（コピーは成功しているので残骸削除が必要）
                error_type = type(del_err).__name__
                self.finished.emit(False, f"元フォルダ削除失敗: {error_type}")
                return
            
            self.finished.emit(True, "")
        except Exception as e:
            # コピー失敗時は元フォルダは残る（安全）
            error_type = type(e).__name__
            self.finished.emit(False, f"コピー失敗: {error_type}")


class Step1ImportPanel(QWidget):
    """Step 1: 新規取り込みパネル"""
    
    import_completed = Signal(str)  # album_folder
    
    def __init__(self, config: ConfigManager, workflow: WorkflowManager):
        super().__init__()
        self.config = config
        self.workflow = workflow
        self.init_ui()
    
    def init_ui(self):
        """UIを初期化"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # タイトル
        title = QLabel("<h2>Step 1: 新規取り込み</h2>")
        layout.addWidget(title)
        
        # 説明
        desc = QLabel(
            "Music Center からアルバムフォルダを選択し、作業フォルダに移動します。\n"
            "移動後、自動的に state.json が作成され、ワークフローが開始されます。\n\n"
            "使い方:\n"
            "• Ctrl+クリック で複数フォルダを同時選択\n"
            "• 親フォルダ選択 で配下の全アルバムを自動検出\n"
            "• 繰り返しボタンを押して追加選択も可能"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        # 選択されたフォルダ表示
        self.selected_folder_label = QLabel("選択: (なし)")
        self.selected_folder_label.setWordWrap(True)
        layout.addWidget(self.selected_folder_label)
        
        layout.addSpacing(10)
        
        # ボタン
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("📁 アルバムを選択（複数可）")
        self.select_button.clicked.connect(self.on_select_folders)
        button_layout.addWidget(self.select_button)
        
        self.import_button = QPushButton("✓ 取り込み開始")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.on_import_all)
        button_layout.addWidget(self.import_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Colab誘導ヒントは不要となったため削除（ここにあった案内ブロックを除去）
        
        layout.addStretch()
        
        # 選択されたフォルダのリスト
        self.selected_sources = []
    
    def load_album(self, album_folder: str):
        """アルバムを読み込み（このパネルでは何もしない）"""
        # Step1は新規取り込み用なので、既存アルバムを読み込む必要はない
        pass
    
    def reset(self):
        """パネルの状態をリセット（新規取り込み開始時）"""
        self.selected_sources = []
        self.selected_folder_label.setText("選択: (なし)")
        self.import_button.setEnabled(False)
    
    def on_select_folders(self):
        """複数フォルダ選択ボタンが押されたときの処理"""
        music_center_dir = self.config.get_directory("MusicCenterDir")
        
        # 非ネイティブダイアログで複数選択を可能に
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setWindowTitle("取り込むフォルダを選択（Ctrl+クリックで複数選択可）")
        
        if music_center_dir:
            dialog.setDirectory(music_center_dir)
        
        # サイドバーに便利なパスを追加
        from PySide6.QtCore import QUrl, QStandardPaths
        sidebar_urls = [
            QUrl.fromLocalFile(QStandardPaths.writableLocation(QStandardPaths.HomeLocation)),
            QUrl.fromLocalFile(QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)),
            QUrl.fromLocalFile(QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)),
            QUrl.fromLocalFile(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)),
            QUrl.fromLocalFile(QStandardPaths.writableLocation(QStandardPaths.MusicLocation)),
        ]
        
        # Music Center フォルダもサイドバーに追加
        if music_center_dir and os.path.exists(music_center_dir):
            sidebar_urls.insert(0, QUrl.fromLocalFile(music_center_dir))
        
        dialog.setSidebarUrls(sidebar_urls)
        
        # ツリービューとリストビューの両方で複数選択を有効化
        from PySide6.QtWidgets import QTreeView, QListView, QAbstractItemView
        
        tree_view = dialog.findChild(QTreeView)
        if tree_view:
            tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        list_view = dialog.findChild(QListView, "listView")
        if list_view:
            list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        if not dialog.exec():
            return
        
        selected_folders = dialog.selectedFiles()
        if not selected_folders:
            return
        
        # 選択された各フォルダからアルバムを検出
        album_folders = []
        for folder in selected_folders:
            detected = self._detect_album_folders(folder)
            album_folders.extend(detected)
        
        if not album_folders:
            QMessageBox.warning(
                self,
                "エラー",
                f"選択されたフォルダ内にアルバムが見つかりませんでした。\n\n"
                "アルバムフォルダの条件:\n"
                "• .flac ファイルが含まれている\n"
                "• または、サブフォルダに .flac ファイルが含まれている"
            )
            return
        
        # 重複チェックして追加
        new_count = 0
        for af in album_folders:
            if af not in self.selected_sources:
                self.selected_sources.append(af)
                new_count += 1
        
        # 表示更新
        count = len(self.selected_sources)
        folder_names = [os.path.basename(f) for f in self.selected_sources]
        display_text = f"選択: {count}個のアルバム\n" + "\n".join(f"  • {name}" for name in folder_names[:10])
        if count > 10:
            display_text += f"\n  ... 他 {count - 10}個"
        self.selected_folder_label.setText(display_text)
        self.import_button.setEnabled(True)
        
        # 結果表示
        if new_count > 0:
            if new_count == 1:
                msg = f"1個のアルバムを追加しました。\n\n合計: {count}個"
            else:
                msg = f"{new_count}個のアルバムを追加しました。\n\n合計: {count}個"
            
            reply = QMessageBox.question(
                self,
                "追加完了",
                msg + "\n\nさらにフォルダを追加しますか?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.on_select_folders()
        else:
            QMessageBox.information(
                self,
                "スキップ",
                f"選択されたアルバムは既に追加済みです。"
            )
    
    def _detect_album_folders(self, folder: str) -> list:
        """
        選択されたフォルダからアルバムフォルダを検出
        - 直接.flacがある → そのフォルダ
        - サブフォルダに.flacがある → 各サブフォルダ
        """
        album_folders = []
        
        # 直接.flacファイルがあるかチェック
        has_flac = False
        try:
            for item in os.listdir(folder):
                if item.lower().endswith('.flac'):
                    has_flac = True
                    break
        except:
            return []
        
        if has_flac:
            # このフォルダ自体がアルバムフォルダ
            album_folders.append(folder)
        else:
            # サブフォルダを探索（1階層のみ）
            try:
                for item in os.listdir(folder):
                    subfolder = os.path.join(folder, item)
                    if not os.path.isdir(subfolder):
                        continue
                    
                    # サブフォルダ内に.flacがあるかチェック
                    has_sub_flac = False
                    try:
                        for subitem in os.listdir(subfolder):
                            if subitem.lower().endswith('.flac'):
                                has_sub_flac = True
                                break
                    except:
                        continue
                    
                    if has_sub_flac:
                        album_folders.append(subfolder)
            except:
                pass
        
        return album_folders
    
    def on_import_all(self):
        """複数アルバムを順次取り込み"""
        if not self.selected_sources:
            return
        
        # 作業フォルダのパス
        work_dir = self.config.get_directory("WorkDir")
        if not work_dir:
            QMessageBox.warning(self, "エラー", "WorkDir が設定されていません。")
            return
        
        # work フォルダが存在しない場合は作成
        if not os.path.exists(work_dir):
            try:
                os.makedirs(work_dir)
            except Exception as e:
                QMessageBox.critical(self, "エラー", f"作業フォルダの作成に失敗しました:\n{e}")
                return
        
        # 確認ダイアログ
        album_count = len(self.selected_sources)
        reply = QMessageBox.question(
            self,
            "確認",
            f"{album_count}個のアルバムを取り込みますか?\n\n"
            f"既存のフォルダと名前が重複する場合は、\n"
            f"自動的にゴミ箱に移動されます。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # プログレスダイアログ
        self.progress = QProgressDialog("取り込み中...", "キャンセル", 0, album_count, self)
        self.progress.setWindowTitle("複数アルバム取り込み")
        self.progress.setModal(True)
        self.progress.setCancelButton(None)
        self.progress.show()
        
        # 取り込み処理を開始
        self.current_import_index = 0
        self.failed_imports = []
        self.work_dir = work_dir
        self._import_next_album()
    
    def _import_next_album(self):
        """次のアルバムを取り込み"""
        if self.current_import_index >= len(self.selected_sources):
            # 全て完了
            self._on_all_imports_completed()
            return
        
        source_folder = self.selected_sources[self.current_import_index]
        
        # source_folderが存在しない場合はスキップ
        if not os.path.exists(source_folder):
            self.failed_imports.append((os.path.basename(source_folder), "フォルダが見つかりません"))
            self.current_import_index += 1
            self._import_next_album()
            return
        
        album_name = os.path.basename(source_folder).strip()
        parent_dir = os.path.dirname(source_folder)
        artist_name = os.path.basename(parent_dir).strip() if parent_dir else "Unknown"
        
        # プログレス更新
        self.progress.setLabelText(f"取り込み中: {album_name} ({self.current_import_index + 1}/{len(self.selected_sources)})")
        self.progress.setValue(self.current_import_index)
        
        dest_folder = os.path.join(self.work_dir, album_name)
        
        # 競合チェック（自動削除）
        if os.path.exists(dest_folder):
            try:
                send2trash(dest_folder)
            except Exception as e:
                self.failed_imports.append((album_name, f"既存フォルダ削除失敗: {e}"))
                self.current_import_index += 1
                self._import_next_album()
                return
        
        # ワーカースレッドで実行
        self.import_worker = ImportWorker(source_folder, dest_folder)
        self.import_worker.finished.connect(
            lambda success, msg: self._on_single_import_finished(success, msg, dest_folder, album_name, artist_name)
        )
        self.import_worker.start()
    
    def _on_single_import_finished(self, success, error_msg, dest_folder, album_name, artist_name):
        """単一アルバム取り込み完了"""
        # ロガーを取得（アルバムフォルダ設定）
        logger = get_logger()
        if os.path.exists(dest_folder):
            logger.set_album_folder(dest_folder)
        
        if not success:
            self.failed_imports.append((album_name, error_msg))
            logger.error("step1", f"取り込み失敗: {album_name} - {error_msg}")
            # 失敗した残骸を削除
            if os.path.exists(dest_folder):
                try:
                    shutil.rmtree(dest_folder)
                except Exception as cleanup_err:
                    logger.warning("step1", f"失敗した残骸の削除失敗: {cleanup_err}")
            self.current_import_index += 1
            self._import_next_album()
            return
        
        # state.json を初期化
        if not self._initialize_album_state(dest_folder, album_name, artist_name):
            self.failed_imports.append((album_name, "state.json初期化失敗"))
            logger.error("step1", f"state.json初期化失敗: {album_name}")
            # 初期化失敗時も残骸を削除
            if os.path.exists(dest_folder):
                try:
                    shutil.rmtree(dest_folder)
                except Exception as cleanup_err:
                    logger.warning("step1", f"初期化失敗後の残骸削除失敗: {cleanup_err}")
        else:
            logger.info("step1", f"アルバム取り込み完了: {album_name} (アーティスト: {artist_name})")
        
        # 次へ
        self.current_import_index += 1
        self._import_next_album()
    
    def _initialize_album_state(self, dest_folder, album_name, artist_name):
        """アルバムのstate.jsonを初期化"""
        # ファイル名をサニタイズ
        sanitized_album_name = self._sanitize_foldername(album_name)
        
        # _flac_src/アルバム名 に FLAC を隔離
        flac_src_dir = os.path.join(dest_folder, "_flac_src", sanitized_album_name)
        try:
            os.makedirs(flac_src_dir, exist_ok=True)
        except:
            return False

        moved_count = 0
        try:
            for file in list(os.listdir(dest_folder)):
                if file.lower().endswith('.flac'):
                    src = os.path.join(dest_folder, file)
                    dst = os.path.join(flac_src_dir, file)
                    try:
                        os.replace(src, dst)
                        moved_count += 1
                    except Exception as e:
                        print(f"[WARN] FLAC移動失敗: {file}: {e}")
        except:
            return False

        # _flac_src/アルバム名 内の .flac を列挙
        flac_files = []
        try:
            for file in os.listdir(flac_src_dir):
                if file.lower().endswith('.flac'):
                    flac_files.append(file)
            flac_files.sort()
        except:
            return False
        
        if not flac_files:
            return False
        
        # StateManager で初期化
        state = StateManager(dest_folder)
        if not state.initialize(album_name, artist_name, flac_files):
            return False
            
        # 初期状態に自動検出（Off Vocalや指定キーワードの除外）を適用する
        try:
            from logic.demucs_detector import detect_demucs_targets
            keywords = self.config.get_demucs_keywords()
            targets = detect_demucs_targets(flac_files, keywords)
            
            tracks = state.get_tracks()
            updated = False
            for track in tracks:
                fname = track.get("originalFile")
                if fname in targets and not targets[fname]:
                    track["demucsTarget"] = False
                    updated = True
            
            if updated:
                state.state["tracks"] = tracks
                state.save()
        except Exception as e:
            print(f"[WARN] 初期化時の自動検出に失敗しました: {e}")
        
        # Step1完了 → Step2へ自動進行
        # まずworkflowにアルバムをロード
        if self.workflow.load_album(dest_folder):
            # ステップを進める
            if self.workflow.advance_step():
                print(f"[INFO] Album '{album_name}' advanced to Step 2")
            else:
                print(f"[WARN] Failed to advance step for '{album_name}'")
        else:
            print(f"[WARN] Failed to load album for step advancement: '{album_name}'")
        
        return True
    
    def _on_all_imports_completed(self):
        """全アルバムの取り込み完了"""
        self.progress.close()
        
        success_count = len(self.selected_sources) - len(self.failed_imports)
        
        if self.failed_imports:
            error_list = "\n".join([f"• {name}: {msg}" for name, msg in self.failed_imports])
            QMessageBox.warning(
                self,
                "取り込み完了（一部失敗）",
                f"成功: {success_count}個\n失敗: {len(self.failed_imports)}個\n\n"
                f"失敗したアルバム:\n{error_list}"
            )
        else:
            QMessageBox.information(
                self,
                "取り込み完了",
                f"{success_count}個のアルバムを取り込みました!"
            )
        
        # リセット
        self.selected_sources = []
        self.selected_folder_label.setText("選択: (なし)")
        self.import_button.setEnabled(False)
        
        # 最初のアルバムの完了シグナルを発火（リスト更新のため）
        if success_count > 0:
            self.import_completed.emit("")  # 空文字列で全体更新を促す
    
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

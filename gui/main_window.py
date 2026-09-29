"""
メインウィンドウ

⚠️ このアプリケーションは個人的な使用を目的として開発されました。
   使用は自己責任でお願いします。
"""
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QStackedWidget, QToolBar, QPushButton,
    QStatusBar, QMessageBox, QLabel, QListWidgetItem
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from send2trash import send2trash

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager
from logic.state_manager import StateManager

# ステップパネルのインポート(後で実装)
from gui.step_panels.step0_music_center import Step0MusicCenterPanel
from gui.step_panels.step1_import import Step1ImportPanel
from gui.step_panels.step2_demucs import Step2DemucsPanel
from gui.step_panels.step3_tagging import Step3TaggingPanel
from gui.step_panels.step_generic import GenericStepPanel
from gui.step_panels.step4_aac import Step4AacPanel
from gui.step_panels.step5_opus import Step5OpusPanel
from gui.step_panels.step6_artwork import Step6ArtworkPanel
from gui.step_panels.step7_transfer import Step7TransferPanel


class AlbumListWidget(QListWidget):
    """空白クリックやEscキー押下で選択解除できるQListWidget"""
    
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if not item:
            self.clearSelection()
            self.setCurrentItem(None)
        super().mousePressEvent(event)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.clearSelection()
            self.setCurrentItem(None)
        super().keyPressEvent(event)


class MainWindow(QMainWindow):
    """メインウィンドウクラス"""
    
    def __init__(self):
        super().__init__()
        
        self.config = ConfigManager()
        self.workflow = WorkflowManager(self.config)
        self.current_album_folder = None
        
        self.init_ui()
        self.refresh_album_list()
        
        # 定期的にアルバムリストを更新（5秒ごと）
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_album_list)
        self.refresh_timer.start(5000)
    
    def init_ui(self):
        """UIを初期化"""
        self.setWindowTitle("CD取り込み自動化ワークフロー・マスターGUI")
        self.setGeometry(100, 100, 1200, 800)
        
        # メインウィジェット
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # レイアウト
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        
        # 左ペイン: アルバムリスト
        self.album_list = AlbumListWidget()
        self.album_list.setMaximumWidth(350)
        self.album_list.currentItemChanged.connect(self.on_album_selected)
        main_layout.addWidget(self.album_list)
        
        # 右ペイン: 作業エリア
        self.step_stack = QStackedWidget()
        main_layout.addWidget(self.step_stack)
        
        # ステップパネルを初期化
        self.init_step_panels()
        
        # 初期画面を新規取り込み（Step 1）に設定
        self.step_stack.setCurrentIndex(1)
        
        # ツールバー
        self.init_toolbar()
        
        # ステータスバー
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("新規取り込みを開始してください")
    
    def init_toolbar(self):
        """ツールバーを初期化"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Music Center取り込みガイド
        music_center_action = QAction("Music Center取り込み", self)
        music_center_action.triggered.connect(self.on_show_music_center_guide)
        toolbar.addAction(music_center_action)
        
        # 新規取り込みボタン
        new_import_action = QAction("新規取り込み", self)
        new_import_action.triggered.connect(self.on_new_import)
        toolbar.addAction(new_import_action)
        
        toolbar.addSeparator()
        
        # 再スキャンボタン
        refresh_action = QAction("再スキャン", self)
        refresh_action.triggered.connect(self.refresh_album_list)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        # 一括処理ボタン（v1.0では無効化）
        # batch_action = QAction("🔄 一括処理", self)
        # batch_action.setToolTip("Step4~7を全アルバム一括処理します")
        # batch_action.triggered.connect(self.on_batch_process)
        # toolbar.addAction(batch_action)
        
        toolbar.addSeparator()
        
        # ロールバックボタン
        rollback_action = QAction("⏪ 前ステップへ", self)
        rollback_action.setToolTip("選択中のアルバムを前のステップに戻します")
        rollback_action.triggered.connect(self.on_rollback_step)
        toolbar.addAction(rollback_action)

        # 作業破棄（ゴミ箱へ移動）
        discard_action = QAction("作業破棄", self)
        discard_action.setToolTip("選択中のアルバム作業フォルダをゴミ箱へ移動します")
        discard_action.triggered.connect(self.on_discard_album)
        toolbar.addAction(discard_action)
        
        toolbar.addSeparator()
        
        # 設定ボタン
        settings_action = QAction("設定", self)
        settings_action.triggered.connect(self.on_settings)
        toolbar.addAction(settings_action)
        
        # ログビューアーボタン
        log_viewer_action = QAction("📋 ログ", self)
        log_viewer_action.setToolTip("ログファイルを表示します")
        log_viewer_action.triggered.connect(self.on_show_log_viewer)
        toolbar.addAction(log_viewer_action)
    
    def init_step_panels(self):
        """各ステップのパネルを初期化"""
        # Step 0: Music Center取り込みガイド
        self.step0_panel = Step0MusicCenterPanel(self.config, self.workflow)
        self.step_stack.addWidget(self.step0_panel)
        
        # Step 1: 新規取り込み
        self.step1_panel = Step1ImportPanel(self.config, self.workflow)
        self.step1_panel.import_completed.connect(self.on_import_completed)
        self.step_stack.addWidget(self.step1_panel)
        
        # Step 2: Demucs処理
        self.step2_panel = Step2DemucsPanel(self.config, self.workflow)
        self.step2_panel.step_completed.connect(self.on_step_completed)
        self.step_stack.addWidget(self.step2_panel)
        
        # Step 3: Mp3Tag (FLAC完成)
        self.step3_panel = Step3TaggingPanel(self.config, self.workflow)
        self.step3_panel.step_completed.connect(self.on_step_completed)
        self.step_stack.addWidget(self.step3_panel)
        
        # Step 4: AAC 変換（専用パネル）
        self.step4_panel = Step4AacPanel(self.config, self.workflow)
        self.step4_panel.step_completed.connect(self.on_step_completed)
        self.step_stack.addWidget(self.step4_panel)

        # Step 5: Opus変換（専用パネル）
        self.step5_opus_panel = Step5OpusPanel(self.config, self.workflow)
        self.step5_opus_panel.step_completed.connect(self.on_step_completed)
        self.step_stack.addWidget(self.step5_opus_panel)

        # Step 6: アートワーク最適化
        self.step6_artwork_panel = Step6ArtworkPanel(self.config, self.workflow)
        self.step6_artwork_panel.step_completed.connect(self.on_step_completed)
        self.step_stack.addWidget(self.step6_artwork_panel)

        # Step 7: 最終転送
        self.step7_transfer_panel = Step7TransferPanel(self.config, self.workflow)
        self.step7_transfer_panel.step_completed.connect(self.on_step_completed)
        self.step_stack.addWidget(self.step7_transfer_panel)
    
    def refresh_album_list(self):
        """アルバムリストを更新"""
        work_dir = self.config.get_directory("WorkDir")
        
        if not work_dir or not os.path.exists(work_dir):
            return
        
        # 現在の選択を保存
        current_selection = None
        if self.album_list.currentItem():
            current_selection = self.album_list.currentItem().data(Qt.UserRole)
        
        # 自動リフレッシュ時のチラつき/選択変更イベント抑止
        self.album_list.blockSignals(True)
        self.album_list.clear()
        
        # work フォルダ内のサブフォルダをスキャン
        try:
            for item in os.listdir(work_dir):
                item_path = os.path.join(work_dir, item)
                if not os.path.isdir(item_path):
                    continue
                
                # state.json があるフォルダのみ表示
                state_path = os.path.join(item_path, "state.json")
                if not os.path.exists(state_path):
                    continue
                
                # state.json を読み込んで表示名を生成
                state = StateManager(item_path)
                if state.load():
                    # WorkflowManager を一時的に作成して表示名を取得
                    temp_workflow = WorkflowManager(self.config)
                    temp_workflow.load_album(item_path)
                    display_name = temp_workflow.get_album_display_name()
                    
                    list_item = QListWidgetItem(display_name)
                    list_item.setData(Qt.UserRole, item_path)
                    self.album_list.addItem(list_item)
                    
                    # 以前の選択を復元
                    if item_path == current_selection:
                        self.album_list.setCurrentItem(list_item)
        
        except Exception as e:
            print(f"[ERROR] アルバムリストの更新に失敗: {e}")
        finally:
            self.album_list.blockSignals(False)
            
        # 以前選択していたアルバムがリストから消えた場合の処理
        if current_selection and not self.album_list.currentItem():
            self.current_album_folder = None
            if self.step_stack.currentIndex() not in (0, 1):
                self.step_stack.setCurrentIndex(1)
                self.status_bar.showMessage("新規取り込みを開始してください")
    
    def on_album_selected(self, current, previous):
        """アルバムが選択されたときの処理"""
        print("[DEBUG] on_album_selected called")
        if not current:
            print("[DEBUG] current is None - switching to step1")
            self.current_album_folder = None
            self.step_stack.setCurrentIndex(1)
            self.status_bar.showMessage("新規取り込みを開始してください")
            return
        
        album_folder = current.data(Qt.UserRole)
        print(f"[DEBUG] album_folder: {album_folder}")
        if not album_folder:
            print("[DEBUG] album_folder is None")
            return
        
        # 絶対パスに変換（相対パスの場合）
        album_folder = os.path.abspath(album_folder)
        
        # 同一アルバムの自動リフレッシュによる再選択は無視して選択状態を保持
        if self.current_album_folder == album_folder and self.workflow and self.workflow.state:
            print("[DEBUG] Same album re-selected on refresh; skipping reload")
            return
        
        # アルバムを読み込み
        self.current_album_folder = album_folder
        print(f"[DEBUG] Loading album: {album_folder}")
        if self.workflow.load_album(album_folder):
            # 現在のステップに応じたパネルを表示
            step = self.workflow.get_current_step()
            print(f"[DEBUG] Current step: {step}")
            # Step0はガイドパネル(index 0)、Step1以降は index = step
            self.step_stack.setCurrentIndex(step)  # Step1 = index 1, Step2 = index 2...
            
            # パネルを更新
            current_panel = self.step_stack.currentWidget()
            print(f"[DEBUG] Current panel: {current_panel}")
            if hasattr(current_panel, 'load_album'):
                print(f"[DEBUG] Calling load_album on panel")
                current_panel.load_album(album_folder)
            
            # ステータスバーを更新
            step_name = self.workflow.get_current_step_name()
            album_name = self.workflow.state.get_album_name()
            self.status_bar.showMessage(f"{album_name} - {step_name}")
            print(f"[DEBUG] Updated status bar: {album_name} - {step_name}")
        else:
            print("[DEBUG] Failed to load album")
    
    def on_show_music_center_guide(self):
        """Music Center取り込みガイドを表示"""
        self.album_list.blockSignals(True)
        self.album_list.clearSelection()
        self.album_list.setCurrentItem(None)
        self.album_list.blockSignals(False)
        self.step_stack.setCurrentWidget(self.step0_panel)
        self.current_album_folder = None
        self.status_bar.showMessage("Music Center でCDを取り込む")
    
    def on_new_import(self):
        """新規取り込みボタンが押されたときの処理"""
        self.album_list.blockSignals(True)
        self.album_list.clearSelection()
        self.album_list.setCurrentItem(None)
        self.album_list.blockSignals(False)
        self.current_album_folder = None
        # Step1パネルをリセットして表示
        self.step1_panel.reset()
        self.step_stack.setCurrentIndex(1)  # Step1 = index 1 (Step0がindex 0)
        self.status_bar.showMessage("新規取り込みを開始してください")
    
    def on_import_completed(self, album_folder: str):
        """取り込み完了時の処理"""
        # Step1完了後に稀にステップ遷移しない問題への対策: 明示的リロード＋バリデーション後 advance
        if not self.workflow.load_album(album_folder):
            print("[WARN] on_import_completed: workflow.load_album failed")
            return

        # Step1 は常に進行可能なので安全に advance できるはず
        can, msg = self.workflow.can_advance_to_next_step()
        if not can:
            print(f"[WARN] Step1 advance blocked unexpectedly: {msg}")
        else:
            advanced = self.workflow.advance_step()
            if not advanced:
                print("[WARN] advance_step returned False at Step1")

        # リスト更新（シグナル再発火抑止のため blockSignals 中で選択復元）
        self.refresh_album_list()
        for i in range(self.album_list.count()):
            item = self.album_list.item(i)
            if item.data(Qt.UserRole) == album_folder:
                self.album_list.setCurrentItem(item)
                break

        # 念のため現在ステップを再評価し表示パネルを強制同期
        step = self.workflow.get_current_step()
        self.step_stack.setCurrentIndex(max(0, step - 1))
        current_panel = self.step_stack.currentWidget()
        if hasattr(current_panel, 'load_album'):
            current_panel.load_album(album_folder)
        # ステータスバー更新
        step_name = self.workflow.get_current_step_name()
        album_name = self.workflow.state.get_album_name() if self.workflow.state else ''
        self.status_bar.showMessage(f"{album_name} - {step_name}")
    
    def on_step_completed(self):
        """ステップ完了時の処理"""
        if not self.workflow.state:
            print("[DEBUG] on_step_completed: workflow.state が None")
            return
        
        current_step = self.workflow.get_current_step()
        print(f"[DEBUG] on_step_completed: 現在のステップ = {current_step}")

        if current_step == 7 and self.current_album_folder and not os.path.exists(self.current_album_folder):
            # Step 7のゴミ箱移動後は、存在しないstate.jsonへ保存しない。
            self.current_album_folder = None
            self.workflow.state = None
            self.workflow.current_album_folder = None
            self.refresh_album_list()
            self.step_stack.setCurrentIndex(1)
            self.status_bar.showMessage("転送完了。作業フォルダをゴミ箱へ移動しました")
            return
        
        # 次のステップに進む
        if self.workflow.advance_step():
            new_step = self.workflow.get_current_step()
            print(f"[DEBUG] on_step_completed: 次のステップに進みました = {new_step}")
            
            if self.current_album_folder:
                # ワークフローを再読み込み
                if not self.workflow.load_album(self.current_album_folder):
                    print(f"[ERROR] on_step_completed: アルバム再読み込み失敗")
                    return
                
                step = self.workflow.get_current_step()
                panel_index = step
                print(f"[DEBUG] on_step_completed: step = {step}, パネルインデックス = {panel_index}")
                
                # パネルを切り替え
                self.step_stack.setCurrentIndex(panel_index)
                print(f"[DEBUG] on_step_completed: パネルを切り替えました (index={panel_index})")
                
                # パネルを更新
                current_panel = self.step_stack.currentWidget()
                print(f"[DEBUG] on_step_completed: 現在のパネル = {current_panel}")
                if hasattr(current_panel, 'load_album'):
                    print(f"[DEBUG] on_step_completed: パネルのload_album()を呼び出し")
                    current_panel.load_album(self.current_album_folder)
                
                # ステータスバーを更新
                step_name = self.workflow.get_current_step_name()
                album_name = self.workflow.state.get_album_name()
                self.status_bar.showMessage(f"{album_name} - {step_name}")
                print(f"[DEBUG] Updated status bar: {album_name} - {step_name}")
            
            # 最後にアルバムリストを更新（選択変更イベントを抑止）
            self.refresh_album_list()
        else:
            print(f"[WARNING] on_step_completed: advance_step() が False を返しました")
    
    def on_settings(self):
        """設定ボタンが押されたときの処理"""
        from gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            # 設定が保存された場合、config を再読み込み
            self.config.load()
            self.status_bar.showMessage("設定を更新しました", 3000)
    
    def on_show_log_viewer(self):
        """ログビューアーボタンが押されたときの処理"""
        if not self.current_album_folder or not os.path.isdir(self.current_album_folder):
            QMessageBox.warning(self, "ログビューアー", "アルバムを選択してください。")
            return
        
        from gui.log_viewer_dialog import LogViewerDialog
        from logic.log_manager import get_logger
        
        logger = get_logger()
        logger.set_album_folder(self.current_album_folder)
        
        dialog = LogViewerDialog(logger, self)
        dialog.exec()
    
    def on_batch_process(self):
        """一括処理ボタンが押されたときの処理"""
        # WorkDirから全アルバムフォルダを取得
        work_dir = self.config.get_directory("WorkDir")
        if not work_dir or not os.path.isdir(work_dir):
            QMessageBox.warning(self, "一括処理", "作業フォルダ (WorkDir) が設定されていません。")
            return
        
        # アルバムフォルダを収集（state.jsonがあるもの）
        album_folders = []
        try:
            for item_name in os.listdir(work_dir):
                item_path = os.path.join(work_dir, item_name)
                if os.path.isdir(item_path):
                    state_file = os.path.join(item_path, "state.json")
                    if os.path.exists(state_file):
                        album_folders.append(item_path)
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"アルバム一覧の取得に失敗しました:\n{e}")
            return
        
        if not album_folders:
            QMessageBox.information(self, "一括処理", "処理可能なアルバムが見つかりませんでした。")
            return
        
        # 一括処理ダイアログを表示
        from gui.batch_process_dialog import BatchProcessDialog
        dialog = BatchProcessDialog(album_folders, self.config, self)
        dialog.exec()
        self.refresh_album_list()
        # バッチが進めた状態を現在のパネルにも反映する。
        self.current_album_folder = None
        self.on_album_selected(self.album_list.currentItem(), None)
    
    def on_rollback_step(self):
        """選択中アルバムを前のステップに戻す"""
        # 対象取得
        target_folder = None
        selected = self.album_list.currentItem()
        if selected:
            target_folder = selected.data(Qt.UserRole)
        if not target_folder:
            # 現在表示中のアルバムフォルダを利用
            target_folder = self.current_album_folder
        
        if not target_folder or not os.path.isdir(target_folder):
            QMessageBox.warning(self, "ロールバック", "ロールバックするアルバムを左のリストから選択してください。")
            return
        
        # ワークフローを読み込み
        temp_workflow = WorkflowManager(self.config)
        if not temp_workflow.load_album(target_folder):
            QMessageBox.critical(self, "エラー", "アルバムの読み込みに失敗しました。")
            return
        
        current_step = temp_workflow.get_current_step()
        album_name = temp_workflow.state.get_album_name()
        
        # 戻す先のステップを計算
        prev_step = current_step - 1
        
        # Step 2未満（Step0,1）に戻すことはできない（作業アルバムが存在しない段階）
        if prev_step < 2:
            QMessageBox.warning(self, "ロールバック", "Step 2（Demucs処理）より前には戻せません。\n（Step0,1はアルバム作成前の段階です）")
            return
        
        # 確認ダイアログ
        current_step_name = temp_workflow.STEP_NAMES.get(current_step, f"Step {current_step}")
        prev_step_name = temp_workflow.STEP_NAMES.get(prev_step, f"Step {prev_step}")
        
        reply = QMessageBox.question(
            self,
            "ステップロールバック",
            f"アルバム: {album_name}\n\n"
            f"現在: {current_step_name}\n"
            f"戻す先: {prev_step_name}\n\n"
            f"前のステップに戻しますか?\n"
            f"(ステップ完了フラグはクリアされます)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # ロールバック実行
        try:
            if not temp_workflow.rollback_step():
                raise RuntimeError("ロールバック状態の保存に失敗しました")
            
            # UIを更新
            self.refresh_album_list()
            
            # ロールバックしたアルバムを選択して表示
            if target_folder == self.current_album_folder:
                # 現在表示中のアルバムの場合、再読み込み
                print(f"[DEBUG] Rollback: Reloading current album, step={prev_step}")
                
                # 一時的に現在のアルバムをクリアしてon_album_selectedの干渉を防ぐ
                self.current_album_folder = None
                
                # 先にパネルを切り替え
                panel_index = prev_step
                print(f"[DEBUG] Rollback: Setting panel index to {panel_index}")
                self.step_stack.setCurrentIndex(panel_index)
                
                # ワークフローを再読み込み
                self.workflow.load_album(target_folder)
                self.current_album_folder = target_folder
                
                # パネルを更新
                current_panel = self.step_stack.currentWidget()
                print(f"[DEBUG] Rollback: Current panel after switch = {current_panel}")
                if hasattr(current_panel, 'load_album'):
                    print(f"[DEBUG] Rollback: Calling load_album on panel")
                    current_panel.load_album(target_folder)
                
                step_name = temp_workflow.STEP_NAMES.get(prev_step, f"Step {prev_step}")
                self.status_bar.showMessage(f"{album_name} - {step_name}")
                print(f"[DEBUG] Rollback: Updated status bar")
            
            QMessageBox.information(
                self,
                "完了",
                f"ステップを戻しました。\n\n"
                f"{album_name}\n"
                f"{prev_step_name} に戻りました。"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"ロールバックに失敗しました:\n{e}")

    def on_discard_album(self):
        """選択中アルバムの作業フォルダをゴミ箱へ移動（作業破棄）"""
        # 対象取得
        target_folder = None
        selected = self.album_list.currentItem()
        if selected:
            target_folder = selected.data(Qt.UserRole)
        if not target_folder:
            # 現在表示中のアルバムフォルダを利用
            target_folder = self.current_album_folder
        if not target_folder or not os.path.isdir(target_folder):
            QMessageBox.warning(self, "作業破棄", "破棄するアルバムを左のリストから選択してください。")
            return

        # WorkDir の配下か安全確認
        work_dir = self.config.get_directory("WorkDir") or ""
        try:
            norm_target = os.path.normcase(os.path.realpath(target_folder))
            norm_work = os.path.normcase(os.path.realpath(work_dir))
            if not work_dir or norm_target == norm_work or os.path.commonpath([norm_target, norm_work]) != norm_work:
                QMessageBox.critical(self, "作業破棄", "作業フォルダ配下以外は破棄できません。")
                return
        except (OSError, ValueError):
            QMessageBox.critical(self, "作業破棄", "作業フォルダの場所を確認できません。")
            return

        album_name = os.path.basename(target_folder)
        reply = QMessageBox.question(
            self,
            "作業破棄の確認",
            f"選択中のアルバム作業を破棄します。\n\n対象: {album_name}\n場所: {target_folder}\n\nこの操作は作業フォルダをゴミ箱へ移動します。続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # 破棄実行
        try:
            send2trash(target_folder)
        except Exception as e:
            QMessageBox.critical(self, "作業破棄", f"ゴミ箱への移動に失敗しました:\n{e}")
            return

        # UI 更新
        if self.current_album_folder == target_folder:
            self.current_album_folder = None
        self.refresh_album_list()
        self.album_list.clearSelection()
        # 初期パネルへ戻す
        self.step_stack.setCurrentIndex(1)
        self.status_bar.showMessage("作業を破棄しました（ゴミ箱へ移動）")
    
    def closeEvent(self, event):
        """ウィンドウを閉じるときの処理"""
        # 実行中のプロセスがあれば警告
        reply = QMessageBox.question(
            self,
            "確認",
            "アプリケーションを終了しますか?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # タイマーを停止
            self.refresh_timer.stop()
            event.accept()
        else:
            event.ignore()

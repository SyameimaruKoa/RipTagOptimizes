"""
Step 0: Music Center取り込みガイド
"""
import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox
)
from PySide6.QtCore import Qt

from logic.config_manager import ConfigManager
from logic.workflow_manager import WorkflowManager


class Step0MusicCenterPanel(QWidget):
    """Step 0: Music Center取り込みガイドパネル"""
    
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
        title = QLabel("<h2>Music Center で CD を取り込む</h2>")
        layout.addWidget(title)
        
        # 説明
        desc = QLabel(
            "Music Center を使って CD から音楽を FLAC 形式で取り込みます。\n"
            "取り込みが完了したら、「新規取り込み」タブから Step 1 でワークフローに追加します。"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        layout.addSpacing(20)
        
        # 手順セクション
        steps_label = QLabel("<h3>📋 取り込み手順</h3>")
        layout.addWidget(steps_label)
        
        # 手順1
        step1_label = QLabel(
            "<b>1. Music Center を起動</b><br>"
            "下のボタンをクリックして Music Center を起動してください。"
        )
        step1_label.setWordWrap(True)
        layout.addWidget(step1_label)
        
        # Music Center 起動ボタン
        launch_button = QPushButton("🎵 Music Center を起動")
        launch_button.clicked.connect(self.on_launch_music_center)
        launch_button.setFixedHeight(40)
        layout.addWidget(launch_button)
        
        layout.addSpacing(10)
        
        # 手順2
        step2_label = QLabel(
            "<b>2. CD を挿入</b><br>"
            "パソコンの光学ドライブに CD を挿入してください。"
        )
        step2_label.setWordWrap(True)
        layout.addWidget(step2_label)
        
        layout.addSpacing(10)
        
        # 手順3
        step3_label = QLabel(
            "<b>3. FLAC 形式で取り込み開始</b><br>"
            "Music Center で以下の設定を確認してから取り込みを開始してください：<br>"
            "• 取り込み形式: <b>FLAC</b><br>"
            "• 保存先: 設定で確認<br>"
            "• アルバム情報を確認してから取り込み"
        )
        step3_label.setWordWrap(True)
        layout.addWidget(step3_label)
        
        layout.addSpacing(20)
        
        # 完了後の案内
        next_label = QLabel(
            "<h3>✅ 取り込み完了後</h3>"
            "取り込みが完了したら、上部メニューの「新規取り込み」タブから Step 1 に進んでください。"
        )
        next_label.setWordWrap(True)
        layout.addWidget(next_label)
        
        layout.addStretch()
        
        # スキップボタン
        skip_layout = QHBoxLayout()
        skip_button = QPushButton("⏭ Step 1 へスキップ (既に取り込み済みの場合)")
        skip_button.clicked.connect(self.on_skip_to_step1)
        skip_layout.addWidget(skip_button)
        layout.addLayout(skip_layout)
    
    def load_album(self, album_folder: str):
        """アルバムを読み込み（このパネルでは何もしない）"""
        # Step0はガイド専用なので、アルバム読み込みは不要
        pass
    
    def on_launch_music_center(self):
        """Music Center を起動"""
        music_center_exe = r"C:\Program Files (x86)\Sony\Music Center\MusicCenter.exe"
        
        if not os.path.exists(music_center_exe):
            QMessageBox.warning(
                self,
                "エラー",
                f"Music Center が見つかりません:\n{music_center_exe}\n\n"
                "手動で Music Center を起動してください。"
            )
            return
        
        try:
            subprocess.Popen([music_center_exe])
            QMessageBox.information(
                self,
                "Music Center 起動中",
                "Music Center を起動しました。\n\n"
                "CD を挿入して、FLAC 形式での取り込みを開始してください。\n"
                "取り込み完了後、Music Center を閉じてください。\n\n"
                "⏱️ 監視中：Music Center の終了を待機中..."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "エラー",
                f"Music Center の起動に失敗しました:\n{e}"
            )
    
    def on_skip_to_step1(self):
        """Step 1 へスキップ"""
        # メインウィンドウに通知するシグナルを発火するか、
        # 直接タブを切り替える
        reply = QMessageBox.question(
            self,
            "確認",
            "Step 1 (新規取り込み) タブに移動しますか？\n\n"
            "既に Music Center で CD を取り込み済みの場合は、\n"
            "Step 1 で取り込んだアルバムをワークフローに追加できます。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # 親ウィンドウのstep_stackを切り替える
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, 'step_stack'):
                    parent.step_stack.setCurrentIndex(1)  # Step 1 に切り替え
                    parent.status_bar.showMessage("新規取り込みを開始してください")
                    break
                parent = parent.parent()

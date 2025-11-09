"""
CD取り込み自動化ワークフロー・マスターGUI
メインエントリーポイント

⚠️ 注意: このアプリケーションは個人的な使用を目的として開発されました。
   使用は自己責任でお願いします。データの損失や破損が発生する可能性があるため、
   必ず重要なデータはバックアップしてからご使用ください。
"""
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow
from logic.config_manager import ConfigManager


def check_required_directories(config: ConfigManager) -> tuple[bool, list[str]]:
    """必須ディレクトリが設定されており、実際に存在するかチェック"""
    from pathlib import Path
    
    required_dirs = [
        ("Paths", "WorkDir", "作業フォルダ"),
        ("Paths", "MusicCenterDir", "Music Center フォルダ"),
        ("Settings", "ExternalOutputDir", "外部ツール出力先")
    ]
    
    missing = []
    for section, key, label in required_dirs:
        value = config.config.get(section, key, fallback='').strip()
        if not value:
            missing.append(f"{label} (未設定)")
        elif not Path(value).exists():
            missing.append(f"{label} (パスが存在しません: {value})")
    
    return len(missing) == 0, missing


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    app.setApplicationName("CD取り込み自動化ワークフロー")
    app.setOrganizationName("CDWorkflow")
    
    # 初回起動時の免責事項表示
    config = ConfigManager()
    accepted = config.config.get('Settings', 'AcceptedDisclaimer', fallback='false').lower()
    
    if accepted != 'true':
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("免責事項")
        msg.setText(
            "⚠️ 重要な注意事項\n\n"
            "このアプリケーションは個人的な使用を目的として開発されたものです。\n\n"
            "• 作者自身のワークフローに最適化されており、他の環境での動作は保証されません\n"
            "• データの損失や破損が発生する可能性があります\n"
            "• 使用は完全に自己責任となります\n\n"
            "必ず重要なデータはバックアップしてからご使用ください。\n\n"
            "上記を理解し、同意しますか？"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        if msg.exec() != QMessageBox.Yes:
            return 0
        
        # 同意を記録
        if 'Settings' not in config.config:
            config.config['Settings'] = {}
        config.config['Settings']['AcceptedDisclaimer'] = 'true'
        config.save()
    
    # 設定チェック
    is_configured, missing_dirs = check_required_directories(config)
    
    if not is_configured:
        # 必須設定が未設定の場合、設定ダイアログを表示
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("初期設定が必要です")
        msg.setText(
            "アプリケーションの実行に必要なディレクトリが設定されていません。\n\n"
            "以下の設定が必要です:\n" +
            "\n".join([f"• {d}" for d in missing_dirs]) +
            "\n\n設定画面を開きますか？"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        if msg.exec() == QMessageBox.Yes:
            from gui.settings_dialog import SettingsDialog
            dialog = SettingsDialog(config)
            if dialog.exec() != QMessageBox.Accepted:
                # キャンセルされた場合は終了
                QMessageBox.critical(
                    None,
                    "起動中止",
                    "必須設定が完了していないため、アプリケーションを起動できません。"
                )
                return 1
            
            # 再チェック
            config = ConfigManager()  # リロード
            is_configured, missing_dirs = check_required_directories(config)
            if not is_configured:
                QMessageBox.critical(
                    None,
                    "設定不完全",
                    "必須ディレクトリが設定されていません。\nアプリケーションを終了します。"
                )
                return 1
        else:
            return 1
    
    # メインウィンドウを表示
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

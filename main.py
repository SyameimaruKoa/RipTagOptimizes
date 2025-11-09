"""
CD取り込み自動化ワークフロー・マスターGUI
メインエントリーポイント
"""
import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    """メイン関数"""
    app = QApplication(sys.argv)
    app.setApplicationName("CD取り込み自動化ワークフロー")
    app.setOrganizationName("CDWorkflow")
    
    # メインウィンドウを表示
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

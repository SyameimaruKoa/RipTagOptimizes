"""
ログマネージャー - _logs フォルダへのログ保存機能
"""
import os
import datetime
from typing import Optional


class LogManager:
    """ログ管理クラス"""
    
    def __init__(self, album_folder: Optional[str] = None):
        self.album_folder = album_folder
        self.log_dir = None
        
        if album_folder:
            self.set_album_folder(album_folder)
    
    def set_album_folder(self, album_folder: str):
        """アルバムフォルダを設定してログディレクトリを初期化"""
        self.album_folder = album_folder
        self.log_dir = os.path.join(album_folder, "_logs")
        
        # _logs ディレクトリを作成
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except Exception as e:
                print(f"[LogManager] ログディレクトリ作成失敗: {e}")
                self.log_dir = None
    
    def log(self, step: str, level: str, message: str):
        """ログを記録
        
        Args:
            step: ステップ名（例: "Step1_Import", "Step2_Demucs"）
            level: ログレベル（INFO, WARNING, ERROR）
            message: ログメッセージ
        """
        if not self.log_dir or not os.path.exists(self.log_dir):
            # ログディレクトリがない場合はコンソール出力のみ
            print(f"[{step}] [{level}] {message}")
            return
        
        try:
            # ログファイル名: Step名_日付.log
            today = datetime.datetime.now().strftime("%Y%m%d")
            log_file = os.path.join(self.log_dir, f"{step}_{today}.log")
            
            # タイムスタンプ付きでログを追記
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"[{timestamp}] [{level}] {message}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
            
            # コンソールにも出力
            print(f"[{step}] [{level}] {message}")
        
        except Exception as e:
            # ログ保存失敗時はコンソール出力のみ
            print(f"[{step}] [{level}] {message}")
            print(f"[LogManager] ログ保存失敗: {e}")
    
    def info(self, step: str, message: str):
        """INFO レベルのログを記録"""
        self.log(step, "INFO", message)
    
    def warning(self, step: str, message: str):
        """WARNING レベルのログを記録"""
        self.log(step, "WARNING", message)
    
    def error(self, step: str, message: str):
        """ERROR レベルのログを記録"""
        self.log(step, "ERROR", message)
    
    def get_log_files(self) -> list[str]:
        """ログファイル一覧を取得"""
        if not self.log_dir or not os.path.exists(self.log_dir):
            return []
        
        try:
            files = [f for f in os.listdir(self.log_dir) if f.endswith('.log')]
            return sorted(files, reverse=True)  # 新しい順
        except Exception:
            return []
    
    def read_log_file(self, filename: str) -> str:
        """ログファイルの内容を読み込む"""
        if not self.log_dir:
            return ""
        
        try:
            log_file = os.path.join(self.log_dir, filename)
            with open(log_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"ログファイルの読み込みに失敗しました: {e}"
    
    def clear_old_logs(self, days: int = 30):
        """指定日数より古いログファイルを削除
        
        Args:
            days: 保持する日数（デフォルト: 30日）
        """
        if not self.log_dir or not os.path.exists(self.log_dir):
            return
        
        try:
            import time
            cutoff_time = time.time() - (days * 86400)  # 秒単位
            
            for filename in os.listdir(self.log_dir):
                if not filename.endswith('.log'):
                    continue
                
                filepath = os.path.join(self.log_dir, filename)
                if os.path.getmtime(filepath) < cutoff_time:
                    try:
                        os.remove(filepath)
                        print(f"[LogManager] 古いログを削除: {filename}")
                    except Exception as e:
                        print(f"[LogManager] ログ削除失敗: {filename} - {e}")
        
        except Exception as e:
            print(f"[LogManager] 古いログのクリーンアップに失敗: {e}")


# グローバルログマネージャーインスタンス
_global_logger: Optional[LogManager] = None


def get_logger() -> LogManager:
    """グローバルログマネージャーを取得"""
    global _global_logger
    if _global_logger is None:
        _global_logger = LogManager()
    return _global_logger


def set_album_folder(album_folder: str):
    """グローバルログマネージャーのアルバムフォルダを設定"""
    logger = get_logger()
    logger.set_album_folder(album_folder)

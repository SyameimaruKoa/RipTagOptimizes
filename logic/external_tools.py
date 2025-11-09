"""
外部ツールの実行・監視を管理するモジュール
"""
import subprocess
import os
from typing import Optional, Callable
from PySide6.QtCore import QProcess, QObject, Signal


class ExternalToolRunner(QObject):
    """外部ツールを実行・監視するクラス (QProcess ラッパー)"""
    
    # シグナル定義
    started = Signal()
    finished = Signal(int, str)  # exit_code, exit_status
    error_occurred = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.process: Optional[QProcess] = None
        self.tool_name = ""
    
    def run_gui_tool(self, tool_path: str, args: list[str] = None, working_dir: str = None) -> bool:
        """
        GUIツール（Mp3tag, foobar2000等）を起動し、終了を監視する
        
        Args:
            tool_path: ツールの実行ファイルパス
            args: コマンドライン引数のリスト
            working_dir: 作業ディレクトリ
        
        Returns:
            起動成功時 True
        """
        if not os.path.exists(tool_path):
            self.error_occurred.emit(f"ツールが見つかりません: {tool_path}")
            return False
        
        self.tool_name = os.path.basename(tool_path)
        self.process = QProcess(self)
        
        # シグナル接続
        self.process.started.connect(self._on_started)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)
        
        # 作業ディレクトリ設定
        if working_dir and os.path.exists(working_dir):
            self.process.setWorkingDirectory(working_dir)
        
        # 起動
        if args:
            self.process.start(tool_path, args)
        else:
            self.process.start(tool_path)
        
        return True
    
    def run_cli_tool(self, tool_path: str, args: list[str], working_dir: str = None) -> tuple[bool, str, str]:
        """
        CLIツール（flac, magick等）を同期実行し、結果を返す
        
        Args:
            tool_path: ツールの実行ファイルパス
            args: コマンドライン引数のリスト
            working_dir: 作業ディレクトリ
        
        Returns:
            (成功フラグ, 標準出力, 標準エラー出力)
        """
        if not os.path.exists(tool_path):
            return False, "", f"ツールが見つかりません: {tool_path}"
        
        try:
            result = subprocess.run(
                [tool_path] + args,
                cwd=working_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=300  # 5分タイムアウト
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return False, "", "タイムアウト: コマンドの実行に5分以上かかりました"
        except Exception as e:
            return False, "", f"実行エラー: {str(e)}"
    
    def is_running(self) -> bool:
        """プロセスが実行中かどうか"""
        return self.process is not None and self.process.state() == QProcess.Running
    
    def terminate(self):
        """プロセスを強制終了"""
        if self.process and self.is_running():
            self.process.terminate()
            self.process.waitForFinished(3000)  # 3秒待機
            if self.is_running():
                self.process.kill()
    
    def _on_started(self):
        """プロセス開始時のハンドラ"""
        print(f"[INFO] {self.tool_name} を起動しました")
        self.started.emit()
    
    def _on_finished(self, exit_code: int, exit_status):
        """プロセス終了時のハンドラ"""
        status_str = "正常終了" if exit_code == 0 else f"異常終了 (code: {exit_code})"
        print(f"[INFO] {self.tool_name} が終了しました: {status_str}")
        self.finished.emit(exit_code, str(exit_status))
    
    def _on_error(self, error):
        """プロセスエラー時のハンドラ"""
        error_msg = f"{self.tool_name} 実行エラー: {error}"
        print(f"[ERROR] {error_msg}")
        self.error_occurred.emit(error_msg)


class FastCopyRunner:
    """FastCopy 専用実行クラス（またはshutilによるフォールバック）"""
    
    @staticmethod
    def move_folder(fastcopy_path: str, source: str, dest: str) -> tuple[bool, str]:
        """
        FastCopyでフォルダを移動（失敗時はshutilを使用）
        
        Args:
            fastcopy_path: FastCopy.exeのパス（空の場合はshutilを使用）
            source: 移動元フォルダ
            dest: 移動先親フォルダ
        
        Returns:
            (成功フラグ, エラーメッセージ)
        """
        if not os.path.exists(source):
            return False, f"Source folder not found: {source}"
        
        # 移動先の完全なパスを構築
        source_name = os.path.basename(source.rstrip('\\'))
        dest_full = os.path.join(dest, source_name)
        
        # FastCopyを使用する場合
        if fastcopy_path and os.path.exists(fastcopy_path):
            return FastCopyRunner._move_with_fastcopy(fastcopy_path, source, dest, dest_full)
        else:
            # FastCopyが無い場合はshutilを使用
            print("[INFO] FastCopy not found, using shutil.move instead")
            return FastCopyRunner._move_with_shutil(source, dest_full)
    
    @staticmethod
    def _move_with_fastcopy(fastcopy_path: str, source: str, dest: str, dest_full: str) -> tuple[bool, str]:
        """FastCopyを使用して移動"""
        # FastCopyのコマンドライン引数
        # FastCopy.exe /cmd=move /to=移動先親フォルダ "移動元フォルダ" /auto_close
        args = [
            "/cmd=move",
            f"/to={dest}",
            source,
            "/auto_close"
        ]
        
        print(f"[DEBUG] FastCopy: {fastcopy_path} {' '.join(args)}")
        
        try:
            result = subprocess.run(
                [fastcopy_path] + args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore',
                timeout=600
            )
            
            if result.returncode == 0 and os.path.exists(dest_full):
                return True, ""
            else:
                # FastCopy失敗時はshutilにフォールバック
                print(f"[WARNING] FastCopy failed (code: {result.returncode}), trying shutil")
                return FastCopyRunner._move_with_shutil(source, dest_full)
                
        except subprocess.TimeoutExpired:
            return False, "Timeout: Move operation took more than 10 minutes"
        except Exception as e:
            print(f"[WARNING] FastCopy exception: {e}, trying shutil")
            return FastCopyRunner._move_with_shutil(source, dest_full)
    
    @staticmethod
    def _move_with_shutil(source: str, dest_full: str) -> tuple[bool, str]:
        """shutilを使用して移動"""
        import shutil
        
        try:
            # 移動先が既に存在する場合は削除
            if os.path.exists(dest_full):
                shutil.rmtree(dest_full)
            
            # フォルダを移動
            shutil.move(source, dest_full)
            
            if os.path.exists(dest_full):
                print(f"[INFO] Successfully moved: {source} -> {dest_full}")
                return True, ""
            else:
                return False, "Move completed but destination folder not found"
                
        except Exception as e:
            return False, f"Move error: {str(e)}"

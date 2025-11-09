"""
config.ini の読み書きを管理するモジュール
"""
import configparser
import os
from pathlib import Path
from typing import Optional


class ConfigManager:
    """設定ファイル管理クラス"""
    
    def __init__(self, config_path: str = "config.ini"):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.load()
    
    def load(self) -> bool:
        """設定ファイルを読み込む"""
        if not os.path.exists(self.config_path):
            self._create_default_config()
            return False
        
        try:
            self.config.read(self.config_path, encoding='utf-8')
            return True
        except Exception as e:
            print(f"[ERROR] 設定ファイル読み込みエラー: {e}")
            return False
    
    def save(self) -> bool:
        """設定ファイルを保存する"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            return True
        except Exception as e:
            print(f"[ERROR] 設定ファイル保存エラー: {e}")
            return False
    
    def _create_default_config(self):
        """デフォルト設定ファイルを作成"""
        self.config['Paths'] = {
            'Mp3Tag': '',
            'MediaHuman': '',
            'Foobar2000': '',
            'WinSCP': '',
            'Flac': '',
            'Metaflac': '',
            'Magick': '',
            'MusicCenterDir': '',
            'WorkDir': './work',
            'NasFlacDir': '',
            'NasFlacDirSftp': '',
        }
        self.config['Settings'] = {
            'JpegQuality': '85',
            'WebpQuality': '85',
            'ResizeWidth': '600',
        }
        self.config['Demucs'] = {
            'SkipKeywords': 'instrumental, inst., (inst), -inst-, off vocal, off-vocal, offvocal, backing track, karaoke, voiceless, minus one',
        }
        self.save()
    
    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """ツールのパスを取得（存在チェック付き）"""
        path = self.config.get('Paths', tool_name, fallback='')
        if path and os.path.exists(path):
            return path
        return None
    
    def get_directory(self, dir_name: str) -> str:
        """ディレクトリパスを取得"""
        return self.config.get('Paths', dir_name, fallback='')
    
    def get_setting(self, key: str, fallback=None):
        """設定値を取得"""
        return self.config.get('Settings', key, fallback=fallback)
    
    def get_demucs_keywords(self) -> list[str]:
        """Demucs除外キーワードを取得"""
        keywords_str = self.config.get('Demucs', 'SkipKeywords', fallback='')
        if not keywords_str:
            return []
        # カンマ区切りで分割し、前後の空白を削除
        return [kw.strip() for kw in keywords_str.split(',') if kw.strip()]
    
    def set_tool_path(self, tool_name: str, path: str):
        """ツールのパスを設定"""
        if 'Paths' not in self.config:
            self.config['Paths'] = {}
        self.config['Paths'][tool_name] = path
    
    def set_directory(self, dir_name: str, path: str):
        """ディレクトリパスを設定"""
        if 'Paths' not in self.config:
            self.config['Paths'] = {}
        self.config['Paths'][dir_name] = path
    
    def set_setting(self, key: str, value: str):
        """設定値を設定"""
        if 'Settings' not in self.config:
            self.config['Settings'] = {}
        self.config['Settings'][key] = value

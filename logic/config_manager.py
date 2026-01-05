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
        # Disable interpolation so percent signs like %USERPROFILE% are
        # preserved and can be expanded later with os.path.expandvars.
        # Using interpolation=None avoids ConfigParser treating %... as
        # interpolation placeholders which caused InterpolationSyntaxError.
        self.config = configparser.ConfigParser(interpolation=None)
        self.load()
    
    @staticmethod
    def expand_path(path: str) -> str:
        """環境変数を展開してパスを返す
        
        Args:
            path: 環境変数を含む可能性のあるパス（例: %USERPROFILE%\\Downloads）
        
        Returns:
            展開されたパス
        """
        if not path:
            return ""
        # Windows環境変数を展開
        expanded = os.path.expandvars(path)
        # ユーザーホームディレクトリを展開（~）
        expanded = os.path.expanduser(expanded)
        return expanded
    
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
        """デフォルト設定ファイルを作成（一般的なツールパスを自動検出）"""
        # 一般的なツールのパスを自動検出
        detected_paths = self._detect_tool_paths()
        
        self.config['Paths'] = {
            'Mp3tag': detected_paths.get('Mp3tag', ''),
            'MediaHuman': detected_paths.get('MediaHuman', ''),
            'Foobar2000': detected_paths.get('Foobar2000', ''),
            'WinSCP': detected_paths.get('WinSCP', ''),
            'Flac': detected_paths.get('Flac', ''),
            'Metaflac': detected_paths.get('Metaflac', ''),
            'Magick': detected_paths.get('Magick', ''),
            'iTunes': detected_paths.get('iTunes', ''),
            'FreeFileSync': detected_paths.get('FreeFileSync', ''),
            'FreeFileSync_Config': '',
            'MusicCenterDir': '%USERPROFILE%\\Music\\Music Center',
            'WorkDir': './work',
        }
        self.config['DefaultDirectories'] = {
            'demucs_output': '%USERPROFILE%\\Downloads',
            'aac_output': '変換MediaHuman',
            'opus_output': 'foobar2000',
            'artwork_select': '%USERPROFILE%\\Downloads',
        }
        self.config['Settings'] = {
            'JpegQuality': '85',
            'WebpQuality': '85',
            'ResizeWidth': '600',
            'AutoReplayGain': '1',
            'ExternalOutputDir': '%USERPROFILE%\\Videos\\エンコード済み',
            'FoobarUseAddSwitch': '1',
            'AcceptedDisclaimer': 'false',
        }
        self.config['Demucs'] = {
            'SkipKeywords': 'instrumental, inst., (inst), -inst-, off vocal, off-vocal, offvocal, backing track, karaoke, voiceless, minus one, game version, オリジナル・カラオケ, ソロ・リミックス, ドラマ, ボーナス・トラック, インスト, オフボーカル, オフボ, カラオケ, 歌無し',
        }
        self.config['Artwork'] = {
            'JpegQuality': '85',
            'WebpQuality': '85',
            'ResizeWidth': '600',
        }
        self.save()
    
    def _detect_tool_paths(self) -> dict:
        """一般的なツールのパスを自動検出する
        
        Returns:
            検出されたツール名とパスの辞書
        """
        detected = {}
        
        # 検索対象のツール定義（ツール名: [相対パスのリスト]）
        tool_definitions = {
            'Mp3tag': [
                r'C:\Program Files\Mp3tag\Mp3tag.exe',
                r'C:\Program Files (x86)\Mp3tag\Mp3tag.exe',
            ],
            'MediaHuman': [
                r'C:\Program Files\MediaHuman\Audio Converter\MHAudioConverter.exe',
                r'C:\Program Files (x86)\MediaHuman\Audio Converter\MHAudioConverter.exe',
            ],
            'Foobar2000': [
                r'C:\Program Files\foobar2000\foobar2000.exe',
                r'C:\Program Files (x86)\foobar2000\foobar2000.exe',
            ],
            'WinSCP': [
                r'%LOCALAPPDATA%\Programs\WinSCP\WinSCP.exe',
                r'C:\Program Files\WinSCP\WinSCP.exe',
                r'C:\Program Files (x86)\WinSCP\WinSCP.exe',
            ],
            'iTunes': [
                r'C:\Program Files\iTunes\iTunes.exe',
                r'C:\Program Files (x86)\iTunes\iTunes.exe',
            ],
            'FreeFileSync': [
                r'C:\Program Files\FreeFileSync\FreeFileSync.exe',
                r'C:\Program Files (x86)\FreeFileSync\FreeFileSync.exe',
            ],
            'Magick': [
                r'C:\Program Files\ImageMagick-7.1.2-Q16\magick.exe',
                r'C:\Program Files\ImageMagick-7.1.1-Q16\magick.exe',
                r'C:\Program Files\ImageMagick-7.1.0-Q16\magick.exe',
                r'C:\Program Files (x86)\ImageMagick-7.1.2-Q16\magick.exe',
            ],
            'Flac': [
                r'%USERPROFILE%\OneDrive\CUIApplication\flac\flac.exe',
                r'C:\Program Files\FLAC\flac.exe',
                r'C:\Program Files (x86)\FLAC\flac.exe',
            ],
            'Metaflac': [
                r'%USERPROFILE%\OneDrive\CUIApplication\flac\metaflac.exe',
                r'C:\Program Files\FLAC\metaflac.exe',
                r'C:\Program Files (x86)\FLAC\metaflac.exe',
            ],
        }
        
        # 各ツールのパスを検索
        for tool_name, paths in tool_definitions.items():
            for path in paths:
                expanded = self.expand_path(path)
                if os.path.exists(expanded):
                    detected[tool_name] = path  # 環境変数形式で保存
                    break
        
        return detected
    
    def get_tool_path(self, tool_name: str) -> Optional[str]:
        """ツールのパスを取得（存在チェック付き）"""
        path = self.config.get('Paths', tool_name, fallback='')
        if not path:
            return None
        # 環境変数を展開
        expanded_path = self.expand_path(path)
        if expanded_path and os.path.exists(expanded_path):
            return expanded_path
        return None
    
    def get_directory(self, dir_name: str) -> str:
        """ディレクトリパスを取得（環境変数展開済み、絶対パスに変換、存在しない場合は作成）"""
        path = self.config.get('Paths', dir_name, fallback='')
        expanded = self.expand_path(path)
        # 相対パスの場合は絶対パスに変換
        if expanded:
            expanded = os.path.abspath(expanded)
            # フォルダが存在しない場合は作成
            try:
                os.makedirs(expanded, exist_ok=True)
            except Exception as e:
                print(f"[WARNING] フォルダ作成エラー ({dir_name}): {expanded} - {e}")
        return expanded
    
    def get_default_directory(self, key: str, fallback: str = "") -> str:
        """初期ディレクトリパスを取得（環境変数展開済み）
        
        Args:
            key: DefaultDirectoriesセクションのキー名
            fallback: デフォルト値
        
        Returns:
            展開されたディレクトリパス
        """
        path = self.config.get('DefaultDirectories', key, fallback=fallback)
        return self.expand_path(path)
    
    def get_directory_name(self, key: str, fallback: str = "") -> str:
        """初期ディレクトリのフォルダ名を取得（展開なし）
        
        Args:
            key: DefaultDirectoriesセクションのキー名
            fallback: デフォルト値
        
        Returns:
            展開されていないフォルダ名（例: '変換MediaHuman'）
        """
        return self.config.get('DefaultDirectories', key, fallback=fallback)
    
    def get_setting(self, key: str, fallback=None):
        """設定値を取得（パス系の設定は環境変数展開済み）"""
        value = self.config.get('Settings', key, fallback=fallback)
        # パス系の設定は環境変数を展開
        if key.lower().endswith('dir') or key.lower().endswith('path'):
            return self.expand_path(value) if value else fallback
        return value
    
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

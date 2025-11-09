"""
state.json の読み書きを管理するモジュール
"""
import json
import os
from typing import Optional, Any
from datetime import datetime


class StateManager:
    """状態管理ファイル (state.json) の読み書きを管理するクラス"""
    
    def __init__(self, album_folder: str):
        self.album_folder = album_folder
        self.state_path = os.path.join(album_folder, "state.json")
        self.state = {}
    
    def load(self) -> bool:
        """state.json を読み込む"""
        if not os.path.exists(self.state_path):
            return False
        
        try:
            with open(self.state_path, 'r', encoding='utf-8') as f:
                self.state = json.load(f)
            return True
        except Exception as e:
            print(f"[ERROR] state.json 読み込みエラー: {e}")
            return False
    
    def save(self) -> bool:
        """state.json を保存する"""
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] state.json 保存エラー: {e}")
            return False
    
    def initialize(self, album_name: str, artist_name: str, flac_files: list[str]) -> bool:
        """新規アルバムの state.json を初期化"""
        self.state = {
            "version": "1.0",
            "albumName": album_name,
            "artistName": artist_name,
            "currentStep": 1,
            "status": "WAITING_USER",
            "tracks": [
                {
                    "id": f"track_{i+1:03d}",
                    "originalFile": fname,
                    "finalFile": fname,
                    "demucsTarget": True,
                    "isInstrumental": False
                }
                for i, fname in enumerate(flac_files)
            ],
            "paths": {
                "demucsOutput": "",
                "aacOutput": "_aac_output",
                "opusOutput": "_opus_output",
                "artworkResized": "_artwork_resized",
                "finalFlac": "_final_flac",
                "rawFlacSrc": "_flac_src"
            },
            "hasArtwork": None,
            "flags": {
                "step2_skipped": False
            },
            "lastError": None
        }
        return self.save()
    
    def get_current_step(self) -> int:
        """現在のステップ番号を取得"""
        return self.state.get("currentStep", 1)
    
    def set_current_step(self, step: int) -> bool:
        """現在のステップ番号を設定"""
        self.state["currentStep"] = step
        return self.save()
    
    def get_status(self) -> str:
        """現在のステータスを取得"""
        return self.state.get("status", "WAITING_USER")
    
    def set_status(self, status: str) -> bool:
        """ステータスを設定"""
        self.state["status"] = status
        return self.save()
    
    def get_tracks(self) -> list[dict]:
        """トラック情報を取得"""
        return self.state.get("tracks", [])
    
    def update_track(self, track_id: str, updates: dict) -> bool:
        """特定のトラック情報を更新"""
        tracks = self.state.get("tracks", [])
        for track in tracks:
            if track.get("id") == track_id:
                track.update(updates)
                return self.save()
        return False
    
    def get_album_name(self) -> str:
        """アルバム名を取得"""
        return self.state.get("albumName", "Unknown Album")
    
    def get_artist_name(self) -> str:
        """アーティスト名を取得"""
        return self.state.get("artistName", "Unknown Artist")
    
    def set_error(self, step: int, message: str) -> bool:
        """エラー情報を記録"""
        self.state["lastError"] = {
            "step": step,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.state["status"] = "ERROR"
        return self.save()
    
    def clear_error(self) -> bool:
        """エラー情報をクリア"""
        self.state["lastError"] = None
        if self.state.get("status") == "ERROR":
            self.state["status"] = "WAITING_USER"
        return self.save()
    
    def get_path(self, key: str) -> str:
        """パス情報を取得"""
        return self.state.get("paths", {}).get(key, "")
    
    def set_path(self, key: str, value: str) -> bool:
        """パス情報を設定"""
        if "paths" not in self.state:
            self.state["paths"] = {}
        self.state["paths"][key] = value
        return self.save()
    
    def get_flag(self, key: str) -> Any:
        """フラグを取得"""
        return self.state.get("flags", {}).get(key)
    
    def set_flag(self, key: str, value: Any) -> bool:
        """フラグを設定"""
        if "flags" not in self.state:
            self.state["flags"] = {}
        self.state["flags"][key] = value
        return self.save()
    
    def has_artwork(self) -> Optional[bool]:
        """アートワークの有無を取得"""
        return self.state.get("hasArtwork")
    
    def set_artwork(self, has_artwork: bool) -> bool:
        """アートワークの有無を設定"""
        self.state["hasArtwork"] = has_artwork
        return self.save()

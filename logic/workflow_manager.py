"""
ワークフロー全体の進行管理
"""
import os
from typing import Optional
from .state_manager import StateManager
from .config_manager import ConfigManager


class WorkflowManager:
    """ワークフローの進行を管理するクラス"""
    
    STEP_NAMES = {
        1: "新規取り込み",
        2: "Demucs処理",
        3: "FLAC完成 (タグ・リネーム)",
        4: "AAC変換 (MediaHuman)",
        5: "Opus変換 (foobar2000)",
        6: "アートワーク最適化 & タグ手直し",
        7: "アートワーク交換",
        8: "ReplayGain & アーカイブ",
        9: "最終配置 (転送)",
        10: "クリーンアップ"
    }
    
    def __init__(self, config: ConfigManager):
        self.config = config
        self.state: Optional[StateManager] = None
        self.current_album_folder: Optional[str] = None
    
    def load_album(self, album_folder: str) -> bool:
        """
        アルバムを読み込む
        
        Args:
            album_folder: アルバムフォルダのパス
        
        Returns:
            読み込み成功時 True
        """
        self.current_album_folder = album_folder
        self.state = StateManager(album_folder)
        return self.state.load()
    
    def get_current_step(self) -> int:
        """現在のステップ番号を取得"""
        if not self.state:
            return 0
        return self.state.get_current_step()
    
    def get_current_step_name(self) -> str:
        """現在のステップ名を取得"""
        step = self.get_current_step()
        return self.STEP_NAMES.get(step, "不明なステップ")
    
    def advance_step(self) -> bool:
        """次のステップに進む"""
        if not self.state:
            return False
        
        current = self.state.get_current_step()
        
        # ステップスキップロジック
        next_step = current + 1
        
        # Step 7: 交換ステップはアートワークが無ければスキップ
        if next_step == 7:
            if not self.state.has_artwork():
                print("[INFO] アートワーク未生成のため Step7(交換) をスキップ")
                next_step = 8
        
        # 最大ステップチェック
        if next_step > 10:
            self.state.set_status("COMPLETED")
            return True
        
        return self.state.set_current_step(next_step)
    
    def can_advance_to_next_step(self) -> tuple[bool, str]:
        """
        次のステップに進める状態かチェック
        
        Returns:
            (進行可能フラグ, エラーメッセージ)
        """
        if not self.state:
            return False, "アルバムが読み込まれていません"
        
        current_step = self.state.get_current_step()
        
        # 各ステップ固有のバリデーション
        if current_step == 1:
            # Step1は state.json が作成されていれば完了
            return True, ""
        
        elif current_step == 2:
            # Step2: Demucsがスキップされた場合も進行可
            return True, ""
        
        elif current_step == 3:
            # Step3: 全トラックの finalFile が設定されているか
            tracks = self.state.get_tracks()
            for track in tracks:
                if not track.get("finalFile"):
                    return False, "まだファイル紐づけが完了していません"
            return True, ""
        
        elif current_step == 4:
            # Step4: _aac_output フォルダに十分なファイルがあるか
            output_dir = os.path.join(
                self.current_album_folder,
                self.state.get_path("aacOutput")
            )
            if not os.path.exists(output_dir):
                return False, "AAC出力フォルダが見つかりません"
            
            aac_count = len([f for f in os.listdir(output_dir) if f.lower().endswith('.m4a')])
            track_count = len(self.state.get_tracks())
            
            if aac_count < track_count:
                return False, f"AACファイル数が不足しています ({aac_count}/{track_count})"
            
            return True, ""
        
        elif current_step == 5:
            # Step5: _opus_output フォルダに十分なファイルがあるか
            output_dir = os.path.join(
                self.current_album_folder,
                self.state.get_path("opusOutput")
            )
            if not os.path.exists(output_dir):
                return False, "Opus出力フォルダが見つかりません"
            
            opus_count = len([f for f in os.listdir(output_dir) if f.lower().endswith('.opus')])
            track_count = len(self.state.get_tracks())
            
            if opus_count < track_count:
                return False, f"Opusファイル数が不足しています ({opus_count}/{track_count})"
            
            return True, ""
        
        elif current_step == 6:
            # Step6: _artwork_resized に cover.jpg と cover.webp があるか
            artwork_dir = os.path.join(
                self.current_album_folder,
                self.state.get_path("artworkResized")
            )
            if not os.path.exists(artwork_dir):
                return False, "アートワーク出力フォルダが見つかりません"
            
            jpg_path = os.path.join(artwork_dir, "cover.jpg")
            webp_path = os.path.join(artwork_dir, "cover.webp")
            
            if not os.path.exists(jpg_path) or not os.path.exists(webp_path):
                return False, "リサイズされたアートワークが見つかりません"
            
            return True, ""
        
        elif current_step == 8:
            # Step8: _final_flac フォルダに十分なファイルがあるか
            final_dir = os.path.join(
                self.current_album_folder,
                self.state.get_path("finalFlac")
            )
            if not os.path.exists(final_dir):
                return False, "最終FLAC出力フォルダが見つかりません"
            
            flac_count = len([f for f in os.listdir(final_dir) if f.lower().endswith('.flac')])
            track_count = len(self.state.get_tracks())
            
            if flac_count < track_count:
                return False, f"最終FLACファイル数が不足しています ({flac_count}/{track_count})"
            
            return True, ""
        
        # その他のステップはユーザー判断に任せる
        return True, ""
    
    def get_album_display_name(self) -> str:
        """アルバムの表示名を取得"""
        if not self.state:
            return "Unknown"
        
        step = self.get_current_step()
        status = self.state.get_status()
        album_name = self.state.get_album_name()
        
        status_icon = ""
        if status == "ERROR":
            status_icon = "⚠️ "
        elif status == "COMPLETED":
            status_icon = "✓ "
        
        return f"{status_icon}[Step {step}/10] {album_name}"

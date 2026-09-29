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
        7: "最終転送"
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
        state = StateManager(album_folder)
        if not state.load():
            self.current_album_folder = None
            self.state = None
            return False
        self.current_album_folder = album_folder
        self.state = state
        return True
    
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
            print("[ERROR] advance_step: state が None です")
            return False
        
        current = self.state.get_current_step()
        print(f"[DEBUG] advance_step: 現在のステップ = {current}")
        
        # ステップスキップロジック
        next_step = current + 1
        print(f"[DEBUG] advance_step: 次のステップ = {next_step}")
        
        # 最大ステップチェック（Step 7で完了）
        if next_step > 7:
            print(f"[DEBUG] advance_step: Step 7 完了、COMPLETED 状態へ")
            previous = self.state.get_status()
            if self.state.set_status("COMPLETED"):
                return True
            self.state.state["status"] = previous
            return False
        
        # ステップを進めて保存
        result = self.state.set_current_step(next_step)
        if result:
            print(f"[DEBUG] advance_step: Step {next_step} に進みました（保存完了）")
        else:
            self.state.state["currentStep"] = current
            print(f"[ERROR] advance_step: set_current_step が失敗しました")
        
        return result

    def rollback_step(self) -> bool:
        """戻す先以降の完了フラグを無効化して保存する。"""
        if not self.state or self.get_current_step() <= 2:
            return False
        from copy import deepcopy
        from .utils import sanitize_foldername
        previous = deepcopy(self.state.state)
        target = self.get_current_step() - 1
        moved_paths = None
        if target == 6 and self.current_album_folder:
            album = sanitize_foldername(self.state.get_album_name())
            artist = sanitize_foldername(self.state.get_artist_name())
            final = os.path.join(self.current_album_folder, "_final_flac", artist, album)
            source = os.path.join(self.current_album_folder, "_flac_src", album)
            if os.path.isdir(final):
                if os.path.exists(source):
                    print("[ERROR] ロールバック: 元音源と最終FLACの両方が存在します")
                    return False
                try:
                    os.makedirs(os.path.dirname(source), exist_ok=True)
                    os.rename(final, source)
                    moved_paths = (source, final)
                except OSError as exc:
                    print(f"[ERROR] ロールバック: FLACの復帰に失敗しました: {exc}")
                    return False
        completed = self.state.state.get("completedSteps", {})
        for key in list(completed):
            if any(key.startswith(f"step{step}_") for step in range(target, 8)):
                del completed[key]
        self.state.state.update(currentStep=target, status="WAITING_USER", lastError=None)
        if target == 2:
            self.state.state.setdefault("flags", {})["step2_skipped"] = False
        if self.state.save():
            return True
        self.state.state = previous
        if moved_paths:
            try:
                os.rename(*moved_paths)
            except OSError as exc:
                print(f"[ERROR] ロールバック: FLAC配置の復元に失敗しました: {exc}")
        return False
    
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
            
            aac_count = 0
            for root, _, files in os.walk(output_dir):
                aac_count += len([f for f in files if f.lower().endswith('.m4a')])
            
            expected_files = set()
            for t in self.state.get_tracks():
                final = t.get("finalFile")
                inst = t.get("instrumentalFile")
                if final:
                    expected_files.add(final)
                if inst:
                    expected_files.add(inst)
            track_count = len(expected_files)
            
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
            
            opus_count = 0
            for root, _, files in os.walk(output_dir):
                opus_count += len([f for f in files if f.lower().endswith('.opus')])
            
            expected_files = set()
            for t in self.state.get_tracks():
                final = t.get("finalFile")
                inst = t.get("instrumentalFile")
                if final:
                    expected_files.add(final)
                if inst:
                    expected_files.add(inst)
            track_count = len(expected_files)
            
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
        
        # STEP_NAMESの最大値を使用（動的に取得）
        max_step = max(self.STEP_NAMES.keys())
        return f"{status_icon}[Step {step}/{max_step}] {album_name}"

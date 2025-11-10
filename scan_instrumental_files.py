#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存のインストゥルメンタルファイルをスキャンして state.json を更新するツール
_flac_src フォルダ内の (Inst).flac ファイルを検出し、対応する元トラックに紐づけます。
"""
import os
import json
import sys


def scan_instrumental_files(album_folder):
    """
    アルバムフォルダ内のインストファイルをスキャンして state.json を更新
    
    Args:
        album_folder: アルバムフォルダのパス
    """
    state_path = os.path.join(album_folder, "state.json")
    flac_src_dir = os.path.join(album_folder, "_flac_src")
    
    # state.json の存在確認
    if not os.path.exists(state_path):
        print(f"[ERROR] state.json が見つかりません: {state_path}")
        return False
    
    # _flac_src フォルダの存在確認
    if not os.path.exists(flac_src_dir):
        print(f"[INFO] _flac_src フォルダが見つかりません: {flac_src_dir}")
        return False
    
    # state.json を読み込み
    try:
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except Exception as e:
        print(f"[ERROR] state.json の読み込みに失敗: {e}")
        return False
    
    # _flac_src 内のファイル一覧を取得
    try:
        all_files = [f for f in os.listdir(flac_src_dir) if f.endswith('.flac')]
    except Exception as e:
        print(f"[ERROR] _flac_src フォルダの読み込みに失敗: {e}")
        return False
    
    # (Inst).flac ファイルを抽出
    inst_files = [f for f in all_files if '(Inst)' in f]
    
    if not inst_files:
        print(f"[INFO] インストゥルメンタルファイルが見つかりません")
        return False
    
    print(f"[INFO] {len(inst_files)} 個のインストファイルを検出しました")
    
    # 各インストファイルに対して対応する元トラックを探す
    updated_count = 0
    
    for inst_file in inst_files:
        # インストファイル名から元の曲名を推定
        # 例: "02-虹 (Inst).flac" -> "02-虹"
        song_name = inst_file.replace(' (Inst).flac', '').replace('(Inst).flac', '')
        
        print(f"\n[INFO] 処理中: {inst_file}")
        print(f"  -> 元の曲名: {song_name}")
        
        # 対応する元トラックを探す
        matched_track = None
        
        for track in state.get("tracks", []):
            original_file = track.get("originalFile", "")
            current_file = track.get("currentFile", "")
            
            # ファイル名から拡張子を除去して比較
            orig_base = os.path.splitext(original_file)[0]
            curr_base = os.path.splitext(current_file)[0]
            
            if song_name == orig_base or song_name == curr_base:
                matched_track = track
                break
        
        if matched_track:
            # トラック情報を更新
            track_id = matched_track.get("id")
            print(f"  -> マッチ: {track_id} ({matched_track.get('originalFile')})")
            
            matched_track["instrumentalFile"] = inst_file
            matched_track["hasInstrumental"] = True
            
            updated_count += 1
        else:
            print(f"  -> [WARNING] 対応する元トラックが見つかりません")
    
    # state.json を保存
    if updated_count > 0:
        try:
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print(f"\n[SUCCESS] state.json を更新しました ({updated_count} トラック)")
            return True
        except Exception as e:
            print(f"\n[ERROR] state.json の保存に失敗: {e}")
            return False
    else:
        print(f"\n[INFO] 更新するトラックがありませんでした")
        return False


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使い方: python scan_instrumental_files.py <アルバムフォルダのパス>")
        print("\n例:")
        print('  python scan_instrumental_files.py "./work/THE IDOLM@STER CINDERELLA GIRLS STARLIGHT MASTER 36"')
        sys.exit(1)
    
    album_folder = sys.argv[1]
    
    if not os.path.exists(album_folder):
        print(f"[ERROR] フォルダが見つかりません: {album_folder}")
        sys.exit(1)
    
    print(f"[INFO] アルバムフォルダ: {album_folder}")
    print("[INFO] インストファイルのスキャンを開始...")
    
    success = scan_instrumental_files(album_folder)
    
    if success:
        print("\n✅ 完了しました")
        sys.exit(0)
    else:
        print("\n❌ 処理に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
Demucs処理対象の自動検出ロジック
"""
import re
from typing import Dict

INSTRUMENTAL_FILENAMES = {"no_vocals.wav", "no_vocals.flac", "minus_vocals.wav", "minus_vocals.flac"}


def detect_demucs_targets(track_filenames: list[str], keywords: list[str]) -> Dict[str, bool]:
    """
    全トラックを解析し、各ファイルのDemucs推奨フラグ(True=対象, False=除外)を返す。
    
    Args:
        track_filenames: トラックのファイル名リスト
        keywords: 除外キーワードのリスト
    
    Returns:
        {ファイル名: 対象フラグ} の辞書
    """
    targets = {f: True for f in track_filenames}
    
    if not keywords:
        return targets
    
    # キーワードを正規表現パターンに変換
    pattern_str = "|".join(map(re.escape, keywords))
    # (Off Vocal) 等の表記を捕捉する正規表現
    # 前後に括弧やハイフンがある場合も考慮
    keyword_regex = re.compile(
        rf"(?i)\s*[\[\(\-]?\s*({pattern_str})\s*[\]\)\-]?",
        re.UNICODE
    )
    
    # 1. 明示的なインスト曲を検出
    inst_files = []
    for f in track_filenames:
        # 拡張子を除いたベース名で判定
        base_name = re.sub(r'\.[^.]+$', '', f)
        if keyword_regex.search(base_name):
            targets[f] = False  # インスト曲そのものは除外
            inst_files.append(f)
    
    # 2. インスト曲のペアとなる原曲を検出（簡易実装）
    # 例: "03 Song (Off Vocal).flac" から "Song" を取り出し、"01 Song.flac" を探す
    for inst_f in inst_files:
        base_name = re.sub(r'\.[^.]+$', '', inst_f)
        
        # キーワード部分を除去して原曲名(推定)を作成
        original_name_guess = keyword_regex.sub('', base_name).strip()
        
        # トラック番号パターンを除去 ("01 - Song" -> "Song", "01. Song" -> "Song" など)
        original_name_guess = re.sub(r'^\d+[\s\-\.]*', '', original_name_guess).strip()
        
        if not original_name_guess:
            continue
        
        # 他のトラックで推定原曲名を含むものを探す
        for f in track_filenames:
            if not targets[f] or f == inst_f:
                continue
            
            # 対象ファイルのベース名（トラック番号除去後）
            f_base = re.sub(r'\.[^.]+$', '', f)
            f_base = re.sub(r'^\d+[\s\-\.]*', '', f_base).strip()
            
            # 部分一致チェック（より厳密な判定が必要な場合は調整）
            # 例: "Song" と "Song (Remix)" は別曲なので、完全一致に近い形で判定
            if original_name_guess.lower() == f_base.lower():
                targets[f] = False
                print(f"[INFO] インストペア検出: '{f}' は '{inst_f}' の原曲と判定されました")
            # より緩い判定: 原曲名がファイル名の先頭にある場合
            elif f_base.lower().startswith(original_name_guess.lower()):
                # ただし、原曲名の直後に特殊文字（括弧など）がない場合のみ
                remaining = f_base[len(original_name_guess):].strip()
                if not remaining or remaining[0] in ['(', '[', '-', '~']:
                    targets[f] = False
                    print(f"[INFO] インストペア検出: '{f}' は '{inst_f}' の原曲候補と判定されました")
    
    return targets


def extract_instrumental_files(demucs_folder: str) -> list[tuple[str, str]]:
    """
    Demucs出力フォルダから instrumental 音源ファイルを再帰的に抽出
    
    Args:
        demucs_folder: Demucsの出力フォルダパス (例: htdemucs_ft/ または親フォルダ)
    
    Returns:
        [(曲フォルダパス, インストファイルパス), ...] のリスト
    """
    import os
    
    results = []
    
    if not os.path.exists(demucs_folder):
        return results
    
    # 再帰的にすべてのサブフォルダを走査
    for root, dirs, files in os.walk(demucs_folder):
        dirs[:] = sorted(d for d in dirs if d != "demucs_ignore" and not d.startswith(".demucs-import-"))
        by_name = {name.lower(): name for name in files}
        # 同一曲フォルダに両形式がある場合はFLACを優先する。
        for name in ("no_vocals.flac", "minus_vocals.flac", "no_vocals.wav", "minus_vocals.wav"):
            if name in by_name:
                results.append((root, os.path.join(root, by_name[name])))
                break
                
    return results

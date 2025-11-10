"""
アートワーク関連の処理
"""
import os
import io
import base64
from typing import Optional, Tuple
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggopus import OggOpus


def check_flac_has_artwork(flac_path: str) -> bool:
    """
    FLACファイルにアートワークが埋め込まれているかチェック
    
    Args:
        flac_path: FLACファイルのパス
    
    Returns:
        アートワークが存在する場合 True
    """
    try:
        audio = FLAC(flac_path)
        # FLAC の pictures 属性をチェック
        return len(audio.pictures) > 0
    except Exception as e:
        print(f"[WARNING] {flac_path} のアートワークチェックに失敗: {e}")
        return False


def check_album_has_artwork(album_folder: str) -> bool:
    """アルバム内の FLAC にアートワークがあるかチェック。
    まず `_flac_src` サブフォルダがあれば優先して調べ、無ければルート直下を調べる。
    """
    if not os.path.exists(album_folder):
        return False

    # 優先: サブフォルダ _flac_src
    flac_src = os.path.join(album_folder, "_flac_src")
    candidates_dirs = []
    if os.path.isdir(flac_src):
        candidates_dirs.append(flac_src)
    candidates_dirs.append(album_folder)

    for d in candidates_dirs:
        try:
            for file in os.listdir(d):
                if file.lower().endswith('.flac'):
                    flac_path = os.path.join(d, file)
                    if check_flac_has_artwork(flac_path):
                        return True
        except Exception:
            pass

    return False


def extract_artwork_from_flac(flac_path: str, output_path: str) -> bool:
    """
    FLACファイルからアートワークを抽出
    
    Args:
        flac_path: FLACファイルのパス
        output_path: 出力画像ファイルのパス
    
    Returns:
        抽出成功時 True
    """
    try:
        audio = FLAC(flac_path)
        if not audio.pictures:
            return False
        
        # 最初の画像を抽出
        picture = audio.pictures[0]
        with open(output_path, 'wb') as f:
            f.write(picture.data)
        
        return True
    except Exception as e:
        print(f"[ERROR] アートワーク抽出エラー: {e}")
        return False


def resize_artwork_with_magick(
    magick_path: str,
    input_path: str,
    output_path: str,
    width: int = 600,
    quality: int = 85,
    format: str = 'jpg'
) -> tuple[bool, str]:
    """
    ImageMagick (magick.exe) でアートワークをリサイズ
    
    Args:
        magick_path: magick.exe のパス
        input_path: 入力画像パス
        output_path: 出力画像パス
        width: リサイズ後の幅（高さは自動調整）
        quality: 圧縮品質 (1-100)
        format: 出力フォーマット ('jpg' or 'webp')
    
    Returns:
        (成功フラグ, エラーメッセージ)
    """
    import subprocess
    
    if not os.path.exists(magick_path):
        return False, f"magick.exe が見つかりません: {magick_path}"
    
    if not os.path.exists(input_path):
        return False, f"入力ファイルが見つかりません: {input_path}"
    
    # magick コマンドライン構築
    # magick input.jpg -resize 600x600 -quality 85 output.jpg
    args = [
        input_path,
        "-resize", f"{width}x{width}",
        "-quality", str(quality),
        output_path
    ]
    
    try:
        result = subprocess.run(
            [magick_path] + args,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=60
        )
        
        if result.returncode == 0:
            return True, ""
        else:
            return False, f"magick エラー: {result.stderr}"
    
    except subprocess.TimeoutExpired:
        return False, "タイムアウト: 画像処理に60秒以上かかりました"
    except Exception as e:
        return False, f"実行エラー: {str(e)}"


def find_first_flac_with_artwork(album_folder: str) -> Optional[str]:
    """
    アルバム内で最初にアートワークを持つ FLAC のパスを返す
    _flac_src サブフォルダを優先して探索
    """
    if not os.path.isdir(album_folder):
        return None
    
    # 優先: _flac_src サブフォルダ
    flac_src = os.path.join(album_folder, "_flac_src")
    search_dirs = []
    if os.path.isdir(flac_src):
        search_dirs.append(flac_src)
    search_dirs.append(album_folder)
    
    for search_dir in search_dirs:
        try:
            for name in sorted(os.listdir(search_dir)):
                if not name.lower().endswith(".flac"):
                    continue
                path = os.path.join(search_dir, name)
                if check_flac_has_artwork(path):
                    return path
        except Exception as e:
            print(f"[WARN] find_first_flac_with_artwork: {search_dir} の探索失敗: {e}")
            continue
    
    return None


# FLAC への再埋め込み機能は事故防止のため削除（抽出のみ許可）。


def embed_artwork_to_mp4(mp4_path: str, image_path: str) -> Tuple[bool, str]:
    """
    MP4(M4A) へアートワークを埋め込む（covr 置換）
    """
    try:
        if not os.path.exists(mp4_path):
            return False, f"MP4/M4A が見つかりません: {mp4_path}"
        if not os.path.exists(image_path):
            return False, f"画像が見つかりません: {image_path}"
        with open(image_path, 'rb') as f:
            data = f.read()
        if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
            cover = MP4Cover(data, imageformat=MP4Cover.FORMAT_JPEG)
        elif image_path.lower().endswith('.png'):
            cover = MP4Cover(data, imageformat=MP4Cover.FORMAT_PNG)
        else:
            # webp は iTunes 互換ではないため JPEG 推奨
            cover = MP4Cover(data, imageformat=MP4Cover.FORMAT_JPEG)
        mp4 = MP4(mp4_path)
        mp4["covr"] = [cover]
        mp4.save()
        return True, ""
    except Exception as e:
        return False, str(e)


def embed_artwork_to_opus(opus_path: str, image_path: str) -> Tuple[bool, str]:
    """
    Opus へアートワークを埋め込む（METADATA_BLOCK_PICTURE）。
    注意: 一部プレイヤの互換性に差があるため任意機能。
    """
    try:
        if not os.path.exists(opus_path):
            return False, f"Opus が見つかりません: {opus_path}"
        if not os.path.exists(image_path):
            return False, f"画像が見つかりません: {image_path}"
        # FLAC Picture 構造体を使って base64 化
        pic = Picture()
        with open(image_path, 'rb') as f:
            pic.data = f.read()
        pic.type = 3
        if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
            pic.mime = 'image/jpeg'
        elif image_path.lower().endswith('.webp'):
            pic.mime = 'image/webp'
        else:
            pic.mime = 'image/png'
        b = pic.write()
        encoded = base64.b64encode(b).decode('ascii')
        opus = OggOpus(opus_path)
        opus['metadata_block_picture'] = [encoded]
        opus.save()
        return True, ""
    except Exception as e:
        return False, str(e)


def ensure_artwork_resized_outputs(album_folder: str, magick_path: str, source_image: str, width: int = 600, jpg_q: int = 85, webp_q: int = 85) -> Tuple[bool, str, str]:
    """
    _artwork_resized/cover.jpg, cover.webp を生成（既存なら上書き）
    Returns: (ok, jpg_path, webp_path or err)
    """
    try:
        out_dir = os.path.join(album_folder, "_artwork_resized")
        os.makedirs(out_dir, exist_ok=True)
        jpg_path = os.path.join(out_dir, "cover.jpg")
        webp_path = os.path.join(out_dir, "cover.webp")

        ok1, err1 = resize_artwork_with_magick(magick_path, source_image, jpg_path, width=width, quality=jpg_q, format='jpg')
        if not ok1:
            return False, err1, ""
        # webp
        ok2, err2 = resize_artwork_with_magick(magick_path, source_image, webp_path, width=width, quality=webp_q, format='webp')
        if not ok2:
            return False, err2, ""
        return True, jpg_path, webp_path
    except Exception as e:
        return False, str(e), ""

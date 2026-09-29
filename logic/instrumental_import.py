"""変換・タグ保存が成功したインスト音源だけを公開する。"""
import os
import shutil
import tempfile

from mutagen.flac import FLAC
from .external_tools import ExternalToolRunner


def import_instrumental(source: str, original: str, destination: str,
                        flac_tool: str | None, working_dir: str) -> None:
    """失敗時は既存出力と入力を保持する。Demucs出力は再試行用に残す。"""
    parent = os.path.dirname(os.path.abspath(destination))
    os.makedirs(parent, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=parent, prefix=".demucs-import-") as staging:
        temporary = os.path.join(staging, "instrumental.flac")
        if source.lower().endswith(".wav"):
            if not flac_tool:
                raise ValueError("WAVの変換にはflac.exeが必要です")
            ok, _, error = ExternalToolRunner().run_cli_tool(
                flac_tool, ["-8", "--keep-foreign-metadata", os.path.abspath(source), "-o", temporary], working_dir
            )
            if not ok:
                raise OSError(f"FLAC変換失敗: {error}")
        else:
            shutil.copy2(source, temporary)
        src = FLAC(original)
        dest = FLAC(temporary)
        dest.clear()
        for key, value in (src.tags or {}).items():
            dest[key] = value
        dest.clear_pictures()
        for picture in src.pictures:
            dest.add_picture(picture)
        dest["genre"] = ["Instrumental"]
        dest.save()
        os.replace(temporary, destination)


def save_synced_instrumental(source: str, destination: str, audio: FLAC) -> None:
    """同期タグをコピーへ保存し、成功後に置換する。他音源との衝突は拒否。"""
    same_file = os.path.exists(destination) and os.path.samefile(source, destination)
    if os.path.exists(destination) and not same_file:
        raise FileExistsError(f"同期先に別の音源が存在します: {destination}")
    parent = os.path.dirname(os.path.abspath(destination))
    with tempfile.TemporaryDirectory(dir=parent, prefix=".inst-sync-") as staging:
        temporary = os.path.join(staging, "instrumental.flac")
        shutil.copy2(source, temporary)
        audio.save(temporary)
        if same_file:
            os.replace(temporary, destination)
        else:
            # Windowsのrenameは既存ファイルを置換しない。
            os.rename(temporary, destination)
            os.unlink(source)

"""AAC/Opus 出力の一意な紐づけと、失敗時に既存音源を保持する取り込み。"""
import os
from pathlib import Path
import re
import shutil
import tempfile


def expected_outputs(tracks: list[dict], extension: str) -> list[str]:
    names = {}
    for track in tracks:
        for key in ("finalFile", "instrumentalFile"):
            filename = track.get(key)
            if filename:
                name = Path(filename).stem + extension
                names.setdefault(name.casefold(), name)
    return list(names.values())


def _track_key(name: str):
    match = re.match(r"^(?:Disc\s+(\d+)-)?(\d+)(?=\D|$)", name, re.IGNORECASE)
    if not match:
        return None
    inst = bool(re.search(r"\(inst\)|instrumental|off[ -]?vocal|backing track|karaoke", name, re.I))
    return int(match.group(1)) if match.group(1) else None, int(match.group(2)), inst


def ingest_outputs(source: str, destination: str, tracks: list[dict], extension: str,
                   *, allow_number_match: bool = True) -> tuple[int, list[str]]:
    """全移動先を先に確定し、曖昧な対応や衝突は移動前に拒否する。"""
    expected = expected_outputs(tracks, extension)
    exact = {name.casefold(): name for name in expected}
    numbered = {}
    for name in expected:
        key = _track_key(name)
        if key is not None:
            numbered.setdefault(key, []).append(name)
    plan = []
    errors = []
    destinations = set()
    try:
        sources = sorted(Path(source).iterdir())
    except OSError as exc:
        return 0, [f"取り込み元を読み込めません: {source}: {exc}"]
    for src in sources:
        if not src.is_file() or src.suffix.lower() != extension:
            continue
        name = exact.get(src.name.casefold())
        if name is None and allow_number_match:
            key = _track_key(src.name)
            candidates = numbered.get(key, [])
            if key is not None and key[0] is None:
                candidates = [n for k, names in numbered.items() if k[1:] == key[1:] for n in names]
            if len(candidates) == 1:
                name = candidates[0]
        if name is None:
            errors.append(f"紐づけを確定できません: {src.name}")
            continue
        if name.casefold() in destinations:
            errors.append(f"移動先が重複しています: {name}")
        destinations.add(name.casefold())
        plan.append((src, Path(destination) / name))
    if errors:
        return 0, errors
    try:
        Path(destination).mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return 0, [f"取り込み先を作成できません: {destination}: {exc}"]
    count = 0
    for src, dst in plan:
        temporary = None
        try:
            if dst.exists() and os.path.samefile(src, dst):
                continue
            # 異なるドライブからのコピーでも既存ファイルを先に削除しない。
            with tempfile.NamedTemporaryFile(dir=destination, prefix=".ingest-", delete=False) as f:
                temporary = f.name
            shutil.copy2(src, temporary)
            os.replace(temporary, dst)
            src.unlink()
            count += 1
        except OSError as exc:
            errors.append(f"取り込み失敗: {src.name}: {exc}")
        finally:
            if temporary and os.path.exists(temporary):
                try:
                    os.unlink(temporary)
                except OSError as exc:
                    errors.append(f"一時ファイルの削除失敗: {temporary}: {exc}")
    return count, errors


def missing_outputs(destination: str, tracks: list[dict], extension: str) -> list[str]:
    return [name for name in expected_outputs(tracks, extension)
            if not (Path(destination) / name).is_file()]

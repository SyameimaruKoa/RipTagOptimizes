"""Deprecated stub.

旧ステップ順で存在した Step5ArtworkPanel は現在不要です。
アートワーク処理は step6_artwork.py の Step6ArtworkPanel を使用してください。
このファイルは残存インポート対策のみで、GUIには利用されません。
"""
from PySide6.QtWidgets import QWidget


class Step5ArtworkPanel(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        raise RuntimeError("Step5ArtworkPanel は非推奨です。Step6ArtworkPanel を使用してください。")

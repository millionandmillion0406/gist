# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = [
    "gist", "youtube_transcript", "markdown", "markdown.extensions.fenced_code",
    "markdown.extensions.nl2br", "markdown.extensions.sane_lists",
]

a = Analysis(
    ["gui.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "notebook", "IPython", "funasr", "modelscope",
        "transformers", "sklearn", "cv2", "easyocr", "webview", "clr", "pythonnet", "clr_loader",
        "whisper", "torch", "torchaudio", "scipy", "numpy", "numba", "librosa", "soundfile",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LinkDistill",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    version="version_info.txt",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="LinkDistill",
)

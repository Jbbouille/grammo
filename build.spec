# -*- mode: python ; coding: utf-8 -*-
import os
import sys

icon = "icon.icns" if sys.platform == "darwin" else "icon.ico"

grammalecte_src = os.path.join(os.path.dirname(SPEC), "Grammalecte-fr-v2.3.0")

a = Analysis(
    ["main.py"],
    pathex=[grammalecte_src],
    binaries=[],
    datas=[
        # Inclure tout le dossier grammalecte (modules + données)
        (os.path.join(grammalecte_src, "grammalecte"), "Grammalecte-fr-v2.3.0/grammalecte"),
    ],
    hiddenimports=[
        "grammalecte",
        "grammalecte.fr",
        "grammalecte.graphspell",
        "grammalecte.grammar_checker",
        "grammalecte.text",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="correcteur-grammalecte",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,   # Pas de fenêtre console (app GUI)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

# macOS : créer un .app bundle
app = BUNDLE(
    exe,
    name="Correcteur Grammalecte.app",
    icon=icon,
    bundle_identifier="fr.grammalecte.correcteur",
)

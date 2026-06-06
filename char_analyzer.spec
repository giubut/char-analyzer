# -*- mode: python ; coding: utf-8 -*-
import os

spec_root = os.path.dirname(os.path.abspath(SPECPATH))

a = Analysis(
    ['main.py'],
    pathex=[spec_root],
    binaries=[],
    datas=[],
    hiddenimports=[
        'api_client', 'config', 'text_analyzer', 'scene_selector',
        'agent_simulator', 'debate_engine', 'judge', 'change_analyzer',
        'report_generator', 'overseer', 'pipeline', 'utils',
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
    name='char_analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

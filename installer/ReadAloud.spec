# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

project_dir = os.path.abspath(os.path.join(SPECPATH, '..'))

datas = [
    (os.path.join(project_dir, 'assets'), 'assets'),
]
datas += collect_data_files('kokoro_onnx')
datas += collect_data_files('rapidocr_onnxruntime')
datas += collect_data_files('espeakng_loader')
datas += collect_data_files('_sounddevice_data')

binaries = collect_dynamic_libs('sounddevice')
binaries += collect_dynamic_libs('_sounddevice_data')
binaries += collect_dynamic_libs('onnxruntime')
binaries += collect_dynamic_libs('espeakng_loader')

hiddenimports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'kokoro_onnx',
    'rapidocr_onnxruntime',
    'sounddevice',
    '_sounddevice_data',
    'pynput',
    'pynput.keyboard._win32',
    'pynput.mouse._win32',
    'pyperclip',
    'pyttsx3',
    'pyttsx3.drivers',
    'pyttsx3.drivers.sapi5',
    'comtypes',
    'comtypes.stream',
    'numpy',
    'PIL',
    'PIL.Image',
]
hiddenimports += collect_submodules('kokoro_onnx')
hiddenimports += collect_submodules('rapidocr_onnxruntime')

a = Analysis(
    [os.path.join(project_dir, 'src', 'main.py')],
    pathex=[project_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'torchaudio',
        'torchvision',
        'triton',
        'scipy',
        'matplotlib',
        'pandas',
        'notebook',
        'IPython',
        'jupyter',
        'sympy',
        'sklearn',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ReadAloudAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, 'assets', 'icon.ico'),
)


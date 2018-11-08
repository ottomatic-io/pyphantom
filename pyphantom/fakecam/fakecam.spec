# -*- mode: python -*-

block_cipher = None

added_files = [('*.kv', ''), ('*.png', ''), ('takes', 'takes'), ]

a = Analysis(['fakecam_gui.py'],
             pathex=['/Users/ben/Projects/PHANTOMfuse/fakecam'],
             binaries=None,
             datas=added_files,
             hiddenimports=['uuid'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['enchant', '_tkinter', 'Tkinter', 'twisted', 'cv2',
                       'gi.repository.Gst', 'gi.repository.GLib',
                       'gi.repository.GObject', 'numpy'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='FakeCam',
          debug=False,
          strip=False,
          upx=True,
          console=False)
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='FakeCam')
app = BUNDLE(coll,
             name='FakeCam.app',
             icon='fakecam/fakecam.icns',
             bundle_identifier=None,
             info_plist={
                 'NSHighResolutionCapable': 'True',
                 'NSHumanReadableCopyright':
                 'Copyright 2016, Ben Hagen &lt;ben@kamerawerk.ch&gt;, '
                 'All Rights Reserved',
             })

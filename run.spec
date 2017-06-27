# -*- mode: python -*-

import os
import pymunk

block_cipher = None

chipmunk_dll = os.path.join(os.path.dirname(pymunk.__file__), 'chipmunk.dll')

extra_libs = [(os.path.basename(chipmunk_dll), chipmunk_dll, 'DATA')]

res = Tree("res", prefix="res")

a = Analysis(['run.py'],
             pathex=['C:\\Users\\Nathan\\Documents\\Projects\\space_game'],
             binaries=[],
             datas=[],
             hiddenimports=["src.pygame_opengl_renderer", "src.pygame_renderer"],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
			 
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
			 
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='run',
          debug=False,
          strip=False,
          upx=True,
          console=False )
		  
coll = COLLECT(exe,
               a.binaries + extra_libs,
               a.zipfiles,
               a.datas + res,
               strip=False,
               upx=True,
               name='run')

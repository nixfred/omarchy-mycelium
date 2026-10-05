"""Private display only; never maps the native fixture over your Wayland desktop."""
import os,subprocess,tempfile
from pathlib import Path
from runtime_paths import omarchy_path,private_x_display
with tempfile.TemporaryDirectory(prefix='mycelium-native-display-') as tmp:
 runtime=Path(tmp)/'runtime';runtime.mkdir(mode=0o700)
 with private_x_display('1920x1080') as display:
  e={**os.environ,'DISPLAY':display,'QT_QPA_PLATFORM':'xcb','XDG_RUNTIME_DIR':str(runtime),'XDG_CACHE_HOME':tmp+'/cache','OMARCHY_PATH':str(omarchy_path()),'MYCELIUM_ISOLATED_X11':'1'}
  p=subprocess.run(['python3',str(Path(__file__).with_name('native.py'))],env=e,text=True,capture_output=True,timeout=22)
  print(p.stdout,p.stderr);raise SystemExit(p.returncode)

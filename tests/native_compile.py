from runtime_paths import omarchy_path,private_x_display
"""Real Wayland types load hidden, without mapping test surfaces or input."""
import os,json,shutil,subprocess,tempfile
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];ROOT=Path(os.environ.get('MYCELIUM_CANDIDATE',str(BASE))).resolve();module=next((m for m in ('v4','v3','v2') if (ROOT/m).exists()),'v1')
with tempfile.TemporaryDirectory(prefix='mycelium-hidden-') as tmp:
 work=Path(tmp);shell=omarchy_path()/'shell'
 for name in ('Commons','Ui','services'):(work/name).symlink_to(shell/name,target_is_directory=True)
 for f in ROOT.glob('*.py'):shutil.copy2(f,work/f.name)
 for f in ROOT.glob('*.js'):shutil.copy2(f,work/f.name)
 shutil.copytree(ROOT/module,work/module)
 shutil.copy2(ROOT/'Widget.qml' if (ROOT/'Widget.qml').exists() else ROOT/module/'Widget.qml',work/'Widget.qml')
 (work/'shell.qml').write_text('''import QtQuick
import Quickshell
import "v1" as V1
ShellRoot {
 V1.Service {id:svc;testMode:true}
 V1.Trace {id:trace;controllerOverride:svc}
 V1.Network {id:network;controller:svc;screenName:"hidden";width:1920;height:1080;visible:false;renderingEnabled:false}
 Widget {visible:false}
 Timer {interval:600;running:true;onTriggered:{if(trace.opened||network.motion)throw new Error("Hidden fixture became interactive");console.log("PASS_REAL_WAYLAND_HIDDEN_COMPILE");Qt.quit()}}
}'''.replace('import "v1"','import "'+module+'"'))
 env={**os.environ,'XDG_RUNTIME_DIR':os.environ.get('XDG_RUNTIME_DIR',str(Path('/run/user')/str(os.getuid()))),'WAYLAND_DISPLAY':os.environ.get('WAYLAND_DISPLAY','wayland-0'),'QT_QPA_PLATFORM':'wayland'}
 p=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],env=env,text=True,capture_output=True,timeout=8)
 log=p.stdout+p.stderr;out=Path(os.environ.get('MYCELIUM_EVIDENCE_DIR',str(BASE/'local-evidence/native')));out.mkdir(parents=True,exist_ok=True);(out/'native-wayland-hidden.log').write_text(log);print(log)
 assert p.returncode==0 and 'PASS_REAL_WAYLAND_HIDDEN_COMPILE' in log
 assert not any(s in log for s in ['WARN scene','ERROR','ReferenceError','TypeError','Unable to assign']),log

"""Temporary native fixture: no content capture, no application focus or config writes."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import re
BASE=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('MYCELIUM_CANDIDATE',str(BASE))).resolve()
MODULE=next((m for m in ('v3','v2') if (ROOT/m).exists()),'v1')
OUT=Path(os.environ.get('MYCELIUM_EVIDENCE_DIR',str(BASE/'local-evidence/native')));OUT.mkdir(parents=True,exist_ok=True);(OUT/'frames').mkdir(exist_ok=True)
for old_frame in (OUT/'frames').glob('frame-*.png'):old_frame.unlink()
SHELL=Path(os.environ['OMARCHY_PATH'])/'shell'
with tempfile.TemporaryDirectory(prefix='mycelium-native-') as tmp:
  work=Path(tmp)
  for name in ('Commons','Ui','services'):(work/name).symlink_to(SHELL/name,target_is_directory=True)
  for p in list(ROOT.glob('*.qml'))+list(ROOT.glob('*.js'))+[ROOT/'bridge.py']:shutil.copy2(p,work/p.name)
  shutil.copytree(ROOT/MODULE,work/'v1')
  if MODULE!='v1':shutil.copy2(ROOT/MODULE/'Widget.qml',work/'Widget.qml')
  isolated_x11=os.environ.get('MYCELIUM_ISOLATED_X11')=='1'
  if isolated_x11:
    # Only remove Wayland attached properties in disposable test copies; test
    # the unchanged production Items/Shapes/controls on an isolated X display.
    for q in (work/'v1').glob('*.qml'):
      q.write_text(re.sub(r'^\s*WlrLayershell\.[^\n]+\n','\n',q.read_text(),flags=re.M))
  (work/'shell.qml').write_text('''import QtQuick
import Quickshell
import "v1" as V1
import Quickshell.Wayland
import qs.Commons
import QtTest
ShellRoot {
  V1.Service {id:svc;testMode:true;onFocusRequested:id => {lastRequest=id};onWorkspaceRequested:id => {lastWorkspace=id}}
  property string lastRequest:""
  property int lastWorkspace:0
  TestCase {id:input;name:"TraceInput";when:false}
  V1.Trace {id:trace;controllerOverride:svc}
  Widget {visible:false}
  PanelWindow {
    id:win;implicitWidth:1200;implicitHeight:800;color:"transparent"
    exclusionMode:ExclusionMode.Ignore;WlrLayershell.keyboardFocus:WlrKeyboardFocus.None;mask:Region {}
    Rectangle {
      id:scene;anchors.fill:parent;color:"#080e16"
      Rectangle {anchors.fill:parent;opacity:0.38;gradient:Gradient {GradientStop {position:0;color:"#122e39"}GradientStop {position:1;color:"#080b13"}}}
      Repeater {model:base.windows.filter(function(w){return w.workspace===1})
        delegate:Rectangle {required property var modelData;x:modelData.x;y:modelData.y;width:modelData.w;height:modelData.h;color:"#111b25";radius:9;border.color:"#283341";border.width:1
          Text {x:20;y:20;text:modelData.app.toUpperCase();font.family:Style.font.family;font.pixelSize:12;color:"#5d7682";font.letterSpacing:3}
          Rectangle {x:20;y:56;width:parent.width-40;height:1;color:"#24343f"}
          Text {x:20;y:80;text:"Native fixture · geometry only";width:parent.width-40;elide:Text.ElideRight;font.family:Style.font.family;font.pixelSize:11;color:"#3c5761"}
        }
      }
      V1.Network {id:network;anchors.fill:parent;controller:svc;screenName:"fixture";traceMode:true}
      Text {x:42;y:52;text:"MYCELIUM";font.family:Style.font.family;font.pixelSize:25;font.letterSpacing:6;color:"#b7ede5"}
      Text {x:44;y:92;text:"THE SPACE BETWEEN YOUR WINDOWS IS ALIVE";font.family:Style.font.family;font.pixelSize:10;font.letterSpacing:2;color:"#497b84"}
      Text {x:42;y:height-75;text:"Observed focus paths / real window groups / stationary attention knots";font.family:Style.font.family;font.pixelSize:10;color:"#789593"}
    }
  }
  Component.onCompleted: {
    var component=Qt.createComponent("v1/Network.qml")
    if(component.status!==Component.Ready)throw new Error(component.errorString())
    var cold=component.createObject(win.contentItem,{controller:svc,screenName:"fixture",renderingEnabled:false})
    if(!cold)throw new Error("Cold network creation failed")
    cold.destroy()
    console.log("PASS_COLD_COMPONENT_CREATION")
  }
  property int captureFrame:0
  Timer {interval:80;repeat:true;running:step<9||(step>=15&&step<21);onTriggered:{captureFrame++;scene.grabToImage(function(result){result.saveToFile(OUT+"/frames/frame-"+String(captureFrame).padStart(3,"0")+".png")})}}
  property int step:0
  property var base:({"settings": {"seeds": [78351], "paused": false, "reducedMotion": false}, "monitors": [{"name": "fixture", "id": 0, "x": 0, "y": 0, "workspace": 1}], "workspaces": [{"id": 1, "name": "1"}, {"id": 2, "name": "2"}, {"id": 3, "name": "3"}, {"id": 4, "name": "4"}, {"id": 7, "name": "7"}, {"id": 10, "name": "10"}], "windows": [{"id": "0x1", "x": 48, "y": 180, "w": 235, "h": 205, "monitor": 0, "workspace": 1, "app": "com.mitchellh.ghostty", "group": ["0x7"], "urgent": true}, {"id": "0x2", "x": 350, "y": 155, "w": 240, "h": 210, "monitor": 0, "workspace": 1, "app": "google-chrome", "group": [], "urgent": false}, {"id": "0x3", "x": 650, "y": 170, "w": 220, "h": 200, "monitor": 0, "workspace": 1, "app": "t3code", "group": [], "urgent": false}, {"id": "0x4", "x": 940, "y": 190, "w": 220, "h": 220, "monitor": 0, "workspace": 1, "app": "obsidian", "group": [], "urgent": false}, {"id": "0x5", "x": 70, "y": 490, "w": 220, "h": 185, "monitor": 0, "workspace": 1, "app": "org.gnome.Nautilus", "group": [], "urgent": false}, {"id": "0x6", "x": 380, "y": 490, "w": 220, "h": 170, "monitor": 0, "workspace": 1, "app": "spotify", "group": [], "urgent": false}, {"id": "0x7", "x": 660, "y": 475, "w": 215, "h": 220, "monitor": 0, "workspace": 1, "app": "com.mitchellh.ghostty", "group": ["0x1"], "urgent": false}, {"id": "0x8", "x": 950, "y": 510, "w": 215, "h": 170, "monitor": 0, "workspace": 1, "app": "chromium", "group": [], "urgent": false}], "focus": "0x1"})
  Timer {interval:350;repeat:true;running:true;onTriggered:{
    step++
    if(step===1)svc.ingest(JSON.stringify(base))
    if(step===3){base.focus="0x2";svc.ingest(JSON.stringify(base))}
    if(step===4){base.focus="0x7";svc.ingest(JSON.stringify(base))}
    if(step===5){var dot=input.findChild(network,"focusPulse");if(!dot||!dot.visible)throw new Error("Real focus pulse invisible");var before=svc.pulseTo;svc.ingest(JSON.stringify(base));if(svc.pulseTo!==before||!dot.visible)throw new Error("Unchanged frame cancelled focus pulse");console.log("PASS_EVENT_PULSE_DUPLICATE_FRAME")}
    if(step===5)scene.grabToImage(function(result){result.saveToFile(OUT+"/native-trace.png")})
    if(step===6){network.traceMode=false;svc.setPreference("reducedMotion",true)}
    if(step===8)scene.grabToImage(function(result){result.saveToFile(OUT+"/native-ambient.png")})
    if(step===9){if(network.breath!==0)throw new Error("Still motion did not settle");if(network.motion)throw new Error("Reduced motion still animates");svc.setPreference("paused",true)}
    if(step===10){if(svc.animating)throw new Error("Paused still animates");console.log("PASS_NATIVE "+JSON.stringify({nodes:network.graph.nodes.length,paths:network.graph.paths.length,edges:svc.edges.length,paused:svc.paused,still:svc.reducedMotion}));base.monitors[0].name=Quickshell.screens[0].name;svc.ingest(JSON.stringify(base));trace.open("")}
    if(step===11)console.log("TRACE_GEOMETRY "+JSON.stringify(trace.windows.map(function(w){return {width:w.width,height:w.height,visible:w.visible,name:w.screen.name}})))
    if(step===11){
      console.log("ICON_LOOKUP "+JSON.stringify({apps:DesktopEntries.applications.values.length,id:trace.iconFor("com.mitchellh.ghostty"),chrome:trace.iconFor("google-chrome")}))
      var item=input.findChild(trace.windows[0].contentItem,"traceScene")
      var fixture=Qt.createQmlObject('import QtQuick; Item {property var windows:[];anchors.fill:parent;z:-1; Rectangle {anchors.fill:parent;color:"#080e16"} Repeater {model:parent.windows;delegate:Rectangle {required property var modelData;x:modelData.x;y:modelData.y;width:modelData.w;height:modelData.h;radius:9;color:"#111b25";border.color:"#283341";Text {x:20;y:20;width:parent.width-40;elide:Text.ElideRight;text:modelData.app;font.pixelSize:11;color:"#536674"}}}}',item,"FixtureBackground")
      fixture.windows=base.windows
    }
    if(step===12)trace.capture(OUT+"/native-controls.png",Quickshell.screens[0].name)
    if(step===13){var appCard=input.findChild(trace.windows[0].contentItem,"window-0x1");if(!appCard)throw new Error("Actual app card missing");input.mouseClick(appCard,appCard.width/2,appCard.height/2,Qt.LeftButton);if(lastRequest!=="0x1"||trace.opened)throw new Error("Trace click failed "+lastRequest);console.log("PASS_TRACE_CLICK "+lastRequest);trace.open("")}
    if(step===14){input.mouseClick(trace.windows[0].contentItem,50,trace.windows[0].height-22,Qt.LeftButton);if(lastWorkspace!==2||trace.opened)throw new Error("Workspace portal click failed");console.log("PASS_PORTAL_CLICK "+lastWorkspace)}
    if(step===15){base.monitors[0].name="fixture";svc.setPreference("paused",false);svc.setPreference("reducedMotion",false);base.windows[5].workspace=2;svc.ingest(JSON.stringify(base));if(!network.graph.paths.some(function(p){return p.kind==="move"}))throw new Error("Departure path missing")}
    if(step===16)scene.grabToImage(function(result){result.saveToFile(OUT+"/native-workspace-departure.png")})
    if(step===18){base.windows=base.windows.filter(function(w){return w.id!=="0x4"});svc.ingest(JSON.stringify(base));lastRequest="";svc.focusWindow("0x4");svc.focusWindow("0xBAD;exec");if(lastRequest!=="")throw new Error("Stale focus dispatched");lastWorkspace=0;svc.focusWorkspace(999);if(lastWorkspace!==0)throw new Error("Stale workspace dispatched");if(svc.edges.some(function(e){return e.a==="0x4"||e.b==="0x4"}))throw new Error("Stale edges retained");console.log("PASS_STALE_NAVIGATION")}
    if(step===19)scene.grabToImage(function(result){result.saveToFile(OUT+"/native-close-retraction.png")})
    if(step===20){base.windows[0].urgent=false;svc.ingest(JSON.stringify(base));if(network.graph.nodes.some(function(n){return n.urgent}))throw new Error("Urgency did not clear")}
    if(step===21){base.windows[0].fullscreen=true;svc.ingest(JSON.stringify(base));if(network.motion)throw new Error("Fullscreen animation");base.monitors[0].off=true;svc.ingest(JSON.stringify(base));if(network.motion)throw new Error("Off-screen animation");base.windows[0].fullscreen=false;base.monitors[0].off=false;svc.ingest(JSON.stringify(base));network.renderingEnabled=false;if(network.motion)throw new Error("Disabled renderer animation");network.renderingEnabled=true;network.visible=false;if(network.motion)throw new Error("Hidden renderer animation");svc.markUnavailable();if(svc.edges.length||svc.previous!==null||svc.previousFocus!==""||svc.pulseFrom!==""||svc.animating)throw new Error("Stale outage state");console.log("PASS_MOVE_CLOSE_URGENCY_FULLSCREEN_OFF");console.log("PASS_RENDER_GATES_OUTAGE_RESET")}
    if(step===22){base.monitors[0].name=Quickshell.screens[0].name;base.focus="0x1";base.windows=base.windows.slice(0,3).map(function(w){return Object.assign({},w,{x:9,y:44,w:trace.windows[0].width-18,h:trace.windows[0].height-53})});svc.ingest(JSON.stringify(base));trace.open("")}
    if(step===23){if(!trace.windows[0].stackedCards)throw new Error("Overlapping apps did not enter scrollable card layout");trace.capture(OUT+"/native-overlap-cards.png",Quickshell.screens[0].name)}
    if(step===24){var deck=input.findChild(trace.windows[0].contentItem,"appDeck");input.mouseClick(deck,deck.width-4,deck.height/2,Qt.LeftButton);if(trace.opened)throw new Error("Blank card-deck click failed to dismiss Trace");console.log("PASS_BLANK_DECK_DISMISS");trace.open("");for(var i=0;i<base.windows.length;i++){var c=input.findChild(trace.windows[0].contentItem,"window-"+base.windows[i].id);if(!c)throw new Error("Missing overlap card");lastRequest="";input.mouseClick(c,c.width/2,c.height/2,Qt.LeftButton);if(lastRequest!==base.windows[i].id||trace.opened)throw new Error("Overlap app unreachable "+base.windows[i].id);trace.open("")};console.log("PASS_OVERLAP_CARD_CLICK_ALL "+base.windows.length)}
    if(step===25){trace.close();Qt.quit()}
  }}
}'''.replace('OUT+',json.dumps(str(OUT))+'+'))
  if isolated_x11:
    q=work/'shell.qml';q.write_text(re.sub(r'WlrLayershell.keyboardFocus:WlrKeyboardFocus.None;','',q.read_text()))
  try:
    result=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],capture_output=True,text=True,timeout=15)
  except subprocess.TimeoutExpired as e:
    log=(e.stdout or b"").decode()+(e.stderr or b"").decode()
    (OUT/"native.log").write_text(log)
    print(log)
    raise
  log=result.stdout+result.stderr;(OUT/'native.log').write_text(log)
  print(log)
  assert result.returncode==0 and 'PASS_NATIVE' in log and 'PASS_TRACE_CLICK' in log and 'PASS_PORTAL_CLICK' in log and 'PASS_MOVE_CLOSE_URGENCY_FULLSCREEN_OFF' in log and 'PASS_STALE_NAVIGATION' in log and 'PASS_RENDER_GATES_OUTAGE_RESET' in log and 'PASS_OVERLAP_CARD_CLICK_ALL' in log,log
  for forbidden in ('Error:', 'ERROR:','ReferenceError','TypeError','Unable to assign','Cannot assign','is not a type','WARN scene' ):
    assert forbidden not in log,log
  for image in ('native-trace.png','native-ambient.png','native-controls.png','native-workspace-departure.png','native-close-retraction.png'):assert (OUT/image).stat().st_size>1000

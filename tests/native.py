"""Native v4 fixture: real tiling geometry, no content capture, no desktop input.

Renders the production Network and Trace on a private display with synthetic
windows laid out the way Hyprland tiles them (zero gaps, 9/12 px gaps, one
window, a floating window), then checks pixels: roots must be visible in the
seams and must not change a single pixel inside any window.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from PIL import Image, ImageChops

BASE=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('MYCELIUM_CANDIDATE',str(BASE))).resolve()
OUT=Path(os.environ.get('MYCELIUM_EVIDENCE_DIR',str(BASE/'local-evidence/native')));OUT.mkdir(parents=True,exist_ok=True)
SHELL=Path(os.environ['OMARCHY_PATH'])/'shell'
QML=r'''import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons
import QtTest
import "v4" as V4
ShellRoot {
  id:shellRoot
  V4.Service {id:svc;testMode:true;onFocusRequested:id => {lastRequest=id};onWorkspaceRequested:id => {lastWorkspace=id}}
  property string lastRequest:""
  property int lastWorkspace:0
  property string screenName:Quickshell.screens[0].name
  property var layoutWindows:[]
  TestCase {id:input;name:"MyceliumV4";when:false}
  V4.Trace {id:trace;controllerOverride:svc}
  Widget {id:stem;visible:false}
  function layout(kind) {
    var W=1920,H=1080,top=35,o=9,i=12,list=[]
    if(kind==="zero"){o=1;i=2}
    var y0=top+o,h=H-top-2*o
    if(kind==="single")return [{id:"0x1",app:"kitty",x:o,y:y0,w:W-2*o,h:h}]
    if(kind==="columns"){var cw=Math.floor((W-2*o-2*i)/3);return [0,1,2].map(function(k){return {id:"0x"+(k+1),app:["kitty","brave-browser","obsidian"][k],x:o+k*(cw+i),y:y0,w:cw,h:h}})}
    var left=Math.floor((W-2*o-i)/2),half=Math.floor((h-i)/2)
    list=[{id:"0x1",app:"kitty",x:o,y:y0,w:left,h:h},{id:"0x2",app:"brave-browser",x:o+left+i,y:y0,w:W-2*o-i-left,h:half},{id:"0x3",app:"obsidian",x:o+left+i,y:y0+half+i,w:W-2*o-i-left,h:h-half-i}]
    if(kind==="floating")list.push({id:"0x9",app:"org.gnome.Nautilus",x:700,y:320,w:520,h:380,floating:true})
    return list
  }
  function frameFor(kind,focus,extra) {
    var wins=layout(kind).map(function(w){return Object.assign({monitor:0,workspace:1,urgent:false,group:[],floating:false,fullscreen:false},w)})
    var f={settings:{seeds:[78351],paused:false,reducedMotion:false},focus:focus||"0x1",
      monitors:[{name:screenName,id:0,x:0,y:0,width:1920,height:1080,workspace:1,focused:true,reserved:[0,35,0,0],off:false}],
      workspaces:[{id:1,name:"1",monitor:0},{id:2,name:"2",monitor:0}],windows:wins}
    if(extra)extra(f)
    layoutWindows=f.windows.filter(function(w){return w.workspace===1})
    console.log("LAYOUT "+kind+" "+JSON.stringify(layoutWindows))
    return f
  }
  property var current:null
  function show(kind,focus,extra){current=frameFor(kind,focus,extra);svc.ingest(JSON.stringify(current))}
  function grab(name){scene.grabToImage(function(r){r.saveToFile(OUT+"/"+name+".png")})}
  property bool failed:false
  function fail(message){if(!failed){failed=true;console.log("TEST_FAILURE "+message);Qt.quit()}throw new Error(String(message))}
  PanelWindow {
    id:win;implicitWidth:1920;implicitHeight:1080;color:"transparent"
    exclusionMode:ExclusionMode.Ignore;WlrLayershell.keyboardFocus:WlrKeyboardFocus.None;mask:Region {}
    Item {
      id:scene;anchors.fill:parent
      Rectangle {anchors.fill:parent;gradient:Gradient {GradientStop {position:0;color:"#16303a"}GradientStop {position:1;color:"#0a0d16"}}}
      Rectangle {width:parent.width;height:35;color:"#0d1219"}
      Repeater {
        model:shellRoot.layoutWindows
        delegate:Item {
          required property var modelData
          x:modelData.x-1;y:modelData.y-1;width:modelData.w+2;height:modelData.h+2
          Rectangle {anchors.fill:parent;color:modelData.floating?"#5a6a7c":"#34404e"}
          Rectangle {
            x:1;y:1;width:parent.width-2;height:parent.height-2;color:modelData.floating?"#1d2733":"#141b24"
            Text {x:18;y:16;text:modelData.app.toUpperCase();font.family:Style.font.family;font.pixelSize:12;font.letterSpacing:3;color:"#5d7682"}
            Repeater {model:8;delegate:Rectangle {required property int index;x:18;y:52+index*22;width:Math.max(0,parent.width*(0.35+((index*37)%40)/100)-36);height:6;radius:3;color:"#1f2a36"}}
          }
        }
      }
      V4.Network {id:network;anchors.fill:parent;controller:svc;screenName:shellRoot.screenName}
    }
  }
  Component.onCompleted: {
    var component=Qt.createComponent("v4/Network.qml")
    if(component.status!==Component.Ready)throw new Error(component.errorString())
    var cold=component.createObject(win.contentItem,{controller:svc,screenName:"fixture",renderingEnabled:false})
    if(!cold)throw new Error("Cold network creation failed")
    cold.destroy()
    console.log("PASS_COLD_COMPONENT_CREATION")
  }
  property int step:0
  Timer {interval:150;repeat:true;running:!failed;onTriggered:{
    try {
    step++
    // 1. Static seams in Still mode: reference without roots, then with roots.
    if(step===1){svc.setPreference("reducedMotion",true);show("gaps")}
    if(step===6){network.visible=false}
    if(step===7)grab("ref-gaps")
    if(step===9){network.visible=true}
    if(step===10){grab("net-gaps");var g=network.graph;if(g.frames.length!==3||!g.focus||!g.svg||g.junctions.length<1)fail("gaps seams "+JSON.stringify({f:g.frames.length,j:g.junctions.length}));console.log("PASS_SEAMS_GAPS "+JSON.stringify({edges:g.edges.length,junctions:g.junctions.length,minInset:g.minInset}))}
    if(step===12)show("zero")
    if(step===17){network.visible=false}
    if(step===18)grab("ref-zero")
    if(step===20){network.visible=true}
    if(step===21){grab("net-zero");var z=network.graph;if(!network.tight||z.frames.length!==3||!z.focus)fail("zero seams");console.log("PASS_SEAMS_ZERO "+JSON.stringify({edges:z.edges.length,minInset:z.minInset}))}
    if(step===23)show("single")
    if(step===28){network.visible=false}
    if(step===29)grab("ref-single")
    if(step===31){network.visible=true}
    if(step===32){grab("net-single");var s=network.graph;if(s.frames.length!==1||s.edges.length!==4)fail("single frame "+s.edges.length);console.log("PASS_SEAMS_SINGLE")}
    if(step===34)show("floating")
    if(step===39){network.visible=false}
    if(step===40)grab("ref-floating")
    if(step===42){network.visible=true}
    if(step===43){grab("net-floating");if(network.graph.frames.length!==3||network.graph.occluders.length!==1)fail("floating occluder");console.log("PASS_FLOATING_OCCLUDER")}
    // 2. Motion: growth on adjacent focus, spark between windows that do not touch.
    if(step===45){svc.setPreference("reducedMotion",false);show("gaps","0x1")}
    if(step===50){show("gaps","0x2")}
    if(step===51){if(!(network.growth<1)||!network.focusPath)fail("focus growth "+network.growth);console.log("PASS_FOCUS_GROWTH "+network.growth.toFixed(2))}
    if(step===53)grab("native-growth")
    if(step===56)show("columns","0x1")
    if(step===62){show("columns","0x3")}
    if(step===63){var dot=input.findChild(network,"focusSpark");if(!network.graph.travel.length||!dot||!dot.visible)fail("spark "+network.graph.travel.length);console.log("PASS_FOCUS_SPARK "+network.graph.travel.length)}
    if(step===72){if(network.growth<0.999)fail("growth did not finish");console.log("PASS_MOTION_SETTLES")}
    // 3. Attention: amber seams, one pulse only, amber stem dot.
    if(step===74){show("gaps","0x1",function(f){f.windows[2].urgent=true})}
    if(step===79){if(network.graph.urgent.length!==1||!network.breathing||!svc.anyUrgent)fail("urgent");show("gaps","0x1",function(f){f.windows[1].urgent=true;f.windows[2].urgent=true})}
    if(step===84){var roots=[];for(var k=0;k<network.children.length;k++)if(network.children[k].objectName==="urgentRoot")roots.push(network.children[k]);if(roots.length!==2)fail("urgent roots "+roots.length);if(Math.abs(roots[1].opacity-0.9*network.presence)>0.001)fail("second urgent pulses");console.log("PASS_URGENT_ONE_PULSE")}
    // 4. Layout change hides seams, then regrows them once stable.
    if(step===86){show("columns","0x1")}
    if(step===87){if(network.presence!==0)fail("stale seams visible during layout change "+network.presence)}
    if(step===94){if(network.presence<0.999)fail("seams did not regrow "+network.presence);console.log("PASS_LAYOUT_REGROW")}
    // README still: seams with focus and one urgent window, Still mode.
    if(step===96){svc.setPreference("reducedMotion",true);show("gaps","0x1",function(f){f.windows[2].urgent=true})}
    if(step===101)grab("native-seams")
    // 5. Gates and outage.
    if(step===103){
      if(network.motion)fail("Still animates")
      svc.setPreference("reducedMotion",false);svc.setPreference("paused",true);if(svc.animating)fail("Paused animates");svc.setPreference("paused",false)
      show("gaps","0x1",function(f){f.windows[0].fullscreen=true});if(network.motion||!network.graph.fullscreen)fail("fullscreen animates")
      show("gaps","0x1",function(f){f.monitors[0].off=true});if(network.motion)fail("off output animates")
      show("gaps","0x2");network.renderingEnabled=false;if(network.motion)fail("disabled renderer animates");network.renderingEnabled=true
      network.visible=false;if(network.motion)fail("hidden renderer animates");network.visible=true
      svc.markUnavailable();if(svc.hops.length||svc.pulseFrom!==""||svc.pulseTo!==""||svc.animating)fail("stale outage state")
      console.log("PASS_RENDER_GATES_OUTAGE_RESET")
    }
    // 6. Trace: every workspace, observed hops, real pointer input.
    if(step===105){
      var hopsFrame=function(ws,focus){
        var f=frameFor("gaps",focus,function(f){
          f.workspaces=[{id:1,name:"1",monitor:0},{id:2,name:"2",monitor:0},{id:3,name:"3",monitor:0},{id:4,name:"4",monitor:0}]
          f.windows.push({id:"0x21",app:"brave-browser",x:9,y:44,w:1902,h:1027,monitor:0,workspace:2,urgent:false,group:[],floating:false,fullscreen:false})
          f.windows.push({id:"0x31",app:"kitty",x:9,y:44,w:945,h:1027,monitor:0,workspace:3,urgent:false,group:[],floating:false,fullscreen:false})
          f.windows.push({id:"0x32",app:"spotify",x:966,y:44,w:945,h:1027,monitor:0,workspace:3,urgent:true,group:[],floating:false,fullscreen:false})
          f.windows.push({id:"0x41",app:"org.gnome.Nautilus",x:9,y:44,w:1902,h:1027,monitor:0,workspace:4,urgent:false,group:[],floating:false,fullscreen:false})
          f.monitors[0].workspace=ws
        })
        f.focus=focus;return f
      };
      [[1,"0x1"],[2,"0x21"],[4,"0x41"],[2,"0x21"],[1,"0x2"]].forEach(function(p){current=hopsFrame(p[0],p[1]);svc.ingest(JSON.stringify(current))})
      if(svc.hops.length!==4)fail("hops "+svc.hops.length)
      trace.open("")
    }
    if(step===107){
      var item=input.findChild(trace.windows[0].contentItem,"traceScene")
      var fixture=Qt.createQmlObject('import QtQuick; Rectangle {anchors.fill:parent;z:-1;gradient:Gradient {GradientStop {position:0;color:"#16303a"}GradientStop {position:1;color:"#0a0d16"}}}',item,"FixtureBackground")
      var forest=trace.windows[0].forest
      if(forest.tiles.length!==4||forest.roots.length<2)fail("forest "+JSON.stringify({tiles:forest.tiles.length,roots:forest.roots.length}))
      console.log("PASS_TRACE_FOREST "+JSON.stringify({tiles:forest.tiles.length,roots:forest.roots.length,pages:forest.pages}))
    }
    if(step===109)trace.capture(OUT+"/native-trace.png",screenName)
    if(step===111){var mini=input.findChild(trace.windows[0].contentItem,"window-0x31");if(!mini)fail("mini window missing");input.mouseClick(mini,mini.width/2,mini.height/2,Qt.LeftButton);if(lastRequest!=="0x31"||trace.opened)fail("window click "+lastRequest);console.log("PASS_TRACE_WINDOW_CLICK "+lastRequest);trace.open("")}
    if(step===113){var tile=input.findChild(trace.windows[0].contentItem,"workspace-2");if(!tile)fail("tile missing");input.mouseClick(tile,1,1,Qt.LeftButton);if(lastWorkspace!==2||trace.opened)fail("workspace click "+lastWorkspace);console.log("PASS_TRACE_WORKSPACE_CLICK "+lastWorkspace);trace.open("")}
    if(step===115){input.mouseClick(trace.windows[0].contentItem,4,trace.windows[0].height-4,Qt.LeftButton);if(trace.opened)fail("backdrop did not dismiss");console.log("PASS_BACKDROP_DISMISS")}
    if(step===117){
      current.windows=current.windows.filter(function(w){return w.id!=="0x41"});svc.ingest(JSON.stringify(current))
      lastRequest="";svc.focusWindow("0x41");svc.focusWindow("0xBAD;exec");if(lastRequest!=="")fail("stale focus dispatched")
      lastWorkspace=0;svc.focusWorkspace(999);if(lastWorkspace!==0)fail("stale workspace dispatched")
      console.log("PASS_STALE_NAVIGATION")
    }
    if(step===119){console.log("NATIVE_DONE");Qt.quit()}
    } catch(e) {if(!failed){failed=true;console.log("TEST_FAILURE "+e);Qt.quit()}}
  }}
}
'''.replace('OUT+',json.dumps(str(OUT))+'+')

def interiors(rects):
  for r in rects:
    yield (int(r['x'])+1,int(r['y'])+1,int(r['x']+r['w'])-2,int(r['y']+r['h'])-2)

def check_pixels(name,rects):
  ref=Image.open(OUT/f'ref-{name}.png').convert('RGB');net=Image.open(OUT/f'net-{name}.png').convert('RGB')
  assert ref.size==net.size,(ref.size,net.size)
  diff=ImageChops.difference(ref,net).convert('L').point(lambda v:255 if v>2 else 0)
  inside=0
  for x0,y0,x1,y1 in interiors(rects):
    box=diff.crop((x0,y0,x1+1,y1+1));inside+=sum(1 for v in box.getdata() if v)
  total=sum(1 for v in diff.getdata() if v)
  assert inside==0,f'{name}: roots changed {inside} pixels inside windows'
  assert total>1500,f'{name}: roots nearly invisible ({total} changed pixels)'
  return total

with tempfile.TemporaryDirectory(prefix='mycelium-native-') as tmp:
  work=Path(tmp)
  for name in ('Commons','Ui','services'):(work/name).symlink_to(SHELL/name,target_is_directory=True)
  shutil.copy2(ROOT/'bridge.py',work/'bridge.py')
  shutil.copytree(ROOT/'v4',work/'v4')
  shutil.copy2(ROOT/'v4'/'Widget.qml',work/'Widget.qml')
  isolated_x11=os.environ.get('MYCELIUM_ISOLATED_X11')=='1'
  qml=QML
  if isolated_x11:
    # Only remove Wayland attached properties in disposable test copies; test
    # the unchanged production Items/Shapes/controls on an isolated X display.
    for q in (work/'v4').glob('*.qml'):
      q.write_text(re.sub(r'^\s*WlrLayershell\.[^\n]+\n','\n',q.read_text(),flags=re.M))
    qml=re.sub(r'WlrLayershell.keyboardFocus:WlrKeyboardFocus.None;','',qml)
  (work/'shell.qml').write_text(qml)
  try:
    result=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],capture_output=True,text=True,timeout=40)
  except subprocess.TimeoutExpired as e:
    log=(e.stdout or b"").decode()+(e.stderr or b"").decode();(OUT/'native.log').write_text(log);print(log);raise
  log=result.stdout+result.stderr;(OUT/'native.log').write_text(log)
  print(log)
  assert 'TEST_FAILURE' not in log and 'NATIVE_DONE' in log,log
  for marker in ('PASS_COLD_COMPONENT_CREATION','PASS_SEAMS_GAPS','PASS_SEAMS_ZERO','PASS_SEAMS_SINGLE','PASS_FLOATING_OCCLUDER','PASS_FOCUS_GROWTH','PASS_FOCUS_SPARK','PASS_MOTION_SETTLES','PASS_URGENT_ONE_PULSE','PASS_LAYOUT_REGROW','PASS_RENDER_GATES_OUTAGE_RESET','PASS_TRACE_FOREST','PASS_TRACE_WINDOW_CLICK','PASS_TRACE_WORKSPACE_CLICK','PASS_BACKDROP_DISMISS','PASS_STALE_NAVIGATION'):
    assert marker in log,f'missing {marker}'
  for forbidden in ('Error:','ERROR:','ReferenceError','TypeError','Unable to assign','Cannot assign','is not a type','WARN scene','Binding loop'):
    assert forbidden not in log,f'{forbidden}\n{log}'
  layouts={m.group(1):json.loads(m.group(2)) for m in re.finditer(r'LAYOUT (\w+) (\[.*\])',log)}
  stats={name:check_pixels(name,layouts[name]) for name in ('gaps','zero','single','floating')}
  print('PASS_PIXELS roots visible in seams, zero changed pixels inside windows '+json.dumps(stats))

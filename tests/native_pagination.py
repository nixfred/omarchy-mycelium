from runtime_paths import omarchy_path,private_x_display
"""Trace map pages on disposable Xvfb with real QtTest pointer input; no desktop interaction."""
import json, os, re, shutil, subprocess, tempfile
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('MYCELIUM_CANDIDATE',str(BASE))).resolve()
SIZE=os.environ.get('MYCELIUM_TEST_SIZE','1920x1080')
SCALE=os.environ.get('QT_SCALE_FACTOR','1')
OUT=Path(os.environ.get('MYCELIUM_EVIDENCE_DIR',str(BASE/'local-evidence/pagination')))/f'{SIZE}-scale-{SCALE}'
OUT.mkdir(parents=True,exist_ok=True)
QML='''import QtQuick
import Quickshell
import "v4" as V4
import QtTest
ShellRoot {
  property string lastRequest:""
  property int lastWorkspace:0
  property var frame:({settings:{seeds:[78351],paused:false,reducedMotion:true},monitors:[],workspaces:[],windows:[],focus:"0x1"})
  V4.Service {id:svc;testMode:true;onFocusRequested:id=>{lastRequest=id};onWorkspaceRequested:id=>{lastWorkspace=id}}
  V4.Trace {id:trace;controllerOverride:svc}
  Timer {interval:500;running:true;onTriggered:{
    var s=Quickshell.screens[0]
    frame.monitors=[{name:s.name,id:0,workspace:1,x:0,y:0,width:1920,height:1080,focused:true,reserved:[0,35,0,0]}]
    // 24 workspaces, two windows each: the bridge's workspace bound.
    for(var i=1;i<=24;i++){
      frame.workspaces.push({id:i,name:String(i),monitor:0})
      frame.windows.push({id:"0x"+(i*2).toString(16),app:"kitty",monitor:0,workspace:i,x:9,y:44,w:945,h:1027,urgent:false,floating:false,fullscreen:false,group:[]})
      frame.windows.push({id:"0x"+(i*2+1).toString(16),app:"brave-browser",monitor:0,workspace:i,x:966,y:44,w:945,h:1027,urgent:i===24,floating:false,fullscreen:false,group:[]})
    }
    svc.ingest(JSON.stringify(frame));trace.open("");runTest.start()
  }}
  Timer {id:runTest;interval:150;onTriggered:{try{input.test_pages()}catch(e){console.log("TEST_FAILURE "+e);quitDelay.start()}}}
  Timer {id:quitDelay;interval:100;onTriggered:Qt.quit()}
  TestCase {
    id:input;name:"TraceMapPages";when:false
    function check(value,message){if(!value)throw new Error(message||"Assertion failed")}
    function expect(actual,expected){check(actual===expected,"Expected "+expected+", got "+actual)}
    function click(name){var item=findChild(trace.windows[0].contentItem,name);check(item!==null,"Missing "+name);mouseClick(item,item.width/2,item.height/2,Qt.LeftButton);wait(10)}
    function bounds(){
      var w=trace.windows[0],area=findChild(w.contentItem,"forestArea"),toolbar=findChild(w.contentItem,"traceToolbar"),pager=findChild(w.contentItem,"pageControls")
      check(area.height>0,"No room for the map at "+w.width+"x"+w.height)
      check(area.y>=toolbar.y+toolbar.height,"Map overlaps the toolbar")
      check(pager.visible===(w.forest.pages>1),"Pager visibility incorrect")
      if(pager.visible)check(pager.y>=area.y+area.height&&pager.y+pager.height<=w.height&&pager.x>=0&&pager.x+pager.width<=w.width,"Pager clipped or overlapping")
      for(var i=0;i<w.forest.tiles.length;i++){
        var t=w.forest.tiles[i],tile=findChild(w.contentItem,"workspace-"+t.id)
        check(tile!==null,"Tile missing "+t.id)
        check(t.x>=-0.5&&t.x+t.w<=area.width+0.5&&t.y-20>=-0.5&&t.y+t.h<=area.height+0.5,"Tile outside map "+t.id)
      }
    }
    function test_pages(){
      wait(150);var w=trace.windows[0]
      expect(w.forest.count,24);bounds()
      console.log("PAGE_GEOMETRY "+JSON.stringify({width:w.width,height:w.height,pages:w.forest.pages,perPage:w.forest.perPage,columns:w.forest.columns,tile:w.forest.tiles.length?Math.round(w.forest.tiles[0].w):0}))
      trace.capture(OUT+"/first-page.png",Quickshell.screens[0].name);wait(150)
      // Reach every workspace through real pager clicks, entering one window on each.
      var seen=[]
      for(var ws=1;ws<=24;ws++){
        var page=Math.floor((ws-1)/w.forest.perPage)
        for(var p=0;p<page;p++)click("nextPage")
        expect(w.pageIndex,page);bounds()
        var id="0x"+(ws*2).toString(16);lastRequest="";click("window-"+id)
        expect(lastRequest,id);check(!trace.opened,"Trace stayed open");seen.push(id);trace.open("");wait(10);expect(w.pageIndex,0)
      }
      console.log("PASS_EVERY_WORKSPACE_REACHABLE "+seen.length)
      while(w.pageIndex+1<w.forest.pages)click("nextPage")
      bounds();trace.capture(OUT+"/last-page.png",Quickshell.screens[0].name);wait(150)
      if(w.forest.pages>1){click("previousPage");expect(w.pageIndex,w.forest.pages-2)}
      // Removing workspaces clamps the page; stale targets do nothing.
      var stale="0x30";frame.workspaces=frame.workspaces.slice(0,2);frame.windows=frame.windows.slice(0,4);svc.ingest(JSON.stringify(frame));wait(30)
      expect(w.forest.pages,1);expect(w.pageIndex,0);bounds();lastRequest="";svc.focusWindow(stale);expect(lastRequest,"")
      console.log("PASS_LIVE_PAGE_CLAMP_STALE_ID")
      trace.close();console.log("PASS_NO_SCROLL_NATIVE_PAGINATION");quitDelay.start()
    }
  }
}'''
with tempfile.TemporaryDirectory(prefix='mycelium-page-test-') as tmp:
    work=Path(tmp);runtime=work/'runtime';runtime.mkdir(mode=0o700)
    shell=omarchy_path()/'shell'
    for name in ('Commons','Ui','services'):(work/name).symlink_to(shell/name,target_is_directory=True)
    shutil.copy2(ROOT/'bridge.py',work/'bridge.py');shutil.copytree(ROOT/'v4',work/'v4')
    for q in (work/'v4').glob('*.qml'):
        q.write_text(re.sub(r'^\s*WlrLayershell\.[^\n]+\n','\n',q.read_text(),flags=re.M))
    (work/'shell.qml').write_text(QML.replace('OUT+',json.dumps(str(OUT))+'+'))
    with private_x_display(SIZE) as display:
        env={**os.environ,'DISPLAY':display,'QT_QPA_PLATFORM':'xcb','XDG_RUNTIME_DIR':str(runtime),'XDG_CACHE_HOME':str(work/'cache'),'OMARCHY_PATH':str(shell.parent)}
        env.pop('WAYLAND_DISPLAY',None)
        try:
            result=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],env=env,text=True,capture_output=True,timeout=90)
        except subprocess.TimeoutExpired as e:
            log=(e.stdout or b'').decode()+(e.stderr or b'').decode();(OUT/'native.log').write_text(log);print(log);raise
        log=result.stdout+result.stderr;(OUT/'native.log').write_text(log);print(log)
        assert result.returncode==0 and 'PASS_NO_SCROLL_NATIVE_PAGINATION' in log and 'TEST_FAILURE' not in log,log
        assert not any(s in log for s in ('FAIL!','Error:','ERROR:','ReferenceError','TypeError','WARN scene','Unable to assign','Binding loop')),log
        for name in ('first-page.png','last-page.png'):assert (OUT/name).stat().st_size>1000

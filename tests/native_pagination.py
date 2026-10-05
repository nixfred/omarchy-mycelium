from runtime_paths import omarchy_path,private_x_display
"""Actual QtTest pointer input on disposable Xvfb; no desktop interaction."""
import json, os, re, shutil, subprocess, tempfile, time
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
ROOT=Path(os.environ.get('MYCELIUM_CANDIDATE',str(BASE))).resolve()
SIZE=os.environ.get('MYCELIUM_TEST_SIZE','1920x1080')
SCALE=os.environ.get('QT_SCALE_FACTOR','1')
OUT=Path(os.environ.get('MYCELIUM_EVIDENCE_DIR',str(BASE/'local-evidence/pagination')))/f'{SIZE}-scale-{SCALE}'
OUT.mkdir(parents=True,exist_ok=True)
QML='''import QtQuick
import Quickshell
import "v3" as V3
import QtTest
ShellRoot {
  property string lastRequest:""
  property int lastWorkspace:0
  property bool ready:false
  property var frame:({settings:{seeds:[78351],paused:false,reducedMotion:true},monitors:[],workspaces:[],windows:[],focus:"0x1"})
  V3.Service {id:svc;testMode:true;onFocusRequested:id=>{lastRequest=id};onWorkspaceRequested:id=>{lastWorkspace=id}}
  V3.Trace {id:trace;controllerOverride:svc}
  Timer {interval:500;running:true;onTriggered:{
    frame.monitors=[{name:Quickshell.screens[0].name,id:0,workspace:1,x:0,y:0}]
    for(var i=1;i<=13;i++)frame.workspaces.push({id:i,name:String(i)})
    for(var j=1;j<=48;j++)frame.windows.push({id:"0x"+j.toString(16),app:j%2?"kitty":"brave-browser",monitor:0,workspace:1,x:9,y:44,w:Quickshell.screens[0].width-18,h:Quickshell.screens[0].height-53,urgent:false,group:[]})
    svc.ingest(JSON.stringify(frame));trace.open("");ready=true;runTest.start()
  }}
  Timer {id:runTest;interval:100;onTriggered:{try{input.test_pages()}catch(e){console.log("TEST_FAILURE "+e);quitDelay.start()}}}
  Timer {id:quitDelay;interval:100;onTriggered:Qt.quit()}
  TestCase {
    id:input;name:"BoundedTrace";when:false
    function check(value,message){if(!value)throw new Error(message||"Assertion failed")}
    function expect(actual,expected){check(actual===expected,"Expected "+expected+", got "+actual)}
    function click(name){var item=findChild(trace.windows[0].contentItem,name);check(item!==null,"Missing "+name);mouseClick(item,item.width/2,item.height/2,Qt.LeftButton);wait(8)}
    function bounds(){
      var w=trace.windows[0],deck=findChild(w.contentItem,"appDeck"),controls=findChild(w.contentItem,"pageControls")
      if(w.pageRows===0)console.log("NO_ROWS "+JSON.stringify({width:w.width,height:w.height,deckY:deck.y,deckH:deck.height,introH:findChild(w.contentItem,"traceIntro").height,toolbarH:findChild(w.contentItem,"traceToolbar").height,controlsW:findChild(w.contentItem,"tracePreferences").width,legendY:findChild(w.contentItem,"traceLegend").y}));check(w.pageRows>0,"No card row fits");check(deck.y>=0&&deck.y+deck.height<=w.height,"Deck outside screen")
      check(controls.visible===w.stackedCards,"Pager visibility incorrect");if(w.stackedCards)check(controls.x>=0&&controls.x+controls.width<=deck.width,"Page controls clipped")
      for(var i=0;i<w.pageCards.length;i++){
        var card=findChild(w.contentItem,"window-"+w.pageCards[i].id)
        check(card!==null,"Page card missing");check(card.x>=0&&card.x+card.width<=deck.width,"Card clipped horizontally")
        check(card.y>=0&&card.y+card.height<=(w.stackedCards?controls.y-4:deck.height),"Card overlaps pager or clips vertically")
      }
    }
    function test_pages(){
      wait(100);var w=trace.windows[0]
      expect(w.localWindows.length,48);check(w.stackedCards);check(w.pageCount>1);bounds();click("pageLabel");check(trace.opened,"Page label dismissed Trace");expect(w.pageIndex,0)
      console.log("PAGE_GEOMETRY "+JSON.stringify({width:w.width,height:w.height,rows:w.pageRows,columns:w.cardColumns,size:w.pageSize,pages:w.pageCount}))
      trace.capture(OUT+"/first-page.png",Quickshell.screens[0].name);wait(120)
      var seen=[]
      // Click every actual app card. Reopening starts at page one; use actual
      // Next buttons to return to the target page rather than assigning state.
      for(var i=0;i<48;i++){
        var page=Math.floor(i/w.pageSize)
        for(var p=0;p<page;p++)click("nextPage")
        bounds();var id=frame.windows[i].id;lastRequest="";click("window-"+id)
        expect(lastRequest,id);check(!trace.opened);seen.push(id);trace.open("");wait(8);expect(w.pageIndex,0)
      }
      console.log("PASS_PAGINATED_APP_CLICKS "+seen.length)
      while(w.pageIndex+1<w.pageCount)click("nextPage")
      bounds();trace.capture(OUT+"/last-page.png",Quickshell.screens[0].name);wait(120)
      click("previousPage");expect(w.pageIndex,w.pageCount-2)
      // Resize only the disposable fixture window; the desktop is untouched.
      w.anchors.right=false;w.anchors.bottom=false;w.implicitWidth=Math.min(480,w.screen.width);w.implicitHeight=360;wait(120)
      bounds();check(w.pageIndex<w.pageCount);trace.capture(OUT+"/resized-page.png",Quickshell.screens[0].name);wait(120)
      w.anchors.right=true;w.anchors.bottom=true;wait(120);bounds();check(w.pageIndex<w.pageCount)
      console.log("PASS_NATIVE_RESIZE_PAGE_BOUNDS")
      // A same-workspace geometry/urgency event preserves the selected page.
      var selected=w.pageIndex;frame.windows[0].urgent=true;svc.ingest(JSON.stringify(frame));wait(20);expect(w.pageIndex,selected)
      // Removing windows clamps the last page without inventing stale targets.
      var stale=frame.windows[47].id;frame.windows=frame.windows.slice(0,1);svc.ingest(JSON.stringify(frame));wait(20)
      expect(w.pageIndex,0);expect(w.pageCount,1);bounds();lastRequest="";svc.focusWindow(stale);expect(lastRequest,"")
      console.log("PASS_LIVE_PAGE_CLAMP_STALE_ID")
      frame.monitors[0].workspace=2;svc.ingest(JSON.stringify(frame));wait(20);expect(w.pageIndex,0);expect(w.localWindows.length,0)
      console.log("PASS_WORKSPACE_PAGE_RESET")
      trace.close();console.log("PASS_NO_SCROLL_NATIVE_PAGINATION");quitDelay.start()
    }
  }
}'''
with tempfile.TemporaryDirectory(prefix='mycelium-page-test-') as tmp:
    work=Path(tmp);runtime=work/'runtime';runtime.mkdir(mode=0o700)
    shell=omarchy_path()/'shell'
    for name in ('Commons','Ui','services'):(work/name).symlink_to(shell/name,target_is_directory=True)
    shutil.copy2(ROOT/'bridge.py',work/'bridge.py');shutil.copytree(ROOT/'v3',work/'v3')
    for q in (work/'v3').glob('*.qml'):
        q.write_text(re.sub(r'^\s*WlrLayershell\.[^\n]+\n','\n',q.read_text(),flags=re.M))
    (work/'shell.qml').write_text(QML.replace('OUT+',json.dumps(str(OUT))+'+'))
    with private_x_display(SIZE) as display:
        env={**os.environ,'DISPLAY':display,'QT_QPA_PLATFORM':'xcb','XDG_RUNTIME_DIR':str(runtime),'XDG_CACHE_HOME':str(work/'cache'),'OMARCHY_PATH':str(shell.parent)}
        try:
            result=subprocess.run(['qs','--no-color','--path',str(work/'shell.qml')],env=env,text=True,capture_output=True,timeout=55)
        except subprocess.TimeoutExpired as e:
            log=(e.stdout or b'').decode()+(e.stderr or b'').decode();(OUT/'native.log').write_text(log);print(log);raise
        log=result.stdout+result.stderr;(OUT/'native.log').write_text(log);print(log)
        assert result.returncode==0 and 'PASS_NO_SCROLL_NATIVE_PAGINATION' in log,log
        assert not any(s in log for s in ('FAIL!', 'Error:','ERROR:','ReferenceError','TypeError','WARN scene','Unable to assign')),log
        for name in ('first-page.png','last-page.png'):assert (OUT/name).stat().st_size>1000

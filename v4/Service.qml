import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.Commons

Item {
  id: root
  property string omarchyPath: ""
  property var shell: null
  property var manifest: null
  property var pluginRegistry: null
  property bool testMode: false
  property var frame: ({windows:[],monitors:[],workspaces:[]})
  // Observed workspace hops, newest last. Memory only, never persisted.
  property var hops: []
  property string previousFocus: ""
  property string pulseFrom: ""
  property string pulseTo: ""
  property int revision: 0
  property int layoutRevision: 0
  property string response: "Window map ready"
  property bool paused: false
  property bool reducedMotion: false
  property bool settled: true
  property bool unavailable: false
  property bool preferencesLoaded: false
  property bool preferencesPending: false
  property int retryCount: 0
  signal frameArrived()
  signal focusRequested(string windowId)
  signal workspaceRequested(int workspaceId)
  readonly property string helper: Qt.resolvedUrl("../bridge.py").toString().replace("file://", "")
  readonly property bool animating: !paused && !reducedMotion && !settled && !unavailable
  readonly property bool anyUrgent: (frame.windows||[]).some(function(w){return w.urgent})
  // The one urgent window allowed to pulse, across every output (motion budget).
  readonly property string pulseUrgentId: {
    var shown={};(frame.monitors||[]).forEach(function(m){if(!m.off)shown[m.id+":"+m.workspace]=true})
    var u=(frame.windows||[]).filter(function(w){return w.urgent&&!w.floating&&shown[w.monitor+":"+w.workspace]})
    return u.length?u[0].id:""
  }
  // Seams sit on window borders, so geometry is tracked whenever roots are
  // visible, including Still. Idle, Pause, outage and covered outputs stop it.
  readonly property bool geometryActive: !testMode && !paused && !idle.isIdle && !unavailable && frame.monitors.some(function(m){return !m.off && !frame.windows.some(function(w){return w.monitor===m.id&&w.workspace===m.workspace&&w.fullscreen})})
  onGeometryActiveChanged: if(bridge.running)bridge.write(geometryActive?"active\n":"idle\n")

  function outputStatus(name,seamCount) {
    if(unavailable)return "Waiting for desktop connection"
    if(paused)return "Ambient paused"
    var outputs=(frame.monitors||[]).filter(function(m){return !name||m.name===name})
    if(!outputs.length)return "Waiting for display"
    if(outputs.every(function(m){return m.off}))return "Display is off"
    if(outputs.every(function(m){return frame.windows.some(function(w){return w.monitor===m.id&&w.workspace===m.workspace&&w.fullscreen})}))return "Ambient hidden by fullscreen"
    if(seamCount===0)return "No tiled windows on this workspace"
    return reducedMotion?"Still roots · motion off":settled?"Roots resting on your window seams":"Roots responding · "+response.toLowerCase()
  }
  // Window rectangles plus what each output shows: a workspace switch slides
  // windows in, so it counts as a layout change too.
  function geometryKey(f) {
    return JSON.stringify([(f.windows||[]).map(function(w){return [w.id,w.x,w.y,w.w,w.h,w.workspace,w.floating,w.fullscreen]}),
      (f.monitors||[]).map(function(m){return [m.id,m.workspace,m.special||0,m.width,m.height]})])
  }
  function focusedWorkspace(f) {
    var m=(f.monitors||[]).filter(function(m){return m.focused})[0]
    return m?m.workspace:0
  }
  function ingest(line) {
    try {
      var next=JSON.parse(line)
      if(next.unavailable) {markUnavailable();return}
      var recovered=unavailable
      unavailable=false
      retryCount=0
      if(next.settings && !preferencesLoaded) { paused=next.settings.paused; reducedMotion=next.settings.reducedMotion;preferencesLoaded=true }
      var changed=recovered || JSON.stringify([frame.windows,frame.monitors,frame.focus,frame.workspaces])!==JSON.stringify([next.windows,next.monitors,next.focus,next.workspaces])
      revision++;if(!changed)return
      var live={};(next.windows||[]).forEach(function(w){live[w.id]=true})
      var fromWs=focusedWorkspace(frame),toWs=focusedWorkspace(next)
      if(fromWs>0&&toWs>0&&fromWs!==toWs)hops=hops.concat([{a:fromWs,b:toWs}]).slice(-12)
      var known={};(next.workspaces||[]).forEach(function(w){known[w.id]=true})
      hops=hops.filter(function(h){return known[h.a]&&known[h.b]})
      var layoutChanged=geometryKey(frame)!==geometryKey(next)
      response=fromWs!==toWs?"Workspace changed":next.focus!==previousFocus?"Focus moved":"Layout changed"
      // A focus change records where it came from; unchanged frames keep the pulse.
      if(next.focus && next.focus!==previousFocus) { pulseFrom=live[previousFocus]?previousFocus:"";pulseTo=next.focus }
      if(!live[pulseTo]) {pulseFrom="";pulseTo=""}
      previousFocus=next.focus||""
      frame=next
      if(layoutChanged)layoutRevision++
      settled=false;settle.restart();frameArrived()
    } catch(e) { console.warn("Mycelium: invalid bridge frame") }
  }
  function markUnavailable() {
    unavailable=true;frame={windows:[],monitors:[],workspaces:[]};settled=true
    previousFocus="";hops=[];pulseFrom="";pulseTo=""
  }
  function setPreference(key,value) {
    if(key==="paused")paused=value
    if(key==="reducedMotion")reducedMotion=value
    if(paused||reducedMotion)settled=true
    if(!testMode) {preferencesPending=true;savePreferences()}
  }
  function savePreferences() {
    if(persist.running||!preferencesPending)return
    preferencesPending=false
    persist.command=["python3",helper,"preferences",String(paused),String(reducedMotion)]
    persist.running=true
  }
  function trace() { if(shell)shell.summon("nixfred.mycelium", "") }
  function resync() {
    if(testMode)return
    retry.stop();retryCount=0
    if(bridge.running)bridge.write("resync\n")
    else bridge.running=true
  }
  function focusWindow(id) {
    if(!/^0x[0-9a-fA-F]+$/.test(id))return
    if(!frame.windows.some(function(w){return w.id===id}))return
    focusRequested(id)
    if(!testMode)Quickshell.execDetached(["python3",helper,"focus",id])
  }
  function focusWorkspace(id) {
    if(!frame.workspaces.some(function(w){return w.id===id&&id>0}))return
    workspaceRequested(id)
    if(!testMode)Quickshell.execDetached(["python3",helper,"workspace",String(id)])
  }
  Timer { id:settle;interval:6500;onTriggered:root.settled=true }
  Timer { id:retry;interval:3000;onTriggered:{root.retryCount++;bridge.running=true} }
  IdleMonitor {id:idle;enabled:!root.testMode;timeout:8;respectInhibitors:false}
  Process {id:persist;onExited:root.savePreferences()}
  Process {
    id:bridge
    running: !root.testMode
    command: ["python3",root.helper,"watch"]
    stdinEnabled:true
    onStarted: bridge.write(root.geometryActive?"active\n":"idle\n")
    stdout: SplitParser { onRead: data => root.ingest(data) }
    onExited: { if(!root.testMode) {root.markUnavailable();if(root.retryCount<3)retry.restart()} }
  }
  IpcHandler {
    target:"nixfred.mycelium"
    function trace(): string {root.trace();return "ok"}
    function pause(): string {root.setPreference("paused",true);return "ok"}
    function resume(): string {root.setPreference("paused",false);return "ok"}
    function resync(): string {root.resync();return "ok"}
    function reducedMotion(value: bool): string {root.setPreference("reducedMotion",value);return "ok"}
    function state(): string {return JSON.stringify({version:4,paused:root.paused,reducedMotion:root.reducedMotion,settled:root.settled,unavailable:root.unavailable,windows:root.frame.windows.length,hops:root.hops.length,urgent:root.anyUrgent,revision:root.revision})}
  }
  Variants {
    model: root.testMode ? [] : Quickshell.screens
    PanelWindow {
      id:ambient
      required property var modelData
      screen:modelData
      readonly property var output:(root.frame.monitors||[]).filter(function(m){return m.name===modelData.name})[0]
      readonly property bool covered:output?root.frame.windows.some(function(w){return w.monitor===output.id&&w.workspace===output.workspace&&w.fullscreen}):false
      anchors {top:true;bottom:true;left:true;right:true}
      color:"transparent"
      exclusionMode:ExclusionMode.Ignore
      WlrLayershell.namespace:"mycelium-ambient"
      WlrLayershell.layer:WlrLayer.Overlay
      WlrLayershell.keyboardFocus:WlrKeyboardFocus.None
      mask:Region {}
      visible: !root.paused && !root.unavailable && output!==undefined && !output.off && !covered
      Network { id:network;anchors.fill:parent;controller:root;screenName:modelData.name;renderingEnabled:parent.visible }
    }
  }
}

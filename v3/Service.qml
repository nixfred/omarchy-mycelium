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
  property var previous: null
  property var edges: []
  property string previousFocus: ""
  property string pulseFrom: ""
  property string pulseTo: ""
  property int revision: 0
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
  readonly property bool geometryActive: !testMode && !paused && !reducedMotion && !idle.isIdle && !unavailable && frame.monitors.some(function(m){return !m.off && !frame.windows.some(function(w){return w.monitor===m.id&&w.workspace===m.workspace&&w.fullscreen})})
  onGeometryActiveChanged: if(bridge.running)bridge.write(geometryActive?"active\n":"idle\n")

  function outputStatus(name,nodeCount) {
    if(unavailable)return "Waiting for desktop connection"
    if(paused)return "Ambient paused"
    var outputs=(frame.monitors||[]).filter(function(m){return !name||m.name===name})
    if(!outputs.length)return "Waiting for display"
    if(outputs.every(function(m){return m.off}))return "Display is off"
    if(outputs.every(function(m){return frame.windows.some(function(w){return w.monitor===m.id&&w.workspace===m.workspace&&w.fullscreen})}))return "Ambient hidden by fullscreen"
    if(nodeCount===0)return "No room for roots on this workspace"
    return reducedMotion?"Still roots · motion off":settled?"Roots resting · react to window changes":response+" · roots responding"
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
      settled=false
      var workspaceChanged=JSON.stringify((frame.monitors||[]).map(function(m){return m.workspace}))!==JSON.stringify((next.monitors||[]).map(function(m){return m.workspace}))
      response=workspaceChanged?"Workspace changed":next.focus!==previousFocus?"Focus switched":"Window layout changed"
      var live={};(next.windows||[]).forEach(function(w){live[w.id]=true})
      var kept=edges.filter(function(e){return live[e.a]&&live[e.b]})
      pulseFrom="";pulseTo=next.focus!==previousFocus && live[next.focus] && live[previousFocus]?next.focus:""
      if(next.focus && previousFocus && next.focus!==previousFocus && live[next.focus] && live[previousFocus]) {
        pulseFrom=previousFocus;pulseTo=next.focus
        kept=kept.filter(function(e){return !(e.a===previousFocus&&e.b===next.focus)})
        kept.push({a:previousFocus,b:next.focus,kind:"focus"})
      }
      edges=kept.slice(-32); previousFocus=next.focus||""
      previous=frame;frame=next
      departures.restart()
      if(changed){settled=false;settle.restart();frameArrived()}
    } catch(e) { console.warn("Mycelium: invalid bridge frame") }
  }
  function markUnavailable() {
    unavailable=true;frame={windows:[],monitors:[],workspaces:[]};settled=true
    previous=null;previousFocus="";edges=[];pulseFrom="";pulseTo=""
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
  Timer { id:departures;interval:1400;onTriggered:root.previous=null }
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
    function state(): string {return JSON.stringify({paused:root.paused,reducedMotion:root.reducedMotion,settled:root.settled,unavailable:root.unavailable,windows:root.frame.windows.length,edges:root.edges.length,revision:root.revision})}
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

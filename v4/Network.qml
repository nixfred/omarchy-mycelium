import QtQuick
import QtQuick.Shapes
import Quickshell
import qs.Commons
import "Topology.js" as Topology

// Ambient roots on the seams between windows. Quiet by default: motion only
// answers an event (focus grows a root, layout changes regrow the seams), and
// the one continuous pulse is reserved for the first urgent window.
Item {
  id:root
  property var controller
  property string screenName: ""
  property bool renderingEnabled: true
  Component.onCompleted: console.debug("Mycelium NetworkV4 seam roots loaded")
  readonly property var graph: Topology.graph(controller.frame,screenName,controller.pulseFrom,controller.pulseTo,width,height)
  readonly property bool motion: renderingEnabled && visible && controller.animating && !graph.off && !graph.fullscreen
  readonly property bool breathing: renderingEnabled && visible && !controller.paused && !controller.reducedMotion && !controller.unavailable && !graph.off && !graph.fullscreen && graph.urgent.some(function(u){return u.id===controller.pulseUrgentId})
  readonly property color sap: Color.accent
  readonly property color amber: "#efb45a"
  // Zero-gap layouts put seams on the border line itself; stay subtler there.
  readonly property bool tight: graph.minInset<2
  property real presence: 1
  property real growth: 1
  property real travelT: 1
  property real oldOpacity: 0
  property real beat: 0.9
  property string focusKey: ""
  property string lastFull: ""
  property string oldSvg: ""
  property var lastWorkspace: null
  property bool pendingGrow: false
  property int seenLayout: -1
  readonly property string focusPath: graph.focus?(growth>=0.999?graph.focus.full:Topology.grown(graph.focus.perimeter,graph.focus.start,growth,graph.occluders,graph.focus.pad)):""

  function startGrow() {
    if(!motion){growth=1;travelT=1;return}
    if(travelT<1&&graph.travel.length)spark.restart()
    else {travelT=1;grow.restart()}
  }
  function react() {
    var g=graph,key=g.focus?g.workspace+":"+g.focus.id:""
    if(controller.layoutRevision!==seenLayout) {
      var first=seenLayout<0
      seenLayout=controller.layoutRevision
      // Hide seams that may now cross moved windows; regrow once stable (R6).
      if(!first){regrow.stop();presence=0;stable.restart()}
    }
    if(key!==focusKey) {
      // Only on the same workspace: another workspace's frame would cross windows here.
      if(lastFull&&motion&&presence>0&&g.workspace===lastWorkspace){oldSvg=lastFull;fade.restart()}
      focusKey=key
      if(motion) {
        growth=0;travelT=g.travel.length?0:1
        if(stable.running)pendingGrow=true;else startGrow()
      } else {grow.stop();spark.stop();growth=1;travelT=1}
    }
    lastFull=g.focus?g.focus.full:""
    lastWorkspace=g.workspace
  }
  Connections {target:root.controller;function onFrameArrived(){root.react()}}
  onMotionChanged: if(!motion){grow.stop();spark.stop();fade.stop();growth=1;travelT=1;oldOpacity=0;pendingGrow=false}
  Timer {
    id:stable;interval:450
    onTriggered:{
      if(root.motion)regrow.restart();else root.presence=1
      if(root.pendingGrow){root.pendingGrow=false;root.startGrow()}
    }
  }
  NumberAnimation {id:regrow;target:root;property:"presence";to:1;duration:320;easing.type:Easing.OutCubic}
  NumberAnimation {id:grow;target:root;property:"growth";from:0;to:1;duration:560;easing.type:Easing.OutCubic}
  NumberAnimation {id:spark;target:root;property:"travelT";from:0;to:1;duration:420;easing.type:Easing.InOutSine;onFinished:grow.restart()}
  NumberAnimation {id:fade;target:root;property:"oldOpacity";from:0.6;to:0;duration:420;easing.type:Easing.InCubic}
  SequentialAnimation {
    running:root.breathing;loops:Animation.Infinite
    onRunningChanged:if(!running)root.beat=0.9
    NumberAnimation {target:root;property:"beat";to:0.35;duration:1300;easing.type:Easing.InOutSine}
    NumberAnimation {target:root;property:"beat";to:0.95;duration:1300;easing.type:Easing.InOutSine}
  }

  // Quiet network: every seam on this workspace, faint.
  Shape {
    objectName:"seamNetwork"
    anchors.fill:parent;preferredRendererType:Shape.CurveRenderer
    opacity:root.presence*(root.tight?0.16:0.22)
    ShapePath {strokeColor:root.sap;strokeWidth:1;fillColor:"transparent";capStyle:ShapePath.FlatCap;PathSvg {path:root.graph.svg}}
  }
  // Knots where three or more seams meet.
  Repeater {
    model:root.graph.junctions
    delegate:Rectangle {
      required property var modelData
      readonly property real size:root.tight?2:3
      x:modelData.x-size/2;y:modelData.y-size/2;width:size;height:size;radius:size/2
      color:root.sap;opacity:root.presence*(root.tight?0.35:0.5)
    }
  }
  // The previous focus root fades as the new one grows.
  Shape {
    anchors.fill:parent;preferredRendererType:Shape.CurveRenderer
    visible:root.oldOpacity>0;opacity:root.oldOpacity*root.presence
    ShapePath {strokeColor:root.sap;strokeWidth:1.5;fillColor:"transparent";capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin;PathSvg {path:root.oldSvg}}
  }
  // The focused window's root.
  Shape {
    objectName:"focusRoot"
    anchors.fill:parent;preferredRendererType:Shape.CurveRenderer
    visible:root.graph.focus!==null;opacity:root.presence
    ShapePath {strokeColor:Qt.rgba(root.sap.r,root.sap.g,root.sap.b,0.16);strokeWidth:root.graph.focus?root.graph.focus.glow:-1;fillColor:"transparent";capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin;PathSvg {path:root.focusPath}}
    ShapePath {strokeColor:Qt.rgba(root.sap.r,root.sap.g,root.sap.b,root.tight?0.7:0.85);strokeWidth:root.tight?1:1.5;fillColor:"transparent";capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin;PathSvg {path:root.focusPath}}
  }
  // A spark crossing the seams when focus jumps between windows that do not touch.
  Item {
    objectName:"focusSpark"
    visible:spark.running&&root.graph.travel.length>0
    readonly property var p:Topology.sample(root.graph.travel,root.travelT)
    x:{var point=p;return point?point.x:0}
    y:{var point=p;return point?point.y:0}
    Rectangle {x:-4;y:-4;width:8;height:8;radius:4;color:root.sap;opacity:0.3}
    Rectangle {x:-1.5;y:-1.5;width:3;height:3;radius:1.5;color:Color.foreground}
  }
  // Attention: amber seams. One urgent window pulses across all outputs (motion budget).
  Repeater {
    model:root.graph.urgent
    delegate:Shape {
      required property var modelData
      objectName:"urgentRoot"
      anchors.fill:parent;preferredRendererType:Shape.CurveRenderer
      opacity:root.presence*(modelData.id===root.controller.pulseUrgentId&&root.breathing?root.beat:0.9)
      ShapePath {strokeColor:Qt.rgba(0.937,0.706,0.353,0.2);strokeWidth:modelData.glow;fillColor:"transparent";capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin;PathSvg {path:modelData.svg}}
      ShapePath {strokeColor:root.amber;strokeWidth:1.5;fillColor:"transparent";capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin;PathSvg {path:modelData.svg}}
    }
  }
}

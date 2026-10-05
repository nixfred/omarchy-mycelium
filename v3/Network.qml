import QtQuick
import QtQuick.Shapes
import Quickshell
import qs.Commons
import "Topology.js" as Topology

Item {
  id:root
  property var controller
  property string screenName: ""
  property bool traceMode: false
  property bool renderingEnabled: true
  Component.onCompleted: console.debug("Mycelium NetworkV3 paginated Trace loaded")
  signal workspaceChosen()
  readonly property var graph: Topology.graph(controller.frame,screenName,controller.edges,controller.previous,width,height)
  readonly property bool motion: renderingEnabled && visible && controller.animating && !graph.off && !graph.fullscreen
  readonly property color sap: Color.accent
  readonly property color cyan: Qt.tint(sap,"#9047e5da")
  property real breath: 0
  property var ghosts: []
  property var priorPaths: []
  property var oldIds: ({})
  onGraphChanged: {
    var ids={};graph.paths.forEach(function(p){ids[p.id]=true})
    oldIds={};priorPaths.forEach(function(p){oldIds[p.id]=true})
    ghosts=controller.animating?priorPaths.filter(function(p){return !ids[p.id]&&p.points.every(function(v,i){return !i||Topology.clear(p.points[i-1],v,graph.rects||[])})}).slice(0,24):[]
    priorPaths=graph.paths
    if(ghosts.length)ghostTimer.restart()
    
  }
  Timer {id:ghostTimer;interval:650;onTriggered:root.ghosts=[]}
  Connections {target:root.controller;function onFrameArrived(){if(root.motion){breathe.restart();if(root.controller.pulseTo&&root.pulsePath.length)pulse.restart()}}}
  SequentialAnimation {
    id:breathe;
    loops:2
    NumberAnimation {target:root;property:"breath";to:1;duration:850;easing.type:Easing.InOutSine}
    NumberAnimation {target:root;property:"breath";to:0;duration:1000;easing.type:Easing.InOutSine}
  }
  onMotionChanged: if(!motion){breathe.stop();breath=0;ghosts=[];pulse.stop()}
  Repeater {
    model:root.graph.paths
    delegate:Item {
      id:branch
      required property var modelData
      anchors.fill:parent
      property real growth: root.motion && !root.oldIds[modelData.id] ? 0 : 1
      readonly property string revealed:growth>=0.999?modelData.svg:Topology.partial(modelData.points,growth)
      Component.onCompleted: grow.start()
      NumberAnimation {id:grow;target:branch;property:"growth";to:1;duration:root.motion?520:0;easing.type:Easing.OutCubic}
      Connections {target:root;function onMotionChanged(){if(!root.motion){grow.stop();branch.growth=1}}}
      Shape {
        anchors.fill:parent
        preferredRendererType:Shape.CurveRenderer
        opacity: root.traceMode?0.6:0.22+root.breath*0.12
        ShapePath {strokeColor:Qt.rgba(root.cyan.r,root.cyan.g,root.cyan.b,0.32);strokeWidth:root.traceMode?8:5;fillColor:"transparent";capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin;PathSvg {path:branch.revealed}}
      }
      Shape {
        anchors.fill:parent
        preferredRendererType:Shape.CurveRenderer
        opacity: modelData.kind==="root"?(root.traceMode?0.85:0.58+root.breath*0.22):(root.traceMode?1:0.72)
        ShapePath {strokeColor:branch.modelData.kind==="group"?Color.foreground:branch.modelData.kind==="move"?"#efb45a":root.cyan;strokeWidth:branch.modelData.kind==="root"?(root.traceMode?1.8:1.4):1.8;fillColor:"transparent";capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin;PathSvg {path:branch.revealed}}
      }
      // Tiny procedural offshoots remain inside verified free corridors.
      Repeater {
        model: Math.min(3,modelData.points.length)
        delegate:Rectangle {
          required property int index
          readonly property var p:Topology.sample(branch.modelData.points,(index+1)/4)
          x:p.x-1.5;y:p.y-1.5;width:3;height:3;radius:2;color:root.cyan
          opacity:branch.growth*(root.traceMode?0.85:0.35)
        }
      }
    }
  }
  Repeater {
    model:root.graph.filaments||[]
    delegate:Item {
      required property var modelData
      anchors.fill:parent
      Shape {
        anchors.fill:parent;preferredRendererType:Shape.CurveRenderer
        opacity:root.traceMode?0.62:0.3
        ShapePath {strokeColor:root.cyan;strokeWidth:0.8;fillColor:"transparent";capStyle:ShapePath.RoundCap;PathSvg {path:modelData.svg}}
      }
      Rectangle {x:modelData.x-1.5;y:modelData.y-1.5;width:3;height:3;radius:2;color:root.cyan;opacity:root.traceMode?0.7:0.24}
    }
  }
  Repeater {
    model:root.graph.junctions||[]
    delegate:Item {
      required property var modelData
      x:modelData.x;y:modelData.y
      readonly property real size:Math.min(24,5+Math.sqrt(modelData.count)*4,Math.max(0,Topology.clearance(modelData,root.graph.rects,root.width,root.height)-1))
      Rectangle {anchors.centerIn:parent;width:parent.size*2;height:width;radius:width/2;color:root.cyan;opacity:root.traceMode?0.045:0.025}
      Rectangle {anchors.centerIn:parent;width:parent.size;height:width;radius:width/2;color:root.cyan;opacity:root.traceMode?0.13:0.065}
      Rectangle {anchors.centerIn:parent;width:5;height:5;radius:3;color:Color.foreground;opacity:root.traceMode?0.8:0.28}
    }
  }
  Item {
    visible:root.graph.paths.some(function(p){return p.kind==="root"}) && root.graph.hub!==undefined
    x:{var g=root.graph;var h=g?g.hub:null;return h?h.x:0}
    y:{var g=root.graph;var h=g?g.hub:null;return h?h.y:0}
    readonly property real diameter:Math.min(84,(root.graph.hub&&root.graph.hub.clearance||0)*1.65)
    Repeater {
      model:5
      delegate:Rectangle {
        required property int index
        anchors.centerIn:parent;width:parent.diameter*(1-index*0.15);height:width;radius:width/2
        color:Qt.rgba(root.cyan.r,root.cyan.g,root.cyan.b,0.018+index*0.012)
        border.width:index===0?1:0;border.color:Qt.rgba(root.cyan.r,root.cyan.g,root.cyan.b,root.traceMode?0.4:0.12)
      }
    }
    Rectangle {anchors.centerIn:parent;width:Math.min(14,parent.diameter);height:width;radius:width/2;color:root.cyan;opacity:0.32+root.breath*0.12}
    Rectangle {anchors.centerIn:parent;width:2;height:2;radius:1;color:Color.foreground;opacity:0.8}
    Text {visible:root.traceMode && parent.diameter>=50;x:-70;y:parent.diameter/2+8;width:140;text:"ROOT / "+String(root.graph.workspace).padStart(2,"0");horizontalAlignment:Text.AlignHCenter;font.family:Style.font.family;font.pixelSize:9;font.letterSpacing:2;color:root.cyan;opacity:0.7}
  }
  Repeater {
    model:root.ghosts
    delegate:Shape {
      id:ghost
      required property var modelData
      property real retreat:1
      anchors.fill:parent;opacity:0.5*retreat
      NumberAnimation on retreat {to:0;duration:600;running:root.motion;easing.type:Easing.InCubic}
      ShapePath {strokeColor:root.cyan;strokeWidth:1;fillColor:"transparent";PathSvg {path:Topology.partial(ghost.modelData.points,ghost.retreat)}}
    }
  }
  Repeater {
    model:root.graph.nodes
    delegate:Item {
      required property var modelData
      x:modelData.x-size/2;y:modelData.y-size/2;width:size;height:size
      readonly property real size:Math.min(26,Math.max(2,(modelData.clearance-1)*2))
      Rectangle {anchors.centerIn:parent;width:Math.min(parent.size,modelData.urgent?20:12);height:width;radius:width/2;color:"transparent";border.color:modelData.urgent?"#efb45a":root.cyan;border.width:modelData.urgent?2:1;opacity:modelData.urgent?1:modelData.focused?0.95:0.4}
      Rectangle {anchors.centerIn:parent;width:4;height:4;radius:2;color:modelData.urgent?"#efb45a":root.cyan}
      Rectangle {visible:modelData.focused;anchors.centerIn:parent;width:parent.size;height:width;radius:width/2;color:"transparent";border.color:root.cyan;border.width:1;opacity:0.2+root.breath*0.2}
      Repeater {
        model:Math.min(5,(modelData.group||[]).length)
        delegate:Rectangle {
          required property int index
          x:parent.size/2+Math.cos(index*Math.PI*2/Math.max(1,parent.modelData.group.length))*Math.max(0,parent.size/2-2)-1
          y:parent.size/2+Math.sin(index*Math.PI*2/Math.max(1,parent.modelData.group.length))*Math.max(0,parent.size/2-2)-1
          width:2;height:2;radius:1;color:Color.foreground;opacity:0.8
        }
      }
    }
  }
  readonly property var pulsePath: {
    var match=graph.paths.filter(function(p){return p.kind==="focus"&&p.id===controller.pulseFrom+":"+controller.pulseTo})
    if(match.length)return match[0].points
    var arrival=graph.paths.filter(function(p){return p.id==="root:"+controller.pulseTo})
    return arrival.length?arrival[0].points:[]
  }
  property real travel: 0
  NumberAnimation {id:pulse;target:root;property:"travel";from:0;to:1;duration:900;easing.type:Easing.InOutSine}
  Item {
    objectName:"focusPulse"
    visible:pulse.running&&root.motion&&root.pulsePath.length>0
    readonly property var p:Topology.sample(root.pulsePath,root.travel)
    x:{var point=p;return point?point.x:0}
    y:{var point=p;return point?point.y:0}
    Rectangle {x:-3;y:-3;width:6;height:6;radius:3;color:root.cyan;opacity:0.3}
    Rectangle {x:-1.5;y:-1.5;width:3;height:3;radius:2;color:Color.foreground}
  }
  // Portals are only navigation chrome in explicit Trace mode.
  Repeater {
    model:root.traceMode?root.graph.portals:[]
    delegate:Rectangle {
      required property var modelData
      x:modelData.x;y:modelData.y-18;width:80;height:34;radius:7
      color:Qt.tint(Color.background,Qt.rgba(root.cyan.r,root.cyan.g,root.cyan.b,0.08));border.color:Qt.rgba(root.cyan.r,root.cyan.g,root.cyan.b,0.45);border.width:1
      Rectangle {x:9;y:8;width:17;height:17;radius:4;rotation:45;color:"transparent";border.color:root.cyan;border.width:1;opacity:0.65}
      Text {x:33;y:6;width:40;text:modelData.name;font.family:Style.font.family;font.pixelSize:10;color:Color.foreground;elide:Text.ElideRight;horizontalAlignment:Text.AlignHCenter}
      Text {x:33;y:20;width:40;text:"PORTAL";font.family:Style.font.family;font.pixelSize:6;font.letterSpacing:1;color:root.cyan;horizontalAlignment:Text.AlignHCenter;opacity:0.75}
      MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:{root.controller.focusWorkspace(modelData.id);root.workspaceChosen()}}
    }
  }
}

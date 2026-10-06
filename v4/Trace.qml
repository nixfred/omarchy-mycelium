import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui
import "Topology.js" as Topology

// Trace: every workspace as a scaled miniature of its monitor. Click a window
// to jump to it on any workspace, or a workspace to switch. Roots beneath the
// tiles link workspaces you recently moved between.
Item {
  id:root
  property string omarchyPath: ""
  property var shell: null
  property var manifest: null
  property var pluginRegistry: null
  property var controllerOverride: null
  property bool opened: false
  property var windows: []
  readonly property var entries:DesktopEntries.applications.values
  readonly property var controller:controllerOverride || (shell?shell.serviceFor("nixfred.mycelium"):null)
  readonly property color amber: "#efb45a"
  function open(payloadJson) {windows.forEach(function(w){w.pageIndex=0});opened=true}
  function close() {opened=false}
  function capture(path,screenName) {
    var matches=windows.filter(function(w){return w.screen.name===screenName})
    if(!matches.length)return false
    matches[0].captureScene(path);return true
  }
  function entryFor(app) {
    // Reading the model is important: byId alone does not invalidate a binding
    // when the application catalog finishes loading after plugin creation.
    var list=root.entries
    var key=(app||"").toLowerCase()
    var matches=list.filter(function(e){return e.id.toLowerCase()===key||e.startupClass.toLowerCase()===key})
    return matches.length?matches[0]:DesktopEntries.byId(app)||DesktopEntries.heuristicLookup(app)
  }
  function iconFor(app) {
    var entry=entryFor(app)
    return entry&&entry.icon?Quickshell.iconPath(entry.icon):""
  }
  function appName(app) {var entry=entryFor(app);return entry&&entry.name?entry.name:app||"Application"}
  Variants {
    model:Quickshell.screens
    PanelWindow {
      id:win
      required property var modelData
      Component.onCompleted: root.windows=root.windows.concat([win])
      Component.onDestruction: root.windows=root.windows.filter(function(w){return w!==win})
      screen:modelData
      readonly property var output:root.controller?(root.controller.frame.monitors||[]).filter(function(m){return m.name===modelData.name})[0]:null
      readonly property bool compact:width<620||height<640
      property int pageIndex:0
      readonly property var forest:root.controller?Topology.forest(root.controller.frame,root.controller.hops,{x:0,y:0,w:forestArea.width,h:forestArea.height},pageIndex,compact?110:170):{tiles:[],roots:[],soil:"",page:0,pages:1,count:0}
      // Clamp the requested page after the map settles; writing it during the
      // forest notification would re-enter the binding.
      onForestChanged:Qt.callLater(function(){if(win.pageIndex!==win.forest.page)win.pageIndex=win.forest.page})
      // Counted from the frame, not the forest: toolbar text height feeds the map area.
      readonly property int workspaceCount:root.controller?(root.controller.frame.workspaces||[]).filter(function(w){return w.id>0}).length:0
      readonly property int windowCount:root.controller?(root.controller.frame.windows||[]).length:0
      readonly property var focusedWindow:root.controller?(root.controller.frame.windows||[]).filter(function(w){return w.id===root.controller.frame.focus})[0]:null
      readonly property int localTiled:root.controller&&output?(root.controller.frame.windows||[]).filter(function(w){return w.monitor===output.id&&w.workspace===output.workspace&&!w.floating}).length:0
      visible:root.opened&&root.controller!==null&&output!==undefined&&output!==null&&!output.off
      anchors {top:true;bottom:true;left:true;right:true}
      color:"transparent";exclusionMode:ExclusionMode.Ignore
      WlrLayershell.namespace:"mycelium-trace"
      WlrLayershell.layer:WlrLayer.Overlay
      WlrLayershell.keyboardFocus:WlrKeyboardFocus.None
      function captureScene(path) {traceScene.grabToImage(function(result){result.saveToFile(path)})}
      Item {
      id:traceScene;objectName:"traceScene";anchors.fill:parent
      // Trace explicitly opts into pointer input; keyboard focus stays with the app.
      Rectangle {anchors.fill:parent;color:Color.background;opacity:0.9}
      MouseArea {anchors.fill:parent;onClicked:root.close()}
      Rectangle {
        id:toolbar;objectName:"traceToolbar"
        anchors.top:parent.top;anchors.topMargin:win.compact?40:54;anchors.horizontalCenter:parent.horizontalCenter
        width:Math.min(parent.width-32,760);height:intro.height+controls.height+(win.compact?24:40);radius:Style.cornerRadius
        color:Color.background;border.color:Color.accent;border.width:1
        MouseArea {anchors.fill:parent}
        Column {id:intro;objectName:"traceIntro";anchors.left:parent.left;anchors.right:parent.right;anchors.margins:18;anchors.top:parent.top;anchors.topMargin:win.compact?8:15;spacing:win.compact?3:7
          Text {width:parent.width;wrapMode:Text.WordWrap;text:win.compact?"MYCELIUM":"MYCELIUM  /  YOUR WINDOW MAP";font.family:Style.font.family;font.pixelSize:win.compact?12:14;font.letterSpacing:win.compact?0:1;color:Color.foreground}
          Text {visible:!win.compact;width:parent.width;text:"Every workspace at a glance. Roots on your screen follow the seams between windows; here they link the workspaces you move between.";wrapMode:Text.WordWrap;font.family:Style.font.family;font.pixelSize:11;color:Color.foreground;opacity:0.85}
          Text {width:parent.width;text:(win.compact||!root.controller?"":root.controller.outputStatus(modelData.name,win.localTiled)+" · ")+win.workspaceCount+" workspaces · "+win.windowCount+" windows";wrapMode:Text.WordWrap;font.family:Style.font.family;font.pixelSize:11;color:Color.accent}
        }
        Row {id:controls;objectName:"tracePreferences";anchors.right:parent.right;anchors.rightMargin:12;anchors.bottom:parent.bottom;anchors.bottomMargin:win.compact?8:10;spacing:8
          Ui.Button {width:win.compact?Math.min(64,Math.max(48,(toolbar.width-116)/3)):Math.min(82,Math.max(1,(toolbar.width-40)/3));fontSize:11;horizontalPadding:6;text:root.controller&&root.controller.unavailable?"Retry":root.controller&&root.controller.paused?"Resume":"Pause";onClicked:{if(root.controller.unavailable)root.controller.resync();else root.controller.setPreference("paused",!root.controller.paused)}}
          Ui.Button {width:win.compact?Math.min(64,Math.max(48,(toolbar.width-116)/3)):Math.min(82,Math.max(1,(toolbar.width-40)/3));fontSize:11;horizontalPadding:6;text:"Still";selected:root.controller&&root.controller.reducedMotion;tooltipText:"Keep roots visible without animation";onClicked:root.controller.setPreference("reducedMotion",!root.controller.reducedMotion)}
          Ui.Button {width:win.compact?Math.min(64,Math.max(48,(toolbar.width-116)/3)):Math.min(82,Math.max(1,(toolbar.width-40)/3));fontSize:11;horizontalPadding:6;text:"Done";onClicked:root.close()}
        }
      }
      Text {
        id:legend;objectName:"traceLegend"
        anchors.bottom:parent.bottom;anchors.bottomMargin:win.compact?10:22;anchors.horizontalCenter:parent.horizontalCenter
        width:Math.min(parent.width-40,700);visible:win.height>=420
        text:win.compact?"Click a window or a workspace. Amber means attention.":"Click a window to jump to it, or a workspace to switch. Bright roots link workspaces you moved between recently. Amber means attention."
        wrapMode:Text.WordWrap;horizontalAlignment:Text.AlignHCenter;font.family:Style.font.family;font.pixelSize:10;color:Color.foreground;opacity:0.75
      }
      Item {
        id:forestArea;objectName:"forestArea"
        x:win.compact?12:32;width:parent.width-x*2
        y:toolbar.y+toolbar.height+(win.compact?10:28)
        // Pager space is always reserved so its appearance cannot resize the map.
        height:Math.max(0,(legend.visible?legend.y:win.height)-y-(win.compact?8:20)-42)
        // Gutter seams, and the hop roots that run along them.
        Shape {
          anchors.fill:parent;preferredRendererType:Shape.CurveRenderer
          ShapePath {strokeColor:Qt.rgba(Color.accent.r,Color.accent.g,Color.accent.b,0.2);strokeWidth:1;fillColor:"transparent";capStyle:ShapePath.RoundCap;PathSvg {path:win.forest.soil}}
        }
        Repeater {
          model:win.forest.roots
          delegate:Shape {
            required property var modelData
            anchors.fill:parent;preferredRendererType:Shape.CurveRenderer
            opacity:modelData.last?0.95:Math.min(0.75,0.35+modelData.count*0.1)
            ShapePath {strokeColor:Color.accent;strokeWidth:Math.min(4,1.2+modelData.count*0.6);fillColor:"transparent";capStyle:ShapePath.RoundCap;joinStyle:ShapePath.RoundJoin;PathSvg {path:modelData.svg}}
          }
        }
        Repeater {
          model:win.forest.tiles
          delegate:Item {
            id:tile
            required property var modelData
            x:modelData.x;y:modelData.y-20;width:modelData.w;height:modelData.h+20
            Text {
              width:parent.width;height:18;elide:Text.ElideRight;verticalAlignment:Text.AlignVCenter
              readonly property bool narrow:tile.modelData.w<220
              text:(narrow?"WS ":"Workspace ")+tile.modelData.name+(tile.modelData.current?(narrow?" · here":"  ·  here"):"")+(narrow?" · "+tile.modelData.windows.length:"  ·  "+tile.modelData.windows.length+(tile.modelData.windows.length===1?" window":" windows"))
              font.family:Style.font.family;font.pixelSize:11;color:tile.modelData.urgent?root.amber:tile.modelData.focused?Color.accent:Color.foreground;opacity:tile.modelData.current?1:0.75
            }
            Rectangle {
              objectName:"workspace-"+tile.modelData.id
              y:20;width:tile.modelData.w;height:tile.modelData.h;radius:8;clip:true
              color:Qt.tint(Color.background,Qt.rgba(Color.accent.r,Color.accent.g,Color.accent.b,tile.modelData.current?0.1:0.04))
              border.width:tile.modelData.focused?2:1
              border.color:tile.modelData.urgent?root.amber:tile.modelData.current?Color.accent:tileHover.containsMouse?Qt.rgba(Color.accent.r,Color.accent.g,Color.accent.b,0.6):Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,0.18)
              MouseArea {id:tileHover;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:{root.controller.focusWorkspace(tile.modelData.id);root.close()}}
              Text {visible:tile.modelData.windows.length===0;anchors.centerIn:parent;text:"empty";font.family:Style.font.family;font.pixelSize:10;color:Color.foreground;opacity:0.45}
              Repeater {
                model:tile.modelData.windows
                delegate:Rectangle {
                  id:mini
                  required property var modelData
                  objectName:"window-"+modelData.id
                  readonly property real iconSize:Math.min(32,width-10,height-(height>=56?24:10))
                  x:modelData.x+1;y:modelData.y+1;width:Math.max(4,modelData.w-2);height:Math.max(4,modelData.h-2);radius:5
                  color:Qt.tint(Color.background,Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,miniHover.containsMouse?0.12:0.06))
                  border.width:modelData.urgent||modelData.focused?2:1
                  border.color:modelData.urgent?root.amber:modelData.focused?Color.accent:miniHover.containsMouse?Qt.rgba(Color.accent.r,Color.accent.g,Color.accent.b,0.7):Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,0.28)
                  Image {id:icon;objectName:"appIcon";visible:mini.iconSize>=12;width:mini.iconSize;height:width;anchors.horizontalCenter:parent.horizontalCenter;y:(parent.height-height-(name.visible?16:0))/2;source:root.iconFor(mini.modelData.app);sourceSize.width:64;sourceSize.height:64;smooth:true}
                  Text {visible:mini.iconSize>=12&&icon.status!==Image.Ready;anchors.fill:icon;text:(mini.modelData.app||"?").charAt(0).toUpperCase();font.pixelSize:Math.max(8,mini.iconSize*0.6);color:Color.accent;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter}
                  Text {id:name;visible:parent.height>=56&&parent.width>=64;x:4;width:parent.width-8;y:icon.y+icon.height+3;text:root.appName(mini.modelData.app);elide:Text.ElideRight;horizontalAlignment:Text.AlignHCenter;font.family:Style.font.family;font.pixelSize:10;color:mini.modelData.urgent?root.amber:Color.foreground;opacity:0.9}
                  MouseArea {id:miniHover;anchors.fill:parent;hoverEnabled:true;cursorShape:Qt.PointingHandCursor;onClicked:{root.controller.focusWindow(mini.modelData.id);root.close()}}
                }
              }
            }
          }
        }
        Text {visible:win.forest.count===0;anchors.centerIn:parent;text:"No workspaces reported yet.";font.family:Style.font.family;font.pixelSize:11;color:Color.foreground}
      }
      Item {
        objectName:"pageControls";visible:win.forest.pages>1
        anchors.horizontalCenter:parent.horizontalCenter;y:forestArea.y+forestArea.height+8;width:248;height:32
        MouseArea {anchors.fill:parent}
        Row {anchors.fill:parent;spacing:8
        Ui.Button {objectName:"previousPage";text:"Previous";width:78;height:32;fontSize:11;horizontalPadding:6;enabled:win.pageIndex>0;opacity:enabled?1:0.4;onClicked:win.pageIndex--}
        Text {objectName:"pageLabel";width:92;height:32;text:"Page "+(win.pageIndex+1)+" / "+win.forest.pages;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.family:Style.font.family;font.pixelSize:11;color:Color.foreground}
        Ui.Button {objectName:"nextPage";text:"Next";width:62;height:32;fontSize:11;horizontalPadding:6;enabled:win.pageIndex+1<win.forest.pages;opacity:enabled?1:0.4;onClicked:win.pageIndex++}
        }
      }
      }
    }
  }
}

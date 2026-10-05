import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Ui as Ui

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
    var key=app.toLowerCase()
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
      readonly property var localWindows:root.controller && output?(root.controller.frame.windows||[]).filter(function(w){return w.monitor===output.id&&w.workspace===output.workspace}):[]
      readonly property bool compact:width<620||height<640
      property int pageIndex:0
      readonly property int pageRows:Math.max(0,Math.floor((appDeck.height-36+12)/56))
      readonly property int pageSize:Math.max(1,cardColumns*pageRows)
      readonly property int pageCount:Math.max(1,Math.ceil(cards.length/pageSize))
      readonly property var pageCards:stackedCards?cards.slice(pageIndex*pageSize,(pageIndex+1)*pageSize):cards
      function clampPage(){pageIndex=Math.max(0,Math.min(pageIndex,pageCount-1))}
      onPageCountChanged:clampPage()
      readonly property int outputWorkspace:output?output.workspace:-1
      onOutputWorkspaceChanged:pageIndex=0
      readonly property real cardWidth:Math.min(148,Math.max(1,width-24))
      readonly property int cardColumns:Math.max(1,Math.floor((width-24)/(cardWidth+12)))
      readonly property var cards:localWindows.map(function(w,i){
        var node=network.graph.nodes.filter(function(n){return n.id===w.id})[0]
        return {id:w.id,app:w.app,urgent:w.urgent,focused:w.id===root.controller.frame.focus,
          x:Math.max(12,Math.min(win.width-win.cardWidth-12,node?node.x+14:24+(i%win.cardColumns)*(win.cardWidth+12))),
          y:Math.max(appDeck.y,Math.min(appDeck.y+appDeck.height-44,node?node.y-21:appDeck.y+Math.floor(i/win.cardColumns)*56))}
      })
      readonly property bool stackedCards:cards.some(function(c,i){return cards.slice(0,i).some(function(p){return Math.abs(c.x-p.x)<win.cardWidth+8&&Math.abs(c.y-p.y)<52})})
      readonly property var output:root.controller?(root.controller.frame.monitors||[]).filter(function(m){return m.name===modelData.name})[0]:null
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
      Rectangle {anchors.fill:parent;color:Color.background;opacity:0.14}
      MouseArea {anchors.fill:parent;onClicked:root.close()}
      Network {id:network;anchors.fill:parent;controller:root.controller;screenName:modelData.name;traceMode:true;renderingEnabled:root.opened;onWorkspaceChosen:root.close()}
      Rectangle {
        id:toolbar;objectName:"traceToolbar"
        anchors.top:parent.top;anchors.topMargin:win.compact?40:54;anchors.horizontalCenter:parent.horizontalCenter
        width:Math.min(parent.width-32,760);height:win.compact?intro.height+12:intro.height+controls.height+40;radius:Style.cornerRadius
        color:Color.background;border.color:Color.accent;border.width:1
        Column {id:intro;objectName:"traceIntro";anchors.left:parent.left;anchors.right:parent.right;anchors.margins:18;anchors.top:parent.top;anchors.topMargin:win.compact?8:15;spacing:win.compact?3:7
          Text {width:win.compact?parent.width-controls.width-8:parent.width;wrapMode:Text.WordWrap;text:win.compact?"MYCELIUM":"MYCELIUM  /  YOUR WINDOW MAP";font.family:Style.font.family;font.pixelSize:win.compact?12:14;font.letterSpacing:win.compact?0:1;color:Color.foreground}
          Text {visible:!win.compact;width:parent.width;text:"Roots grow in the gaps around your windows. Switching apps sends a focus pulse; opening, closing or moving windows reshapes the roots.";wrapMode:Text.WordWrap;font.family:Style.font.family;font.pixelSize:11;color:Color.foreground;opacity:0.85}
          Text {width:win.compact?parent.width-controls.width-8:parent.width;text:win.width<420?win.localWindows.length+" apps\nWS "+(win.output?win.output.workspace:"?"):(win.compact?"":root.controller.outputStatus(modelData.name,network.graph.nodes.length)+" · ")+win.localWindows.length+" apps on workspace "+(win.output?win.output.workspace:"?");wrapMode:Text.WordWrap;font.family:Style.font.family;font.pixelSize:11;color:Color.accent}
        }
        Row {id:controls;objectName:"tracePreferences";anchors.right:parent.right;anchors.rightMargin:12;anchors.top:win.compact?parent.top:undefined;anchors.topMargin:8;anchors.bottom:win.compact?undefined:parent.bottom;anchors.bottomMargin:10;spacing:8
          Ui.Button {width:win.compact?Math.min(64,Math.max(48,(toolbar.width-116)/3)):Math.min(82,Math.max(1,(toolbar.width-40)/3));fontSize:11;horizontalPadding:6;text:root.controller&&root.controller.unavailable?"Retry":root.controller&&root.controller.paused?"Resume":"Pause";onClicked:{if(root.controller.unavailable)root.controller.resync();else root.controller.setPreference("paused",!root.controller.paused)}}
          Ui.Button {width:win.compact?Math.min(64,Math.max(48,(toolbar.width-116)/3)):Math.min(82,Math.max(1,(toolbar.width-40)/3));fontSize:11;horizontalPadding:6;text:"Still";selected:root.controller&&root.controller.reducedMotion;tooltipText:"Keep roots visible without animation";onClicked:root.controller.setPreference("reducedMotion",!root.controller.reducedMotion)}
          Ui.Button {width:win.compact?Math.min(64,Math.max(48,(toolbar.width-116)/3)):Math.min(82,Math.max(1,(toolbar.width-40)/3));fontSize:11;horizontalPadding:6;text:"Done";onClicked:root.close()}
        }
      }

      Rectangle {
        id:legend;objectName:"traceLegend"
        anchors.bottom:parent.bottom;anchors.bottomMargin:66+Math.max(0,Math.ceil(network.graph.portals.length/Math.max(1,Math.floor((parent.width-32)/92)))-1)*35;anchors.horizontalCenter:parent.horizontalCenter
        width:Math.min(parent.width-40,660);height:win.height<480?0:legendText.implicitHeight+18;visible:height>0;radius:7;color:Color.background
        border.color:Qt.rgba(Color.accent.r,Color.accent.g,Color.accent.b,0.25)
        Text {id:legendText;width:parent.width-18;anchors.centerIn:parent;text:win.compact?"Choose an app or workspace. Amber means attention.":(win.stackedCards?"Apps share screen space; use the page controls. ":"Click an app or a workspace to enter it. ")+"Roots show layout; links show observed focus switches or real groups. Amber means attention.";wrapMode:Text.WordWrap;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.family:Style.font.family;font.pixelSize:10;color:Color.foreground;opacity:0.8}
      }
      Item {
        id:appDeck;objectName:"appDeck";x:0;y:toolbar.y+toolbar.height+(win.compact?4:12);width:parent.width;height:Math.max(0,legend.y-y-(win.compact?4:12))
        clip:true
      MouseArea {anchors.fill:parent;onClicked:root.close()}
      Repeater {
        model:win.pageRows>0||!win.stackedCards?win.pageCards:[]
        delegate:Rectangle {
          required property var modelData
          required property int index
          objectName:"window-"+modelData.id
          x:win.stackedCards?12+(index%win.cardColumns)*(win.cardWidth+12):modelData.x;y:win.stackedCards?Math.floor(index/win.cardColumns)*56:modelData.y-appDeck.y
          width:win.cardWidth;height:44;radius:7;color:Color.background
          border.width:1;border.color:modelData.urgent?"#efb45a":modelData.focused?Color.accent:Qt.rgba(Color.foreground.r,Color.foreground.g,Color.foreground.b,0.22)
          Image {id:icon;visible:parent.width>=100;objectName:"appIcon";x:9;y:10;width:24;height:24;source:root.iconFor(modelData.app);sourceSize.width:24;sourceSize.height:24}
          Text {visible:parent.width>=100&&icon.status!==Image.Ready;x:9;y:10;width:24;height:24;text:modelData.app.charAt(0).toUpperCase();font.pixelSize:17;color:Color.accent;horizontalAlignment:Text.AlignHCenter}
          Text {x:parent.width>=100?42:9;y:8;width:Math.max(0,parent.width-x-8);text:root.appName(modelData.app);font.family:Style.font.family;font.pixelSize:11;color:Color.foreground;elide:Text.ElideRight}
          Text {x:parent.width>=100?42:9;y:25;width:Math.max(0,parent.width-x-8);elide:Text.ElideRight;text:modelData.urgent?"Attention":modelData.focused?"Focused":"Enter app";font.family:Style.font.family;font.pixelSize:9;color:modelData.urgent?"#efb45a":Color.accent;opacity:0.8}
          MouseArea {anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:{root.controller.focusWindow(modelData.id);root.close()}}
        }
      }
      Item {
        objectName:"pageControls";visible:win.stackedCards&&win.pageRows>0
        anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;width:248;height:32
        MouseArea {anchors.fill:parent}
        Row {anchors.fill:parent;spacing:8
        Ui.Button {objectName:"previousPage";text:"Previous";width:78;height:32;fontSize:11;horizontalPadding:6;enabled:win.pageIndex>0;opacity:enabled?1:0.4;onClicked:win.pageIndex--}
        Text {objectName:"pageLabel";width:92;height:32;text:"Page "+(win.pageIndex+1)+" / "+win.pageCount;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.family:Style.font.family;font.pixelSize:11;color:Color.foreground}
        Ui.Button {objectName:"nextPage";text:"Next";width:62;height:32;fontSize:11;horizontalPadding:6;enabled:win.pageIndex+1<win.pageCount;opacity:enabled?1:0.4;onClicked:win.pageIndex++}
        }
      }
      Text {visible:win.stackedCards&&win.pageRows===0;anchors.fill:parent;text:"More room is needed to show app cards. Enlarge this display or lower its scale.";wrapMode:Text.WordWrap;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;font.family:Style.font.family;font.pixelSize:11;color:Color.foreground}
      }
      }
    }
  }
}

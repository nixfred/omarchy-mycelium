import QtQuick
import QtQuick.Shapes
import qs.Ui
import qs.Commons

BarWidget {
  id:root
  moduleName:"nixfred.mycelium"
  readonly property var controller:bar&&bar.shell?bar.shell.serviceFor(moduleName):null
  implicitWidth:34
  implicitHeight:barSize
  WidgetButton {
    anchors.fill:parent;bar:root.bar;hasVisualContent:true;labelVisible:false
    tooltipText:root.controller?"Mycelium · "+root.controller.outputStatus("")+(root.controller.anyUrgent?"\nA window wants attention.":"")+"\nClick for the map of every workspace. Right-click to "+(root.controller.paused?"resume.":"pause."):"Mycelium · waiting for desktop connection"
    onPressed:button => {
      if(!root.controller)return
      if(button===Qt.RightButton)root.controller.setPreference("paused",!root.controller.paused)
      else root.controller.trace()
    }
    Rectangle {anchors.right:parent.right;anchors.rightMargin:4;anchors.bottom:parent.bottom;anchors.bottomMargin:5;width:4;height:4;radius:2
      color:root.controller&&(root.controller.anyUrgent||root.controller.unavailable||root.controller.paused)?"#efb45a":Color.accent
      opacity:root.controller&&(root.controller.anyUrgent||!root.controller.settled)?1:0.4
    }
    Shape {anchors.centerIn:parent;width:22;height:22;opacity:root.controller&&root.controller.paused?0.4:0.9
      ShapePath {strokeColor:Color.accent;strokeWidth:1.3;fillColor:"transparent";capStyle:ShapePath.RoundCap
        PathSvg {path:"M 11 20 C 11 15 11 8 11 3 M 11 12 Q 4 12 3 5 M 11 15 Q 19 14 20 6 M 11 8 Q 15 7 17 3"}
      }
    }
  }
}

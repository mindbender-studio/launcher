import QtQuick 2.6
import "icons.js" as Icons

Item {
    id: root

    property string name

    property bool rotate: root.name.match(/.*-rotate/) !== null
    property bool shadow: false

    property var icons: Icons.map

    width: 28
    height: 28

    Image {
        id: image
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom

        source: root.icons.hasOwnProperty(name) ? res_path+root.icons[name] : ""
        fillMode: Image.PreserveAspectFit

        NumberAnimation on rotation {
            running: root.rotate
            from: 0
            to: 360
            loops: Animation.Infinite
            duration: 1100
        }
    }
}

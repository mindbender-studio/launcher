import QtQuick 2.6

import "awesome.js" as Awesome


Item {
    id: root

    property string name
    property bool rotate: root.name.match(/.*-rotate/) !== null

    property alias color: text.color
    property int size: 16

    property bool shadow: false

    property var icons: Awesome.map

    property alias weight: text.font.weight

    width: text.width
    height: text.height

    FontLoader { id: fontAwesome; source: Qt.resolvedUrl("../res/font/fontawesome/FontAwesome.otf") }

    Text {
        id: text
        anchors.centerIn: parent

        property string name: root.name.match(/.*-rotate/) !== null ? root.name.substring(0, root.name.length - 7) : root.name

        font.family: fontAwesome.name
        font.weight: Font.Light
        text: root.icons.hasOwnProperty(name) ? root.icons[name] : ""
        color: "#eee"
        style: shadow ? Text.Raised : Text.Normal
        styleColor: Qt.rgba(0,0,0,0.5)
        font.pixelSize: root.size

        Behavior on color {
            ColorAnimation { duration: 200 }
        }

        NumberAnimation on rotation {
            running: root.rotate
            from: 0
            to: 360
            loops: Animation.Infinite
            duration: 1100
        }
    }
}

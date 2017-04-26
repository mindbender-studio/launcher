import QtQuick 2.7
import QtQuick.Controls 2.1

ToolBar {
    height: 30

    background: Rectangle {
        color: "transparent"
        border.color: "#222"
        anchors.margins: 2

        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            color: "transparent"
            border.color: "#555"
        }
    }
}
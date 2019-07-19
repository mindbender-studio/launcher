import QtQuick 2.6
import QtQuick.Controls 2.0


Item {
    id: root

    property var model

    Row {
        anchors.fill: parent

        ToolButton {
            contentItem: AwesomeIcon {
                name: "home"
                size: 18
            }
            background: Item { }  // Hide background
            height: parent.height
            width: parent.height
            onClicked: controller.pop(-1)
        }

        Repeater {
            id: repeater
            model: root.model
            delegate: ToolButton {
                id: control

                background: Item { }  // Hide background

                contentItem: Text {
                    text: modelData
                    font: control.font
                    color: control.down ? "#aaa" : "#fff"
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                }

                height: parent.height
                font.pixelSize: 10
                onClicked: controller.pop(index)
            }
        }
    }
}
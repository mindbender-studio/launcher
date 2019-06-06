import QtQuick 2.6
import QtQuick.Controls 2.0
import QtQuick.Layouts 1.3

Flow {
    id: actionLayout

    property variant model

    flow: Grid.LeftToRight
    spacing: 3

    Repeater {
        id: actionRepeater
        model: actionLayout.model

        delegate: ItemDelegate {
            id: control

            padding: 0
            width: 55
            height: 65

            contentItem: ColumnLayout {

                ImageAction {
                    id: actionImage
                    property int availableWidth: control.availableWidth

                    name: model.icon
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: actiontext.top
                }

                AwesomeIcon {
                    id: actionIcon
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.top: parent.top
                    name: model.icon
                    size: 28
                    color: model.color ? model.color : "white"
                }

                Text {
                    id: actiontext
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    width: control.availableWidth
                    Layout.alignment: Qt.AlignTop | Qt.AlignHCenter

                    text: model.label || model.name
                    color: "#eee"
                    font.pixelSize: 11

                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignTop

                }
            }

            background: Rectangle {
                opacity: control.down ? 0.3 : 0.0
                color: "white"
            }

            onClicked: controller.trigger_action(actionRepeater.model.index(index, null))
        }
    }
}

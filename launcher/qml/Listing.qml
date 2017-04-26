import QtQuick 2.6
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.3

Page {
    id: root

    property var model

    background: Rectangle { color: "transparent" }

    contentItem: ListView {
        id: listView

        model: root.model
        anchors.fill: parent

        delegate: ItemDelegate {
            id: control
            height: 20

            contentItem: RowLayout {
                anchors.fill: parent
                spacing: 2
                Layout.alignment: Qt.AlignLeft

                Image {
                    source: "../res/%1".arg(modelData.icon)
                    fillMode: Image.PreserveAspectFit
                    Layout.fillHeight: true
                    Layout.margins: 2
                    Layout.maximumWidth: height
                }

                Text {
                    text: modelData.label
                    color: "#eee"
                    font: control.font
                    Layout.fillHeight: true
                    Layout.fillWidth: true
                    Layout.margins: 0
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignLeft
                }
            }

            background: Rectangle {
                opacity: control.down ? 0.3 : 0.0
                color: "white"
            }

            width: listView.width - listView.leftMargin - listView.rightMargin
            onClicked: controller.push(modelData)
        }
    }
}
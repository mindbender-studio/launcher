import QtQuick 2.6
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.3

ColumnLayout {
    id: root

    property var model

    spacing: 2

    Label {
        Layout.fillWidth: true
        text: "Environment"
        color: "white"
        lineHeight: 1.5
        font.pointSize: 12
        height: 20
    }

    Repeater {
        model: root.model
        Layout.fillWidth: true

        delegate: RowLayout {
            height: 20
            spacing: 5

            Label {
                Layout.alignment: Text.AlignRight

                color: "#eee"
                text: modelData.key
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignRight
            }

            TextField {
                id: control
                Layout.fillWidth: true

                readOnly: true
                selectByMouse: true
                width: 50
                color: "#eee"
                text: modelData.value || ""
                verticalAlignment: Text.AlignVCenter
                horizontalAlignment: Text.AlignLeft

                selectionColor: "#444"
                selectedTextColor: "#eee"

                background: Rectangle {
                    color: control.enabled ? Qt.rgba(0, 0, 0, 0.3) : "#222"
                    border.color: "#222"
                }
            }
        }
    }
    Item {
        id: _filler
        Layout.fillHeight: true
        Layout.fillWidth: true
    }
}
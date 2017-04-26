import QtQuick 2.6
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.3

Page {
    id: root

    property string label
    property var model

    background: Rectangle { color: "transparent" }

    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 5

        Environment {
            model: root.model
        }
    }
}
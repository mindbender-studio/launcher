import QtQuick 2.7
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.3


ApplicationWindow {
    id: window
    title: "Mindbender Launcher"

    visible: true
    width: 500
    height: 500
    color: "#444"

    header: MyToolBar {
        RowLayout {
            anchors.fill: parent

            Breadcrumbs {
                Layout.fillHeight: true
                Layout.fillWidth: true
                model: controller.breadcrumbs
            }

            /** Toggle Terminal on/off
             */
            MyButton {
                id: terminalButton
                icon: "terminal"
                checkable: true
                implicitHeight: parent.height
                implicitWidth: parent.height
                Layout.alignment: Qt.AlignRight
            }

            /** Toggle Attribute Editor on/off
             */
            MyButton {
                id: attributeEditorButton
                implicitWidth: parent.height
                implicitHeight: parent.height
                checkable: true
                icon: "adjust"
                Layout.alignment: Qt.AlignRight
            }
        }
    }

    footer: MyToolBar { }


    /** Main Layout
     *  ____________________
     * |          |         |
     * |          |         |
     * |          |         |
     * |__________|_________|
     * |                    |
     * |                    |
     * |____________________|
     *
     */
    Rectangle {
        id: browserContainer
        border.color: "#222"
        color: "#333"

        anchors {
            top: parent.top
            bottom: terminalContainer.top
            right: attributeEditorContainer.left
            left: parent.left
        }

        StackView {
            id: browser
            clip: true
            anchors.fill: parent
            anchors.margins: 2
        }
    }

    Rectangle {
        id: attributeEditorContainer

        color: "#333"
        border.color: "#222"

        anchors {
            top: parent.top
            bottom: terminalContainer.top
            right: parent.right
        }

        width: attributeEditorButton.checked ? parent.width / 2 : 0

        Behavior on width { SmoothedAnimation { velocity: 2000 } }

        visible: width > 0

        Attributes {
            clip: true
            anchors.fill: parent
            anchors.margins: 2
            model: controller.environment
        }
    }

    Rectangle {
        id: terminalContainer

        height: terminalButton.checked ? 200 : 0

        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
        }

        Behavior on height { SmoothedAnimation { velocity: 2000 } }

        border.color: "#222"
        color: "#111"

        clip: true
        visible: height > 0

        ListView {
            id: terminalView
            anchors.fill: parent
            model: terminal
            delegate: Text {
                text: line
                color: "#eee"
                width: ListView.view.width
            }
        }
    }

    /** Respond to changes from controller
     *
     *           ____
     *  ______  /    v  ______
     * |      |        |      |
     * |      |        |      |
     * |______|        |______|
     *          ^____/
     *
     */
    Connections {
        target: controller
        onPushed: browser.push(_listing, { model: items })
        onPopped: browser.pop()
    }

    Connections {
        target: terminal
        onRowsInserted: terminalView.positionViewAtEnd()
    }

    Component {
        id: _listing
        Listing { }
    }
}

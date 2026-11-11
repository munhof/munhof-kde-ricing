import Quickshell
import QtQuick

// Real, content-sized layer-shell surface. Never anchors both horizontal edges.
// No exclusive zone: do not modify KWin/Polonium's tiling work area.
PanelWindow {
    id: panel
    property var entries: []
    property string edge: "top"
    property string horizontalPosition: "center"
    property string currentTime: Qt.formatDateTime(new Date(), "ddd dd · hh:mm")

    anchors {
        top: panel.edge === "top"
        bottom: panel.edge === "bottom"
        left: panel.horizontalPosition === "left"
        right: panel.horizontalPosition === "right"
    }
    margins {
        top: panel.edge === "top" ? 12 : 0
        bottom: panel.edge === "bottom" ? 16 : 0
        left: panel.horizontalPosition === "left" ? 16 : 0
        right: panel.horizontalPosition === "right" ? 16 : 0
    }

    implicitWidth: capsule.implicitWidth
    implicitHeight: capsule.implicitHeight
    color: "transparent"
    focusable: false
    aboveWindows: true
    exclusionMode: ExclusionMode.Ignore

    Rectangle {
        id: capsule
        anchors.fill: parent
        implicitWidth: contents.implicitWidth + 16
        implicitHeight: panel.edge === "bottom" ? 54 : 40
        color: "#e8151a2c"
        border.color: "#916fbbde"
        border.width: 1
        radius: panel.edge === "bottom" ? 18 : 14

        Row {
            id: contents
            anchors.centerIn: parent
            spacing: panel.edge === "bottom" ? 4 : 5

            Repeater {
                model: panel.entries
                delegate: Rectangle {
                    id: item
                    required property var modelData
                    implicitWidth: Math.max(item.modelData.width || 40, label.implicitWidth + 18)
                    implicitHeight: panel.edge === "bottom" ? 44 : 32
                    color: pointer.containsMouse ? "#715480a6" : "transparent"
                    radius: 10

                    Text {
                        id: label
                        anchors.centerIn: parent
                        text: item.modelData.text === "@clock" ? panel.currentTime : item.modelData.text
                        font.family: "JetBrainsMono Nerd Font"
                        font.pixelSize: panel.edge === "bottom" ? 23 : 13
                        font.bold: false
                        color: "#efeaff"
                    }

                    MouseArea {
                        id: pointer
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: !!item.modelData.command
                        onClicked: Quickshell.execDetached(item.modelData.command)
                    }
                }
            }
        }
    }

    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: panel.currentTime = Qt.formatDateTime(new Date(), "ddd dd · hh:mm")
    }
}

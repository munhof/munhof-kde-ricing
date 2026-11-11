import Quickshell
import Quickshell.Wayland
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

    // The LayerShell surface itself, not just the painted rectangle, is compact.
    implicitWidth: Math.ceil(contents.implicitWidth + 24)
    implicitHeight: panel.edge === "bottom" ? 58 : 42
    color: "transparent"
    focusable: false
    aboveWindows: true
    exclusionMode: ExclusionMode.Ignore

    // Identity for compositor diagnostics and Polonium's window-class filters.
    // This is a layer-shell namespace, not proof that KWin exposes a normal window.
    WlrLayershell.namespace: "munhof-rice-island"
    WlrLayershell.layer: WlrLayer.Top

    Rectangle {
        id: capsule
        anchors.fill: parent
        implicitWidth: panel.implicitWidth
        implicitHeight: panel.implicitHeight
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

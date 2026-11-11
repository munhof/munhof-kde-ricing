import Quickshell
import QtQuick

// Experimental island layout for KDE Plasma/KWin Wayland.
// Four small surfaces per connected screen; reacts to hotplug via Variants.
// This prototype does not change Polonium, KScreen, or KDE panel settings.
ShellRoot {
    Variants {
        model: Quickshell.screens
        Island {
            property var modelData
            screen: modelData
            edge: "top"
            horizontalPosition: "left"
            entries: [
                { text: "󰣇", width: 38, command: ["sh", "-c", "exec \"$HOME/.local/bin/munhof-rice-appearance\" launcher"] },
                { text: "●  RICE", width: 86 }
            ]
        }
    }

    Variants {
        model: Quickshell.screens
        Island {
            property var modelData
            screen: modelData
            edge: "top"
            horizontalPosition: "center"
            entries: [
                { text: "KDE  ·  WAYLAND", width: 170 }
            ]
        }
    }

    Variants {
        model: Quickshell.screens
        Island {
            property var modelData
            screen: modelData
            edge: "top"
            horizontalPosition: "right"
            entries: [
                { text: "", width: 36, command: ["krunner"] },
                { text: "@clock", width: 150 }
            ]
        }
    }

    Variants {
        model: Quickshell.screens
        Island {
            property var modelData
            screen: modelData
            edge: "bottom"
            horizontalPosition: "center"
            entries: [
                { text: "󰣇", width: 46, command: ["sh", "-c", "exec \"$HOME/.local/bin/munhof-rice-appearance\" launcher"] },
                { text: "", width: 46, command: ["konsole"] },
                { text: "", width: 46, command: ["xdg-open", "https://duckduckgo.com"] },
                { text: "󰉋", width: 46, command: ["dolphin"] },
                { text: "", width: 46, command: ["krunner"] }
            ]
        }
    }
}

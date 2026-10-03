/* Lucy OS Calamares slideshow — Dinknesh story + human-AI vision.
 * Obsidian background, gold accents. Shown during the install exec phase.
 */
import QtQuick 2.0
import calamares.slideshow 1.0

Presentation {
    id: presentation

    Timer {
        interval: 8000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: presentation.goToNextSlide()
    }

    function onActivate() {}
    function onLeave() {}

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#0b0a08"
            Column {
                anchors.centerIn: parent
                spacing: 12
                Text {
                    text: "1974 · Hadar, Ethiopia"
                    color: "#d4af37"
                    font.pixelSize: 16
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: "Dinknesh · ድንቅነሽ"
                    color: "#f7e8c3"
                    font.pixelSize: 42
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: "A 3.2-million-year-old skeleton that illuminated human origins."
                    color: "#cfc4ae"
                    font.pixelSize: 18
                    anchors.horizontalCenter: parent.horizontalCenter
                    wrapMode: Text.WordWrap
                    width: 640
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#0b0a08"
            Column {
                anchors.centerIn: parent
                spacing: 12
                Text {
                    text: "The Name"
                    color: "#d4af37"
                    font.pixelSize: 16
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: "Lucy"
                    color: "#f7e8c3"
                    font.pixelSize: 42
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: "Named for “Lucy in the Sky with Diamonds”, she became a global icon of discovery."
                    color: "#cfc4ae"
                    font.pixelSize: 18
                    anchors.horizontalCenter: parent.horizontalCenter
                    wrapMode: Text.WordWrap
                    width: 640
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    Slide {
        Rectangle {
            anchors.fill: parent
            color: "#0b0a08"
            Column {
                anchors.centerIn: parent
                spacing: 12
                Text {
                    text: "Human × AI Synergy"
                    color: "#d4af37"
                    font.pixelSize: 16
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: "Lucy OS"
                    color: "#f7e8c3"
                    font.pixelSize: 42
                    font.bold: true
                    anchors.horizontalCenter: parent.horizontalCenter
                }
                Text {
                    text: "An AI-native desktop: offline intelligence, glassmorphic calm, and tools that work out of the box."
                    color: "#cfc4ae"
                    font.pixelSize: 18
                    anchors.horizontalCenter: parent.horizontalCenter
                    wrapMode: Text.WordWrap
                    width: 640
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }
}

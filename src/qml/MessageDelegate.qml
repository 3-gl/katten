// SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Item {
    id: delegate
    width: ListView.view.width
    height: bubble.implicitHeight + Kirigami.Units.largeSpacing

    Rectangle {
        id: bubble
        anchors.top: parent.top
        anchors.left: model.role === "user" ? undefined : parent.left
        anchors.right: model.role === "user" ? parent.right : undefined
        anchors.margins: Kirigami.Units.largeSpacing
        implicitWidth: contentColumn.implicitWidth + 2 * Kirigami.Units.largeSpacing
        width: Math.min(parent.width - 2 * Kirigami.Units.largeSpacing, implicitWidth)
        radius: Kirigami.Units.cornerRadius
        color: model.role === "user" ? Kirigami.Theme.highlightColor : Kirigami.Theme.backgroundColor
        border.width: 1
        border.color: model.error ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.disabledTextColor

        ColumnLayout {
            id: contentColumn
            anchors.fill: parent
            anchors.margins: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.smallSpacing

            Controls.Label {
                Layout.fillWidth: true
                text: (model.role === "user" ? i18n("You") : i18n("Vibe")) + " · " + model.timestamp
                font: Kirigami.Theme.smallFont
                color: model.role === "user" ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.disabledTextColor
            }

            TextEdit {
                Layout.fillWidth: true
                visible: model.role !== "user"
                readOnly: true
                selectByMouse: true
                textFormat: TextEdit.RichText
                wrapMode: TextEdit.Wrap
                text: model.html
                color: model.error ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor
                onLinkActivated: (link) => Qt.openUrlExternally(link)
            }

            Kirigami.SelectableLabel {
                Layout.fillWidth: true
                visible: model.role === "user"
                text: model.text
                wrapMode: Text.Wrap
                color: Kirigami.Theme.highlightedTextColor
            }

            Controls.Label {
                visible: model.pending
                text: i18n("Thinking…")
                font: Kirigami.Theme.smallFont
                color: model.role === "user" ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.disabledTextColor
            }

            RowLayout {
                spacing: Kirigami.Units.smallSpacing

                Controls.ToolButton {
                    icon.name: "edit-copy"
                    Controls.ToolTip.text: i18n("Copy to clipboard")
                    Controls.ToolTip.visible: hovered
                    onClicked: kattenApp.copyToClipboard(model.text)
                }
                Controls.ToolButton {
                    icon.name: "view-refresh"
                    visible: model.role !== "user"
                    Controls.ToolTip.text: i18n("Retry")
                    Controls.ToolTip.visible: hovered
                    onClicked: kattenApp.retryLast()
                }
            }
        }
    }
}

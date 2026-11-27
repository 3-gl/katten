// SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page {
    id: chatPage
    title: kattenApp.currentTitle.length > 0 ? kattenApp.currentTitle : i18n("Katten")
    padding: 0

    signal openSettingsRequested()

    actions: [
        Kirigami.Action {
            text: i18n("New conversation")
            icon.name: "list-add"
            onTriggered: kattenApp.newConversation()
        },
        Kirigami.Action {
            text: i18n("Delete conversation")
            icon.name: "edit-delete"
            visible: kattenApp.currentConversationId.length > 0
            onTriggered: kattenApp.deleteConversation(kattenApp.currentConversationId)
        },
        Kirigami.Action {
            text: i18n("Settings…")
            icon.name: "settings-configure"
            displayHint: Kirigami.DisplayHint.AlwaysHide
            onTriggered: chatPage.openSettingsRequested()
        }
    ]

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !kattenApp.hasApiKey
            type: Kirigami.MessageType.Warning
            text: i18n("No Mistral API key is configured. Open Settings to store your API key securely in KWallet.")
            actions: [
                Kirigami.Action {
                    text: i18n("Open Settings")
                    icon.name: "settings-configure"
                    onTriggered: chatPage.openSettingsRequested()
                }
            ]
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: kattenApp.lastError.length > 0
            type: Kirigami.MessageType.Error
            text: kattenApp.lastError
        }

        ListView {
            id: messageList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: Kirigami.Units.largeSpacing
            topMargin: Kirigami.Units.largeSpacing
            bottomMargin: Kirigami.Units.largeSpacing
            model: kattenApp.messages
            delegate: MessageDelegate {}
            onCountChanged: Qt.callLater(positionViewAtEnd)
            Controls.ScrollBar.vertical: Controls.ScrollBar {}
        }

        Controls.Label {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.largeSpacing
            visible: messageList.count === 0 && !kattenApp.busy
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.Wrap
            opacity: 0.6
            text: i18n("Ask Vibe anything. Answers support rich text: bold, lists, tables, links, code blocks and charts.")
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing
            visible: kattenApp.hasApiKey

            Controls.TextArea {
                id: inputField
                Layout.fillWidth: true
                Layout.maximumHeight: Kirigami.Units.gridUnit * 6
                placeholderText: i18n("Ask Vibe…")
                wrapMode: Controls.TextArea.Wrap
                enabled: !kattenApp.busy
                Keys.onReturnPressed: (event) => {
                    if (event.modifiers & Qt.ShiftModifier)
                        return
                    if (inputField.text.trim().length > 0) {
                        kattenApp.sendPrompt(inputField.text.trim())
                        inputField.text = ""
                        event.accepted = true
                    }
                }
            }

            Controls.Button {
                text: i18n("Send")
                icon.name: "document-send"
                enabled: inputField.text.trim().length > 0 && !kattenApp.busy
                onClicked: {
                    kattenApp.sendPrompt(inputField.text.trim())
                    inputField.text = ""
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing
            visible: kattenApp.busy

            Controls.BusyIndicator {
                running: true
                implicitWidth: Kirigami.Units.gridUnit
                implicitHeight: Kirigami.Units.gridUnit
            }
            Controls.Label {
                text: i18n("Vibe is thinking…")
            }
        }
    }
}

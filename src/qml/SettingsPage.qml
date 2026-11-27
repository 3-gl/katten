// SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page {
    id: settingsPage
    title: i18n("Settings")

    ColumnLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !kattenApp.hasApiKey
            type: Kirigami.MessageType.Warning
            text: i18n("No API key configured. Katten never stores your key in plain text — it is kept in KWallet.")
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Controls.Label {
                text: i18n("Mistral API key")
                font.bold: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Controls.TextField {
                    id: apiKeyField
                    Layout.fillWidth: true
                    echoMode: Controls.TextInput.Password
                    placeholderText: i18n("Paste your API key from console.mistral.ai")
                }
                Controls.Button {
                    text: i18n("Save in KWallet")
                    icon.name: "document-save"
                    enabled: apiKeyField.text.length > 0
                    onClicked: {
                        if (kattenApp.setApiKey(apiKeyField.text))
                            apiKeyField.text = ""
                    }
                }
                Controls.Button {
                    text: i18n("Clear")
                    icon.name: "edit-delete"
                    enabled: kattenApp.hasApiKey
                    onClicked: kattenApp.clearApiKey()
                }
            }

            Controls.Label {
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                font: Kirigami.Theme.smallFont
                color: Kirigami.Theme.disabledTextColor
                text: i18n("Create a key at console.mistral.ai under “API keys”. The key is stored in the KWallet folder “Katten”. The MISTRAL_API_KEY environment variable is used as a fallback if no key is stored.")
            }

            Controls.Label {
                Layout.fillWidth: true
                visible: kattenApp.lastError.length > 0
                wrapMode: Text.Wrap
                color: Kirigami.Theme.negativeTextColor
                text: kattenApp.lastError
            }
        }

        Kirigami.Separator {
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Controls.Label {
                text: i18n("Model")
            }
            Controls.ComboBox {
                id: modelCombo
                Layout.fillWidth: true
                editable: true
                model: kattenApp.availableModels
                currentIndex: Math.max(0, find(kattenApp.model))
                onActivated: (index) => {
                    if (index >= 0)
                        kattenApp.model = textAt(index)
                }
                onAccepted: {
                    if (currentText.length > 0)
                        kattenApp.model = currentText
                }
                Connections {
                    target: kattenApp
                    function onModelChanged() {
                        modelCombo.currentIndex = Math.max(0, modelCombo.find(kattenApp.model))
                    }
                }
            }
            Controls.Button {
                text: i18n("Reload list")
                icon.name: "view-refresh"
                onClicked: kattenApp.refreshModels()
            }
        }

        Controls.CheckBox {
            text: i18n("Enable web search for new conversations")
            checked: kattenApp.webSearch
            onToggled: kattenApp.webSearch = checked
        }
        Controls.Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            font: Kirigami.Theme.smallFont
            color: Kirigami.Theme.disabledTextColor
            text: i18n("Web search uses Mistral's built-in web_search tool. It is applied when a conversation is created and cannot be changed afterwards.")
        }

        Item {
            Layout.fillHeight: true
        }
    }
}

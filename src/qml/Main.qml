// SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
// SPDX-License-Identifier: GPL-3.0-or-later

import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    width: 960
    height: 680
    minimumWidth: 480
    minimumHeight: 400
    title: i18n("Katten")

    globalDrawer: Kirigami.GlobalDrawer {
        id: drawer
        title: i18n("Katten")
        contentItem: ColumnLayout {
            spacing: 0

            Controls.Button {
                Layout.fillWidth: true
                text: i18n("New conversation")
                icon.name: "list-add"
                onClicked: {
                    kattenApp.newConversation()
                    drawer.close()
                }
            }

            ListView {
                id: conversationList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: kattenApp.conversations
                delegate: Controls.ItemDelegate {
                    width: ListView.view.width
                    text: model.title.length > 0 ? model.title : i18n("New conversation")
                    icon.name: "document-edit"
                    highlighted: model.id === kattenApp.currentConversationId
                    onClicked: {
                        kattenApp.openConversation(model.id)
                        drawer.close()
                    }
                }
                Controls.Label {
                    anchors.centerIn: parent
                    visible: conversationList.count === 0
                    text: i18n("No conversations yet")
                    opacity: 0.6
                }
                Controls.ScrollBar.vertical: Controls.ScrollBar {}
            }

            Controls.Button {
                Layout.fillWidth: true
                text: i18n("Settings…")
                icon.name: "settings-configure"
                onClicked: {
                    root.pageStack.push(settingsPageComponent)
                    drawer.close()
                }
            }
        }
    }

    pageStack.initialPage: ChatPage {
        id: chatPage
        onOpenSettingsRequested: root.pageStack.push(settingsPageComponent)
    }

    Component {
        id: settingsPageComponent
        SettingsPage {}
    }

    contextDrawer: Kirigami.ContextDrawer {}
}

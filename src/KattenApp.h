/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include "ConversationModel.h"
#include "ConversationStore.h"
#include "MessageModel.h"
#include "MistralClient.h"

#include <QObject>
#include <QPointer>
#include <QStringList>

class QWindow;

/**
 * Central application object, exposed to QML as "kattenApp" and to D-Bus as
 * org.kde.katten /Katten (used by the KRunner plugin).
 */
class KattenApp : public QObject
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.kde.katten")

    Q_PROPERTY(ConversationModel *conversations READ conversations CONSTANT)
    Q_PROPERTY(MessageModel *messages READ messages CONSTANT)
    Q_PROPERTY(QString currentConversationId READ currentConversationId NOTIFY currentConversationIdChanged)
    Q_PROPERTY(QString currentTitle READ currentTitle NOTIFY currentConversationIdChanged)
    Q_PROPERTY(bool busy READ busy NOTIFY busyChanged)
    Q_PROPERTY(bool hasApiKey READ hasApiKey NOTIFY hasApiKeyChanged)
    Q_PROPERTY(QString model READ model WRITE setModel NOTIFY modelChanged)
    Q_PROPERTY(bool webSearch READ webSearch WRITE setWebSearch NOTIFY webSearchChanged)
    Q_PROPERTY(QStringList availableModels READ availableModels NOTIFY availableModelsChanged)
    Q_PROPERTY(QString lastError READ lastError NOTIFY lastErrorChanged)

public:
    explicit KattenApp(QObject *parent = nullptr);

    void setMainWindow(QWindow *window);

    ConversationModel *conversations() const;
    MessageModel *messages() const;
    QString currentConversationId() const;
    QString currentTitle() const;
    bool busy() const;
    bool hasApiKey() const;
    QString model() const;
    void setModel(const QString &model);
    bool webSearch() const;
    void setWebSearch(bool on);
    QStringList availableModels() const;
    QString lastError() const;

    Q_INVOKABLE QString newConversation();
    Q_INVOKABLE void openConversation(const QString &id);
    Q_INVOKABLE void deleteConversation(const QString &id);
    Q_INVOKABLE void sendPrompt(const QString &text);
    Q_INVOKABLE void retryLast();
    Q_INVOKABLE bool setApiKey(const QString &key);
    Q_INVOKABLE void clearApiKey();
    Q_INVOKABLE void refreshModels();
    Q_INVOKABLE void copyToClipboard(const QString &text) const;

    // D-Bus interface (used by the KRunner plugin and by D-Bus activation).
    Q_INVOKABLE void openPrompt(const QString &prompt);
    Q_INVOKABLE void raiseWindow();

Q_SIGNALS:
    void currentConversationIdChanged();
    void busyChanged();
    void hasApiKeyChanged();
    void modelChanged();
    void webSearchChanged();
    void availableModelsChanged();
    void lastErrorChanged();

private:
    void setBusy(bool busy);
    void setLastError(const QString &error);
    void handleReply(const QString &serverId, const QString &text);
    void handleError(const QString &error);
    void reloadCurrentMessages();

    ConversationStore m_store;
    ConversationModel *m_conversationModel;
    MessageModel *m_messageModel;
    MistralClient m_client;
    QString m_currentId;
    bool m_busy = false;
    QStringList m_models;
    QString m_lastError;
    QPointer<QWindow> m_window;
};

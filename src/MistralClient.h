/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QJsonObject>
#include <QNetworkAccessManager>
#include <QObject>
#include <QString>
#include <QStringList>
#include <functional>

/**
 * Minimal client for the Mistral API (https://api.mistral.ai/v1).
 *
 * Uses the Conversations API so that multi-turn conversations are supported:
 * a conversation is created with POST /v1/conversations and continued with
 * POST /v1/conversations/{id}/messages, using the conversation_id returned by
 * the server. The built-in web_search tool is enabled per conversation.
 */
class MistralClient : public QObject
{
    Q_OBJECT

public:
    explicit MistralClient(QObject *parent = nullptr);

    void setApiKey(const QString &key);

    // Sends prompt as a new message. If serverConversationId is empty a new
    // conversation is created (with webSearch tool when requested); otherwise
    // the message is appended to the existing server-side conversation.
    void sendMessage(const QString &serverConversationId, const QString &prompt, const QString &model, bool webSearch);
    void fetchModels();

Q_SIGNALS:
    void messageSent(const QString &serverConversationId, const QString &text);
    void messageFailed(const QString &errorMessage);
    void modelsFetched(const QStringList &modelIds);

private:
    void request(const QString &method, const QString &endpoint, const QJsonObject &body,
                 const std::function<void(const QJsonObject &, const QString &)> &callback);
    static QString extractOutputText(const QJsonObject &response);

    QNetworkAccessManager m_nam;
    QString m_apiKey;
};

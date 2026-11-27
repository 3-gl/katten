/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "MistralClient.h"

#include <KLocalizedString>
#include <QJsonArray>
#include <QJsonDocument>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QTimer>
#include <QUrl>

namespace
{
const QUrl kApiBase(QStringLiteral("https://api.mistral.ai/v1/"));
constexpr int kTimeoutMs = 120000;
}

MistralClient::MistralClient(QObject *parent)
    : QObject(parent)
{
}

void MistralClient::setApiKey(const QString &key)
{
    m_apiKey = key;
}

void MistralClient::request(const QString &method, const QString &endpoint, const QJsonObject &body,
                             const std::function<void(const QJsonObject &, const QString &)> &callback)
{
    if (m_apiKey.isEmpty()) {
        callback({}, i18nc("@info", "No Mistral API key configured. Open Settings to store your API key in KWallet."));
        return;
    }

    QNetworkRequest req(kApiBase.resolved(QUrl(endpoint)));
    req.setHeader(QNetworkRequest::ContentTypeHeader, QStringLiteral("application/json"));
    req.setRawHeader("Accept", "application/json");
    req.setRawHeader("Authorization", "Bearer " + m_apiKey.toUtf8());
    req.setTransferTimeout(kTimeoutMs);

    QNetworkReply *reply = method == QLatin1String("GET")
        ? m_nam.get(req)
        : m_nam.sendCustomRequest(req, method.toLatin1(), QJsonDocument(body).toJson(QJsonDocument::Compact));

    QTimer *timer = new QTimer(reply);
    timer->setSingleShot(true);
    connect(timer, &QTimer::timeout, reply, &QNetworkReply::abort);
    timer->start(kTimeoutMs);

    connect(reply, &QNetworkReply::finished, this, [reply, callback]() {
        reply->deleteLater();
        const QByteArray payload = reply->readAll();
        const int status = reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt();
        if (reply->error() != QNetworkReply::NoError || status < 200 || status >= 300) {
            QString message = reply->errorString();
            const QJsonDocument doc = QJsonDocument::fromJson(payload);
            if (doc.isObject()) {
                const QString apiMessage = doc.object().value(QStringLiteral("message")).toString();
                if (!apiMessage.isEmpty())
                    message = apiMessage;
            }
            callback({}, i18nc("@info", "Mistral API error (%1): %2", status > 0 ? QString::number(status) : reply->errorString(), message));
            return;
        }
        const QJsonDocument doc = QJsonDocument::fromJson(payload);
        callback(doc.object(), {});
    });
}

void MistralClient::sendMessage(const QString &serverConversationId, const QString &prompt, const QString &model, bool webSearch)
{
    QJsonObject body;
    body[QStringLiteral("inputs")] = prompt;

    QString endpoint;
    if (serverConversationId.isEmpty()) {
        endpoint = QStringLiteral("conversations");
        body[QStringLiteral("model")] = model;
        if (webSearch) {
            QJsonArray tools;
            tools.append(QJsonObject{{QStringLiteral("type"), QStringLiteral("web_search")}});
            body[QStringLiteral("tools")] = tools;
        }
    } else {
        endpoint = QStringLiteral("conversations/") + serverConversationId + QStringLiteral("/messages");
    }

    request(QStringLiteral("POST"), endpoint, body, [this, serverConversationId](const QJsonObject &response, const QString &error) {
        if (!error.isEmpty()) {
            Q_EMIT messageFailed(error);
            return;
        }
        QString conversationId = response.value(QStringLiteral("conversation_id")).toString();
        if (conversationId.isEmpty())
            conversationId = serverConversationId;
        const QString text = extractOutputText(response);
        if (text.trimmed().isEmpty()) {
            Q_EMIT messageFailed(i18nc("@info", "Vibe returned an empty response."));
            return;
        }
        Q_EMIT messageSent(conversationId, text);
    });
}

QString MistralClient::extractOutputText(const QJsonObject &response)
{
    QString text;
    const QJsonArray outputs = response.value(QStringLiteral("outputs")).toArray();
    for (const QJsonValue &entryValue : outputs) {
        const QJsonObject entry = entryValue.toObject();
        if (entry.value(QStringLiteral("type")).toString() != QLatin1String("message.output"))
            continue;
        const QJsonValue content = entry.value(QStringLiteral("content"));
        if (content.isString()) {
            text += content.toString();
        } else if (content.isArray()) {
            for (const QJsonValue &chunkValue : content.toArray()) {
                const QJsonObject chunk = chunkValue.toObject();
                if (chunk.value(QStringLiteral("type")).toString() == QLatin1String("text"))
                    text += chunk.value(QStringLiteral("text")).toString();
            }
        }
    }
    return text;
}

void MistralClient::fetchModels()
{
    request(QStringLiteral("GET"), QStringLiteral("models"), {}, [this](const QJsonObject &response, const QString &error) {
        if (!error.isEmpty()) {
            Q_EMIT modelsFetched({});
            return;
        }
        QStringList models;
        const QJsonArray data = response.value(QStringLiteral("data")).toArray();
        for (const QJsonValue &value : data) {
            const QString id = value.toObject().value(QStringLiteral("id")).toString();
            if (!id.isEmpty())
                models.append(id);
        }
        models.sort();
        Q_EMIT modelsFetched(models);
    });
}

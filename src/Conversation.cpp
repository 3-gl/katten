/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "Conversation.h"

#include <QJsonArray>

QString Message::roleToString(Role role)
{
    switch (role) {
    case Role::User:
        return QStringLiteral("user");
    case Role::Assistant:
        return QStringLiteral("assistant");
    case Role::Error:
        return QStringLiteral("error");
    }
    return QStringLiteral("assistant");
}

Message::Role Message::roleFromString(const QString &role)
{
    if (role == QLatin1String("user"))
        return Role::User;
    if (role == QLatin1String("error"))
        return Role::Error;
    return Role::Assistant;
}

QJsonObject Message::toJson() const
{
    QJsonObject obj;
    obj[QStringLiteral("role")] = roleToString(role);
    obj[QStringLiteral("text")] = text;
    obj[QStringLiteral("timestamp")] = timestamp.toString(Qt::ISODateWithMs);
    obj[QStringLiteral("pending")] = pending;
    return obj;
}

Message Message::fromJson(const QJsonObject &obj)
{
    Message msg;
    msg.role = roleFromString(obj.value(QStringLiteral("role")).toString());
    msg.text = obj.value(QStringLiteral("text")).toString();
    msg.timestamp = QDateTime::fromString(obj.value(QStringLiteral("timestamp")).toString(), Qt::ISODateWithMs);
    if (!msg.timestamp.isValid())
        msg.timestamp = QDateTime::currentDateTime();
    msg.pending = obj.value(QStringLiteral("pending")).toBool(false);
    return msg;
}

QJsonObject Conversation::toJson() const
{
    QJsonObject obj;
    obj[QStringLiteral("id")] = id;
    obj[QStringLiteral("serverId")] = serverId;
    obj[QStringLiteral("title")] = title;
    obj[QStringLiteral("createdAt")] = createdAt.toString(Qt::ISODateWithMs);
    obj[QStringLiteral("updatedAt")] = updatedAt.toString(Qt::ISODateWithMs);
    QJsonArray messagesArray;
    for (const Message &msg : messages)
        messagesArray.append(msg.toJson());
    obj[QStringLiteral("messages")] = messagesArray;
    return obj;
}

Conversation Conversation::fromJson(const QJsonObject &obj)
{
    Conversation conv;
    conv.id = obj.value(QStringLiteral("id")).toString();
    conv.serverId = obj.value(QStringLiteral("serverId")).toString();
    conv.title = obj.value(QStringLiteral("title")).toString();
    conv.createdAt = QDateTime::fromString(obj.value(QStringLiteral("createdAt")).toString(), Qt::ISODateWithMs);
    conv.updatedAt = QDateTime::fromString(obj.value(QStringLiteral("updatedAt")).toString(), Qt::ISODateWithMs);
    if (!conv.createdAt.isValid())
        conv.createdAt = QDateTime::currentDateTime();
    if (!conv.updatedAt.isValid())
        conv.updatedAt = conv.createdAt;
    const QJsonArray messagesArray = obj.value(QStringLiteral("messages")).toArray();
    for (const QJsonValue &value : messagesArray)
        conv.messages.append(Message::fromJson(value.toObject()));
    return conv;
}

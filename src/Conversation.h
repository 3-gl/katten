/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QDateTime>
#include <QJsonObject>
#include <QString>
#include <QVector>

struct Message {
    enum class Role { User, Assistant, Error };

    Role role = Role::Assistant;
    QString text;
    QDateTime timestamp = QDateTime::currentDateTime();
    bool pending = false;

    static QString roleToString(Role role);
    static Role roleFromString(const QString &role);

    QJsonObject toJson() const;
    static Message fromJson(const QJsonObject &obj);
};

struct Conversation {
    QString id;
    QString serverId; // Mistral conversation id, empty until the first reply
    QString title;
    QDateTime createdAt = QDateTime::currentDateTime();
    QDateTime updatedAt = QDateTime::currentDateTime();
    QVector<Message> messages;

    QJsonObject toJson() const;
    static Conversation fromJson(const QJsonObject &obj);
};

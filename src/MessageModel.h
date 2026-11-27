/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include "Conversation.h"

#include <QAbstractListModel>
#include <QVector>

class ConversationStore;

class MessageModel : public QAbstractListModel
{
    Q_OBJECT

public:
    enum Roles {
        RoleRole = Qt::UserRole + 1,
        TextRole,
        HtmlRole,
        TimestampRole,
        PendingRole,
        ErrorRole,
    };

    explicit MessageModel(QObject *parent = nullptr);

    void setConversation(const QString &conversationId, ConversationStore *store);
    void clear();

    int rowCount(const QModelIndex &parent = QModelIndex()) const override;
    QVariant data(const QModelIndex &index, int role = Qt::DisplayRole) const override;
    QHash<int, QByteArray> roleNames() const override;

private:
    QString m_conversationId;
    ConversationStore *m_store = nullptr;
    QVector<Message> m_messages;
};

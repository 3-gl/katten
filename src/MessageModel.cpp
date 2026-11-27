/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "MessageModel.h"

#include "ConversationStore.h"
#include "MarkdownRenderer.h"

MessageModel::MessageModel(QObject *parent)
    : QAbstractListModel(parent)
{
}

void MessageModel::setConversation(const QString &conversationId, ConversationStore *store)
{
    beginResetModel();
    m_conversationId = conversationId;
    m_store = store;
    m_messages.clear();
    if (m_store && !m_conversationId.isEmpty())
        m_messages = m_store->conversation(m_conversationId).messages;
    endResetModel();
}

void MessageModel::clear()
{
    setConversation(QString(), nullptr);
}

int MessageModel::rowCount(const QModelIndex &parent) const
{
    if (parent.isValid())
        return 0;
    return m_messages.size();
}

QVariant MessageModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() < 0 || index.row() >= m_messages.size())
        return {};
    const Message &msg = m_messages.at(index.row());
    switch (role) {
    case RoleRole:
        return Message::roleToString(msg.role);
    case TextRole:
        return msg.text;
    case HtmlRole:
        if (msg.role == Message::Role::Assistant)
            return MarkdownRenderer::render(msg.text);
        return msg.text.toHtmlEscaped();
    case TimestampRole:
        return QLocale().toString(msg.timestamp, QLocale::ShortFormat);
    case PendingRole:
        return msg.pending;
    case ErrorRole:
        return msg.role == Message::Role::Error;
    }
    return {};
}

QHash<int, QByteArray> MessageModel::roleNames() const
{
    return {
        {RoleRole, "role"},
        {TextRole, "text"},
        {HtmlRole, "html"},
        {TimestampRole, "timestamp"},
        {PendingRole, "pending"},
        {ErrorRole, "error"},
    };
}

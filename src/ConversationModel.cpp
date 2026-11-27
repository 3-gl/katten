/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "ConversationModel.h"

#include "ConversationStore.h"

ConversationModel::ConversationModel(ConversationStore *store, QObject *parent)
    : QAbstractListModel(parent)
    , m_store(store)
{
    connect(m_store, &ConversationStore::changed, this, [this]() {
        beginResetModel();
        endResetModel();
    });
}

int ConversationModel::rowCount(const QModelIndex &parent) const
{
    if (parent.isValid())
        return 0;
    return m_store->conversations().size();
}

QVariant ConversationModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid())
        return {};
    const QVector<Conversation> convs = m_store->conversations();
    if (index.row() < 0 || index.row() >= convs.size())
        return {};
    const Conversation &conv = convs.at(index.row());
    switch (role) {
    case IdRole:
        return conv.id;
    case TitleRole:
        return conv.title;
    case MessageCountRole:
        return conv.messages.size();
    case UpdatedAtRole:
        return QLocale().toString(conv.updatedAt, QLocale::ShortFormat);
    case ServerIdRole:
        return conv.serverId;
    }
    return {};
}

QHash<int, QByteArray> ConversationModel::roleNames() const
{
    return {
        {IdRole, "id"},
        {TitleRole, "title"},
        {MessageCountRole, "messageCount"},
        {UpdatedAtRole, "updatedAt"},
        {ServerIdRole, "serverId"},
    };
}

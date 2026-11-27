/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include "Conversation.h"

#include <QHash>
#include <QObject>
#include <QVector>

/**
 * Persists conversations as JSON files below the application data directory
 * (~/.local/share/katten/conversations). Files are created with owner-only
 * permissions; conversation content is private user data.
 */
class ConversationStore : public QObject
{
    Q_OBJECT

public:
    explicit ConversationStore(QObject *parent = nullptr);

    QString directory() const;
    QVector<Conversation> conversations() const; // sorted by updatedAt, newest first
    Conversation conversation(const QString &id) const;
    bool hasConversation(const QString &id) const;

    QString createConversation(); // returns the new local id
    bool saveConversation(const Conversation &conv);
    bool removeConversation(const QString &id);

Q_SIGNALS:
    void changed();

private:
    void reload() const;
    QString filePath(const QString &id) const;

    mutable QHash<QString, Conversation> m_cache;
    mutable bool m_loaded = false;
};

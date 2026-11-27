/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "ConversationStore.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QStandardPaths>
#include <QUuid>

ConversationStore::ConversationStore(QObject *parent)
    : QObject(parent)
{
    QDir().mkpath(directory());
    QFile::setPermissions(directory(), QFileDevice::ReadOwner | QFileDevice::WriteOwner | QFileDevice::ExeOwner);
}

QString ConversationStore::directory() const
{
    return QStandardPaths::writableLocation(QStandardPaths::AppDataLocation) + QStringLiteral("/conversations");
}

QString ConversationStore::filePath(const QString &id) const
{
    return directory() + QLatin1Char('/') + id + QStringLiteral(".json");
}

void ConversationStore::reload() const
{
    if (m_loaded)
        return;
    m_loaded = true;
    m_cache.clear();
    QDir dir(directory());
    const QStringList files = dir.entryList({QStringLiteral("*.json")}, QDir::Files);
    for (const QString &file : files) {
        QFile f(dir.absoluteFilePath(file));
        if (!f.open(QIODevice::ReadOnly))
            continue;
        const QJsonDocument doc = QJsonDocument::fromJson(f.readAll());
        if (!doc.isObject())
            continue;
        Conversation conv = Conversation::fromJson(doc.object());
        if (!conv.id.isEmpty())
            m_cache.insert(conv.id, conv);
    }
}

QVector<Conversation> ConversationStore::conversations() const
{
    reload();
    QVector<Conversation> list = m_cache.values().toVector();
    std::sort(list.begin(), list.end(), [](const Conversation &a, const Conversation &b) {
        return a.updatedAt > b.updatedAt;
    });
    return list;
}

Conversation ConversationStore::conversation(const QString &id) const
{
    reload();
    return m_cache.value(id);
}

bool ConversationStore::hasConversation(const QString &id) const
{
    reload();
    return m_cache.contains(id);
}

QString ConversationStore::createConversation()
{
    reload();
    const QString id = QUuid::createUuid().toString(QUuid::WithoutBraces);
    Conversation conv;
    conv.id = id;
    m_cache.insert(id, conv);
    saveConversation(conv);
    Q_EMIT changed();
    return id;
}

bool ConversationStore::saveConversation(const Conversation &conv)
{
    reload();
    m_cache.insert(conv.id, conv);
    QFile f(filePath(conv.id));
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate))
        return false;
    f.setPermissions(QFileDevice::ReadOwner | QFileDevice::WriteOwner);
    f.write(QJsonDocument(conv.toJson()).toJson(QJsonDocument::Indented));
    f.close();
    Q_EMIT changed();
    return true;
}

bool ConversationStore::removeConversation(const QString &id)
{
    reload();
    if (!m_cache.contains(id))
        return false;
    m_cache.remove(id);
    QFile::remove(filePath(id));
    Q_EMIT changed();
    return true;
}

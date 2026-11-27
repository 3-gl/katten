/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "ConversationStore.h"

#include <QDir>
#include <QFile>
#include <QStandardPaths>
#include <QTemporaryDir>
#include <QTest>

class ConversationStoreTest : public QObject
{
    Q_OBJECT

private Q_SLOTS:
    void initTestCase();
    void testCreateSaveReload();
    void testRemove();
    void testFilePermissions();

private:
    QTemporaryDir m_dataHome;
};

void ConversationStoreTest::initTestCase()
{
    qputenv("XDG_DATA_HOME", m_dataHome.path().toUtf8());
}

void ConversationStoreTest::testCreateSaveReload()
{
    ConversationStore store;
    const QString id = store.createConversation();
    QVERIFY(!id.isEmpty());

    Conversation conv = store.conversation(id);
    conv.title = QStringLiteral("Test chat");
    conv.serverId = QStringLiteral("conv_123");
    Message user;
    user.role = Message::Role::User;
    user.text = QStringLiteral("Hello");
    Message assistant;
    assistant.role = Message::Role::Assistant;
    assistant.text = QStringLiteral("Hi there");
    conv.messages.append(user);
    conv.messages.append(assistant);
    QVERIFY(store.saveConversation(conv));

    ConversationStore store2;
    QVERIFY(store2.hasConversation(id));
    const Conversation loaded = store2.conversation(id);
    QCOMPARE(loaded.title, QStringLiteral("Test chat"));
    QCOMPARE(loaded.serverId, QStringLiteral("conv_123"));
    QCOMPARE(loaded.messages.size(), 2);
    QCOMPARE(loaded.messages.at(0).role, Message::Role::User);
    QCOMPARE(loaded.messages.at(0).text, QStringLiteral("Hello"));
    QCOMPARE(loaded.messages.at(1).role, Message::Role::Assistant);
    QCOMPARE(loaded.messages.at(1).text, QStringLiteral("Hi there"));
    QVERIFY(store2.conversations().size() >= 1);
}

void ConversationStoreTest::testRemove()
{
    ConversationStore store;
    const QString id = store.createConversation();
    QVERIFY(store.hasConversation(id));
    QVERIFY(store.removeConversation(id));
    QVERIFY(!store.hasConversation(id));
}

void ConversationStoreTest::testFilePermissions()
{
    ConversationStore store;
    const QString id = store.createConversation();
    Conversation conv = store.conversation(id);
    QVERIFY(store.saveConversation(conv));
    const QString path = store.directory() + QLatin1Char('/') + id + QStringLiteral(".json");
    QVERIFY(QFile::exists(path));
    const QFileDevice::Permissions perms = QFile::permissions(path);
    QVERIFY(perms & QFileDevice::ReadOwner);
    QVERIFY(perms & QFileDevice::WriteOwner);
    QVERIFY(!(perms & QFileDevice::ReadGroup));
    QVERIFY(!(perms & QFileDevice::ReadOther));
}

int main(int argc, char **argv)
{
    QCoreApplication app(argc, argv);
    ConversationStoreTest test;
    return QTest::qExec(&test, argc, argv);
}

#include "conversationstoretest.moc"

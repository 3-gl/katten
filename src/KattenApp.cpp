/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "KattenApp.h"

#include "ApiKeyStore.h"
#include "ConversationModel.h"
#include "MessageModel.h"
#include "Settings.h"

#include <KLocalizedString>
#include <QClipboard>
#include <QGuiApplication>
#include <QWindow>

KattenApp::KattenApp(QObject *parent)
    : QObject(parent)
    , m_conversationModel(new ConversationModel(&m_store, this))
    , m_messageModel(new MessageModel(this))
{
    m_client.setApiKey(ApiKeyStore::self()->apiKey());
    connect(&m_client, &MistralClient::messageSent, this, &KattenApp::handleReply);
    connect(&m_client, &MistralClient::messageFailed, this, &KattenApp::handleError);
    connect(&m_client, &MistralClient::modelsFetched, this, [this](const QStringList &models) {
        m_models = models;
        if (!m_models.contains(Settings::self()->model()))
            m_models.prepend(Settings::self()->model());
        Q_EMIT availableModelsChanged();
    });
    connect(Settings::self(), &Settings::modelChanged, this, &KattenApp::modelChanged);
    connect(Settings::self(), &Settings::webSearchChanged, this, &KattenApp::webSearchChanged);
    connect(&m_store, &ConversationStore::changed, this, [this]() {
        if (!m_currentId.isEmpty() && !m_store.hasConversation(m_currentId)) {
            m_currentId.clear();
            m_messageModel->clear();
            Q_EMIT currentConversationIdChanged();
        }
    });
    if (hasApiKey())
        refreshModels();
    else
        m_models = {Settings::self()->model()};
}

void KattenApp::setMainWindow(QWindow *window)
{
    m_window = window;
}

ConversationModel *KattenApp::conversations() const
{
    return m_conversationModel;
}

MessageModel *KattenApp::messages() const
{
    return m_messageModel;
}

QString KattenApp::currentConversationId() const
{
    return m_currentId;
}

QString KattenApp::currentTitle() const
{
    if (m_currentId.isEmpty())
        return {};
    return m_store.conversation(m_currentId).title;
}

bool KattenApp::busy() const
{
    return m_busy;
}

bool KattenApp::hasApiKey() const
{
    return !ApiKeyStore::self()->apiKey().isEmpty();
}

QString KattenApp::model() const
{
    return Settings::self()->model();
}

void KattenApp::setModel(const QString &model)
{
    Settings::self()->setModel(model);
}

bool KattenApp::webSearch() const
{
    return Settings::self()->webSearch();
}

void KattenApp::setWebSearch(bool on)
{
    Settings::self()->setWebSearch(on);
}

QStringList KattenApp::availableModels() const
{
    return m_models;
}

QString KattenApp::lastError() const
{
    return m_lastError;
}

void KattenApp::setBusy(bool busy)
{
    if (m_busy == busy)
        return;
    m_busy = busy;
    Q_EMIT busyChanged();
}

void KattenApp::setLastError(const QString &error)
{
    m_lastError = error;
    Q_EMIT lastErrorChanged();
}

QString KattenApp::newConversation()
{
    const QString id = m_store.createConversation();
    Conversation conv = m_store.conversation(id);
    conv.title = i18nc("@title", "New conversation");
    m_store.saveConversation(conv);
    openConversation(id);
    return id;
}

void KattenApp::openConversation(const QString &id)
{
    if (!m_store.hasConversation(id))
        return;
    m_currentId = id;
    m_messageModel->setConversation(m_currentId, &m_store);
    Q_EMIT currentConversationIdChanged();
}

void KattenApp::deleteConversation(const QString &id)
{
    m_store.removeConversation(id);
}

void KattenApp::reloadCurrentMessages()
{
    m_messageModel->setConversation(m_currentId, &m_store);
}

void KattenApp::sendPrompt(const QString &text)
{
    const QString prompt = text.trimmed();
    if (prompt.isEmpty() || m_busy)
        return;
    if (m_currentId.isEmpty())
        newConversation();

    Conversation conv = m_store.conversation(m_currentId);
    const bool firstPrompt = conv.messages.isEmpty();

    Message userMessage;
    userMessage.role = Message::Role::User;
    userMessage.text = prompt;
    conv.messages.append(userMessage);
    if (firstPrompt)
        conv.title = prompt.left(60);

    if (!hasApiKey()) {
        Message errorMessage;
        errorMessage.role = Message::Role::Error;
        errorMessage.text = i18nc("@info", "No Mistral API key configured. Open Settings to store your API key in KWallet.");
        conv.messages.append(errorMessage);
        conv.updatedAt = QDateTime::currentDateTime();
        m_store.saveConversation(conv);
        reloadCurrentMessages();
        setLastError(errorMessage.text);
        return;
    }

    Message pending;
    pending.role = Message::Role::Assistant;
    pending.pending = true;
    conv.messages.append(pending);
    conv.updatedAt = QDateTime::currentDateTime();
    m_store.saveConversation(conv);
    reloadCurrentMessages();

    setLastError({});
    setBusy(true);
    m_client.setApiKey(ApiKeyStore::self()->apiKey());
    // Web search tools are fixed when the server-side conversation is created.
    m_client.sendMessage(conv.serverId, prompt, Settings::self()->model(), firstPrompt && Settings::self()->webSearch());
}

void KattenApp::retryLast()
{
    if (m_busy || m_currentId.isEmpty())
        return;
    Conversation conv = m_store.conversation(m_currentId);
    int lastUserIndex = -1;
    for (int i = conv.messages.size() - 1; i >= 0; --i) {
        if (conv.messages.at(i).role == Message::Role::User) {
            lastUserIndex = i;
            break;
        }
    }
    if (lastUserIndex < 0)
        return;
    const QString prompt = conv.messages.at(lastUserIndex).text;
    while (conv.messages.size() > lastUserIndex + 1)
        conv.messages.removeLast();
    Message pending;
    pending.role = Message::Role::Assistant;
    pending.pending = true;
    conv.messages.append(pending);
    conv.updatedAt = QDateTime::currentDateTime();
    m_store.saveConversation(conv);
    reloadCurrentMessages();
    setLastError({});
    setBusy(true);
    m_client.setApiKey(ApiKeyStore::self()->apiKey());
    m_client.sendMessage(conv.serverId, prompt, Settings::self()->model(), false);
}

void KattenApp::handleReply(const QString &serverId, const QString &text)
{
    if (m_currentId.isEmpty())
        return;
    Conversation conv = m_store.conversation(m_currentId);
    if (conv.serverId.isEmpty())
        conv.serverId = serverId;
    if (!conv.messages.isEmpty()) {
        Message &last = conv.messages.last();
        last.pending = false;
        last.role = Message::Role::Assistant;
        last.text = text;
        last.timestamp = QDateTime::currentDateTime();
    }
    conv.updatedAt = QDateTime::currentDateTime();
    m_store.saveConversation(conv);
    reloadCurrentMessages();
    setBusy(false);
}

void KattenApp::handleError(const QString &error)
{
    if (!m_currentId.isEmpty()) {
        Conversation conv = m_store.conversation(m_currentId);
        if (!conv.messages.isEmpty()) {
            Message &last = conv.messages.last();
            last.pending = false;
            last.role = Message::Role::Error;
            last.text = error;
            last.timestamp = QDateTime::currentDateTime();
        }
        conv.updatedAt = QDateTime::currentDateTime();
        m_store.saveConversation(conv);
        reloadCurrentMessages();
    }
    setLastError(error);
    setBusy(false);
}

bool KattenApp::setApiKey(const QString &key)
{
    QString error;
    if (!ApiKeyStore::self()->storeKey(key, &error)) {
        setLastError(error);
        return false;
    }
    m_client.setApiKey(ApiKeyStore::self()->apiKey());
    setLastError({});
    Q_EMIT hasApiKeyChanged();
    refreshModels();
    return true;
}

void KattenApp::clearApiKey()
{
    QString error;
    ApiKeyStore::self()->removeKey(&error);
    m_client.setApiKey(ApiKeyStore::self()->apiKey());
    Q_EMIT hasApiKeyChanged();
}

void KattenApp::refreshModels()
{
    m_client.setApiKey(ApiKeyStore::self()->apiKey());
    if (hasApiKey())
        m_client.fetchModels();
    else {
        m_models = {Settings::self()->model()};
        Q_EMIT availableModelsChanged();
    }
}

void KattenApp::copyToClipboard(const QString &text) const
{
    QGuiApplication::clipboard()->setText(text);
}

void KattenApp::openPrompt(const QString &prompt)
{
    raiseWindow();
    const QString id = newConversation();
    Q_UNUSED(id)
    if (!prompt.trimmed().isEmpty())
        sendPrompt(prompt);
}

void KattenApp::raiseWindow()
{
    if (m_window) {
        m_window->showNormal();
        m_window->raise();
        m_window->requestActivate();
    }
}

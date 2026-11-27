/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "ApiKeyStore.h"

#include <KLocalizedString>
#include <kwallet.h>

ApiKeyStore *ApiKeyStore::self()
{
    static ApiKeyStore instance;
    return &instance;
}

ApiKeyStore::ApiKeyStore(QObject *parent)
    : QObject(parent)
{
}

KWallet::Wallet *ApiKeyStore::openWallet(QString *error) const
{
    KWallet::Wallet *wallet = KWallet::Wallet::openWallet(KWallet::Wallet::LocalWallet(), 0, KWallet::Wallet::Synchronous);
    if (!wallet || !wallet->isOpen()) {
        m_lastError = i18nc("@info", "Could not open KWallet. Is kwalletd running? The API key cannot be stored safely without it.");
        if (error)
            *error = m_lastError;
        return nullptr;
    }
    return wallet;
}

QString ApiKeyStore::apiKey() const
{
    QString key;
    QString error;
    if (KWallet::Wallet *wallet = openWallet(&error)) {
        if (wallet->setFolder(QString::fromLatin1(Folder))) {
            wallet->readPassword(QString::fromLatin1(KeyName), key);
        }
        wallet->deleteLater();
    }
    if (key.isEmpty())
        key = QString::fromLocal8Bit(qgetenv("MISTRAL_API_KEY"));
    return key;
}

bool ApiKeyStore::hasStoredKey()
{
    QString error;
    if (KWallet::Wallet *wallet = openWallet(&error)) {
        const bool has = wallet->setFolder(QString::fromLatin1(Folder)) && wallet->hasEntry(QString::fromLatin1(KeyName));
        wallet->deleteLater();
        return has;
    }
    return false;
}

bool ApiKeyStore::storeKey(const QString &key, QString *error)
{
    if (key.trimmed().isEmpty()) {
        m_lastError = i18nc("@info", "The API key is empty.");
        if (error)
            *error = m_lastError;
        return false;
    }
    if (KWallet::Wallet *wallet = openWallet(error)) {
        wallet->setFolder(QString::fromLatin1(Folder));
        const int rc = wallet->writePassword(QString::fromLatin1(KeyName), key.trimmed());
        wallet->deleteLater();
        if (rc != 0) {
            m_lastError = i18nc("@info", "Failed to write the API key to KWallet (error %1).", rc);
            if (error)
                *error = m_lastError;
            return false;
        }
        return true;
    }
    return false;
}

bool ApiKeyStore::removeKey(QString *error)
{
    if (KWallet::Wallet *wallet = openWallet(error)) {
        const bool ok = wallet->setFolder(QString::fromLatin1(Folder)) && wallet->removeEntry(QString::fromLatin1(KeyName));
        wallet->deleteLater();
        return ok;
    }
    return false;
}

QString ApiKeyStore::lastError() const
{
    return m_lastError;
}

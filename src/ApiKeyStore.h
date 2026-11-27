/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QObject>
#include <QString>

namespace KWallet
{
class Wallet;
}

/**
 * Stores the Mistral API key in KWallet (folder "Katten", key "mistral-api-key").
 * Nothing secret is ever written to a plain-text config file. The
 * MISTRAL_API_KEY environment variable is honoured as a fallback for users who
 * deliberately manage the key themselves.
 */
class ApiKeyStore : public QObject
{
    Q_OBJECT

public:
    static ApiKeyStore *self();

    QString apiKey() const; // KWallet entry, falling back to $MISTRAL_API_KEY
    bool hasStoredKey();
    bool storeKey(const QString &key, QString *error = nullptr);
    bool removeKey(QString *error = nullptr);

    QString lastError() const;

    static constexpr const char *Folder = "Katten";
    static constexpr const char *KeyName = "mistral-api-key";

private:
    explicit ApiKeyStore(QObject *parent = nullptr);
    KWallet::Wallet *openWallet(QString *error) const;

    mutable QString m_lastError;
};

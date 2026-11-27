/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <QObject>
#include <QString>

class KConfigGroup;

/**
 * Non-secret application settings, stored in ~/.config/kattenrc.
 * The API key is deliberately NOT stored here; it lives in KWallet.
 */
class Settings : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString model READ model WRITE setModel NOTIFY modelChanged)
    Q_PROPERTY(bool webSearch READ webSearch WRITE setWebSearch NOTIFY webSearchChanged)

public:
    static Settings *self();

    QString model() const;
    void setModel(const QString &model);

    bool webSearch() const;
    void setWebSearch(bool on);

    static constexpr const char *DefaultModel = "mistral-medium-latest";

Q_SIGNALS:
    void modelChanged();
    void webSearchChanged();

private:
    explicit Settings(QObject *parent = nullptr);
    KConfigGroup group() const;
};

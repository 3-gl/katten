/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "Settings.h"

#include <KConfigGroup>
#include <KSharedConfig>

Settings *Settings::self()
{
    static Settings instance;
    return &instance;
}

Settings::Settings(QObject *parent)
    : QObject(parent)
{
}

KConfigGroup Settings::group() const
{
    return KSharedConfig::openConfig(QStringLiteral("kattenrc"), KConfig::NoGlobals)->group(QStringLiteral("General"));
}

QString Settings::model() const
{
    return group().readEntry("model", QString::fromLatin1(DefaultModel));
}

void Settings::setModel(const QString &model)
{
    KConfigGroup g = group();
    if (g.readEntry("model", QString::fromLatin1(DefaultModel)) == model)
        return;
    g.writeEntry("model", model);
    g.sync();
    Q_EMIT modelChanged();
}

bool Settings::webSearch() const
{
    return group().readEntry("webSearch", true);
}

void Settings::setWebSearch(bool on)
{
    KConfigGroup g = group();
    if (g.readEntry("webSearch", true) == on)
        return;
    g.writeEntry("webSearch", on);
    g.sync();
    Q_EMIT webSearchChanged();
}

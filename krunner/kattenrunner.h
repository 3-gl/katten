/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#pragma once

#include <KRunner/AbstractRunner>
#include <QStringList>

/**
 * KRunner plugin that forwards prompts to the Katten application over D-Bus
 * (org.kde.katten /Katten, method openPrompt). The application is started via
 * D-Bus activation if it is not running yet.
 */
class KattenRunner : public KRunner::AbstractRunner
{
    Q_OBJECT

public:
    explicit KattenRunner(QObject *parent, const KPluginMetaData &metaData);

    void match(KRunner::RunnerContext &context) override;
    void reloadConfiguration() override;

protected Q_SLOTS:
    void run(const KRunner::RunnerContext &context, const KRunner::QueryMatch &match) override;

private:
    QStringList m_keywords;
};

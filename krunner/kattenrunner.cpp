/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "kattenrunner.h"

#include <KLocalizedString>
#include <KConfigGroup>
#include <KRunner/QueryMatch>
#include <KRunner/RunnerContext>

#include <QDBusConnection>
#include <QDBusInterface>
#include <QDBusReply>
#include <QDebug>

K_PLUGIN_CLASS_WITH_JSON(KattenRunner, "plasma-runner-katten.json")

namespace
{
QStringList defaultKeywords()
{
    return {QStringLiteral("katten"),
            QStringLiteral("lechat"),
            QStringLiteral("lc"),
            QStringLiteral("mistral"),
            QStringLiteral("vibe")};
}
}

KattenRunner::KattenRunner(QObject *parent, const KPluginMetaData &metaData)
    : KRunner::AbstractRunner(parent, metaData)
{
    setMinLetterCount(2);
    reloadConfiguration();
}

void KattenRunner::reloadConfiguration()
{
    const QString configured = config().readEntry("keywords", QString());
    if (configured.isEmpty()) {
        m_keywords = defaultKeywords();
    } else {
        m_keywords = configured.split(QLatin1Char(','), Qt::SkipEmptyParts);
        for (QString &keyword : m_keywords)
            keyword = keyword.trimmed().toLower();
    }
    for (const QString &keyword : m_keywords)
        addSyntax(keyword + QStringLiteral(" :q:"), i18nc("@info:shell", "Send the query to Katten (Mistral Vibe)"));
}

void KattenRunner::match(KRunner::RunnerContext &context)
{
    const QString query = context.query().trimmed();
    for (const QString &keyword : m_keywords) {
        if (query.compare(keyword, Qt::CaseInsensitive) == 0
            || query.startsWith(keyword + QLatin1Char(' '), Qt::CaseInsensitive)) {
            const QString prompt = query.mid(keyword.length()).trimmed();
            KRunner::QueryMatch match(this);
            match.setId(query);
            match.setData(prompt);
            match.setIconName(QStringLiteral("org.kde.katten"));
            match.setCategoryRelevance(KRunner::QueryMatch::CategoryRelevance::High);
            if (prompt.isEmpty()) {
                match.setText(i18nc("@action", "Open Katten"));
                match.setSubtext(i18nc("@info", "Open the Katten window"));
            } else {
                match.setText(i18nc("@action", "Ask Katten: %1", prompt));
                match.setSubtext(i18nc("@info", "Send this prompt to Mistral Vibe in the Katten window"));
            }
            context.addMatch(match);
        }
    }
}

void KattenRunner::run(const KRunner::RunnerContext &context, const KRunner::QueryMatch &match)
{
    Q_UNUSED(context)
    const QString prompt = match.data().toString();

    QDBusInterface iface(QStringLiteral("org.kde.katten"),
                         QStringLiteral("/Katten"),
                         QStringLiteral("org.kde.katten"),
                         QDBusConnection::sessionBus());
    const QDBusReply<void> reply = iface.call(QStringLiteral("openPrompt"), prompt);
    if (reply.isValid())
        return;

    qWarning() << "Katten runner: could not reach org.kde.katten:" << reply.error().message();
    QDBusInterface notifications(QStringLiteral("org.freedesktop.Notifications"),
                                 QStringLiteral("/org/freedesktop/Notifications"),
                                 QStringLiteral("org.freedesktop.Notifications"),
                                 QDBusConnection::sessionBus());
    notifications.call(QStringLiteral("Notify"),
                       QStringLiteral("Katten"),
                       QVariant(0u),
                       QStringLiteral("org.kde.katten"),
                       i18nc("@title", "Katten"),
                       i18nc("@info", "Could not start Katten. Is the Katten application installed?"),
                       QStringList(),
                       QVariantMap(),
                       5000);
}

#include "kattenrunner.moc"
#include "moc_kattenrunner.cpp"

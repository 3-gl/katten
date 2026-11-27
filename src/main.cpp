/*
    SPDX-FileCopyrightText: 2026 Emilio González Longoria <hej@emilio.dk>
    SPDX-License-Identifier: GPL-3.0-or-later
*/

#include "KattenApp.h"

// klocalizedqmlcontext.h must be included before KLocalizedString: with
// TRANSLATION_DOMAIN defined, klocalizedstring.h turns i18n* into macros that
// would otherwise mangle the member declarations in klocalizedqmlcontext.h.
#include <klocalizedqmlcontext.h>

#include <KAboutData>
#include <KDBusService>
#include <KLocalizedString>

#include <QCommandLineParser>
#include <QDBusConnection>
#include <QGuiApplication>
#include <QIcon>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QWindow>
#include <QDebug>

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    QGuiApplication::setWindowIcon(QIcon::fromTheme(QStringLiteral("org.kde.katten")));

    KLocalizedString::setApplicationDomain("katten");
    KAboutData about(QStringLiteral("katten"),
                     i18nc("@title", "Katten"),
                     QStringLiteral("0.5.0"),
                     i18nc("@info", "Unofficial Mistral Vibe client for KDE Plasma"),
                     KAboutLicense::GPL_V3,
                     QStringLiteral("Copyright 2026 Emilio González Longoria"));
    about.setOrganizationDomain("kde.org");
    about.setHomepage(QStringLiteral("https://github.com/3-gl/katten"));
    about.addAuthor(i18nc("@info:credit", "Emilio González Longoria"), QString(), QStringLiteral("hej@emilio.dk"));
    KAboutData::setApplicationData(about);

    QCommandLineParser parser;
    parser.addHelpOption();
    parser.addOption({{QStringLiteral("p"), QStringLiteral("prompt")},
                      i18nc("@option", "Prompt to send to Mistral Vibe"),
                      QStringLiteral("prompt")});
    parser.addPositionalArgument(QStringLiteral("prompt"),
                                 i18nc("@info", "Prompt to send to Mistral Vibe (same as --prompt)"),
                                 QStringLiteral("[prompt]"));
    parser.process(app);

    // Single instance: a second launch forwards its prompt to the running
    // instance over D-Bus (KDBusService also registers org.kde.katten, which
    // the installed D-Bus service file maps to this binary for activation).
    KDBusService service(KDBusService::Unique);

    auto *kattenApp = new KattenApp;

    QQmlApplicationEngine engine;
    auto *localizedContext = new KLocalizedQmlContext(&engine);
    engine.rootContext()->setContextObject(localizedContext);
    engine.rootContext()->setContextProperty(QStringLiteral("kattenApp"), kattenApp);

    QObject::connect(&engine, &QQmlApplicationEngine::objectCreated, &app, [](QObject *object, const QUrl &url) {
        Q_UNUSED(url)
        if (!object)
            QCoreApplication::exit(1);
    });
    engine.loadFromModule("org.kde.katten", "Main");
    if (engine.rootObjects().isEmpty())
        return 1;
    if (auto *window = qobject_cast<QWindow *>(engine.rootObjects().first()))
        kattenApp->setMainWindow(window);

    const bool dbusOk = QDBusConnection::sessionBus().registerObject(QStringLiteral("/Katten"), kattenApp, QDBusConnection::ExportAllInvokables | QDBusConnection::ExportAllSlots);
    qWarning() << "registerObject /Katten:" << dbusOk;

    auto handleArguments = [kattenApp](const QStringList &arguments) {
        QCommandLineParser p;
        p.addOption({{QStringLiteral("p"), QStringLiteral("prompt")},
                     i18nc("@option", "Prompt to send to Mistral Vibe"),
                     QStringLiteral("prompt")});
        p.addPositionalArgument(QStringLiteral("prompt"),
                                 i18nc("@info", "Prompt to send to Mistral Vibe (same as --prompt)"),
                                 QStringLiteral("[prompt]"));
        p.parse(arguments);
        QString prompt = p.value(QStringLiteral("prompt"));
        if (prompt.isEmpty())
            prompt = p.positionalArguments().join(QLatin1Char(' '));
        if (!prompt.isEmpty())
            kattenApp->openPrompt(prompt);
        else
            kattenApp->raiseWindow();
    };

    QObject::connect(&service, &KDBusService::activateRequested, &app, [&handleArguments](const QStringList &arguments) {
        handleArguments(arguments);
    });
    handleArguments(app.arguments());

    return app.exec();
}

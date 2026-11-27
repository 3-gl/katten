set(katten_SRCS
    main.cpp
    Conversation.cpp
    ConversationStore.cpp
    ConversationModel.cpp
    MessageModel.cpp
    MarkdownRenderer.cpp
    ApiKeyStore.cpp
    Settings.cpp
    MistralClient.cpp
    KattenApp.cpp
)

ecm_add_qml_module(kattenqml
    URI org.kde.katten
    QML_FILES
        qml/Main.qml
        qml/ChatPage.qml
        qml/MessageDelegate.qml
        qml/SettingsPage.qml
    GENERATE_PLUGIN_SOURCE
)
ecm_finalize_qml_module(kattenqml DESTINATION ${KDE_INSTALL_QMLDIR})

add_executable(katten ${katten_SRCS})
target_link_libraries(katten PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Qml
    Qt6::Quick
    Qt6::Network
    Qt6::DBus
    Qt6::Svg
    KF6::CoreAddons
    KF6::I18n
    KF6::I18nQml
    KF6::ConfigCore
    KF6::Wallet
    KF6::DBusAddons
    KF6::IconThemes
    KF6::Kirigami
)

install(TARGETS katten ${KDE_INSTALL_TARGETS_DEFAULT_ARGS})

install(PROGRAMS ${CMAKE_CURRENT_SOURCE_DIR}/../org.kde.katten.desktop
        DESTINATION ${KDE_INSTALL_APPDIR})
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/../org.kde.katten.metainfo.xml
        DESTINATION ${KDE_INSTALL_METAINFODIR})
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/../org.kde.katten.service
        DESTINATION ${KDE_INSTALL_DATADIR}/dbus-1/services)
install(FILES ${CMAKE_CURRENT_SOURCE_DIR}/../katten-icon.svg
        DESTINATION ${KDE_INSTALL_ICONDIR}/hicolor/scalable/apps
        RENAME org.kde.katten.svg)

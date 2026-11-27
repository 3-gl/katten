cmake_minimum_required(VERSION 3.16)

project(katten VERSION 0.5.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ECM 6.0 REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})

include(KDEInstallDirs)
include(KDECompilerSettings NO_POLICY_SCOPE)
include(KDECMakeSettings)
include(ECMAddTests)
include(ECMQmlModule)
include(FeatureSummary)

set(QT_MIN_VERSION "6.6")
set(KF6_MIN_VERSION "6.0")

find_package(Qt6 ${QT_MIN_VERSION} REQUIRED COMPONENTS Core Gui Qml Quick QuickControls2 Network DBus Svg)
find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS CoreAddons I18n Config Wallet DBusAddons IconThemes Kirigami)

add_definitions(-DTRANSLATION_DOMAIN=\"katten\")
qt_policy(SET QTP0001 NEW)

set(CMAKE_INSTALL_DEFAULT_COMPONENT_NAME app)

option(KATTEN_BUILD_KRUNNER_PLUGIN "Build the optional KRunner plugin (shipped as a separate package)" ON)

ki18n_install(po)

add_subdirectory(src)

if(KATTEN_BUILD_KRUNNER_PLUGIN)
    find_package(KF6 ${KF6_MIN_VERSION} REQUIRED COMPONENTS Runner)
    add_subdirectory(krunner)
endif()

if(BUILD_TESTING)
    add_subdirectory(tests)
endif()

# Release tarballs via CPack; .deb packages are built from the debian/ directory
# (two binary packages: katten and katten-krunner).
set(CPACK_PACKAGE_NAME "katten")
set(CPACK_PACKAGE_VENDOR "Emilio González Longoria")
set(CPACK_PACKAGE_CONTACT "Emilio González Longoria <hej@emilio.dk>")
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Unofficial Mistral Vibe client for KDE Plasma")
set(CPACK_PACKAGE_VERSION_MAJOR ${PROJECT_VERSION_MAJOR})
set(CPACK_PACKAGE_VERSION_MINOR ${PROJECT_VERSION_MINOR})
set(CPACK_PACKAGE_VERSION_PATCH ${PROJECT_VERSION_PATCH})
set(CPACK_PACKAGE_DESCRIPTION_FILE "${CMAKE_CURRENT_SOURCE_DIR}/README.md")
set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")
set(CPACK_GENERATOR "TGZ")
set(CPACK_SOURCE_GENERATOR "TGZ")
set(CPACK_DEB_COMPONENT_INSTALL ON)
set(CPACK_COMPONENTS_ALL app krunner)
include(CPack)

feature_summary(WHAT ALL FATAL_ON_MISSING_REQUIRED_PACKAGES)

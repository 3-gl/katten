#!/bin/sh
# Extracts translatable messages from the C++ and QML sources into po/katten.pot.
# Run this after changing user-visible strings, then update the .po files.
set -e
cd "$(dirname "$0")/.."

xgettext --from-code=UTF-8 -C --kde \
    -ki18n:1 -ki18nc:1c,2 -ki18ncp:1c,2,3 -ki18nd:2 \
    src/*.cpp src/*.h krunner/*.cpp krunner/*.h \
    -o po/katten.pot

xgettext --from-code=UTF-8 -L JavaScript --kde \
    -ki18n:1 -ki18nc:1c,2 -ki18ncp:1c,2,3 \
    src/qml/*.qml \
    --join-existing -o po/katten.pot

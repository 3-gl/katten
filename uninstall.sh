#!/bin/bash
#
# Katten - unofficial Mistral Vibe plugin for KRunner
# Uninstaller
#

set -e

echo "========================================"
echo "Katten Uninstaller"
echo "========================================"
echo

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Stop the plugin
echo "Stopping plugin..."
pkill -f "katten.py" 2>/dev/null || true

# Remove files
echo "Removing plugin files..."

rm -f ~/.local/share/krunner/dbusplugins/katten.desktop
rm -f ~/.local/share/dbus-1/services/org.kde.katten.service
rm -rf ~/.local/share/katten
rm -f ~/.local/share/icons/hicolor/128x128/apps/katten-icon.png
rm -f ~/.local/share/icons/hicolor/scalable/apps/katten-icon.svg
rm -f ~/.local/bin/katten-config
rm -f ~/.config/autostart/katten.desktop

echo -e "${GREEN}[OK]${NC} Plugin files removed"

# Ask about config
echo
read -p "Remove configuration (including API key and history)? (y/N): " remove_config
if [[ "$remove_config" =~ ^[Yy]$ ]]; then
    rm -rf ~/.config/katten
    echo -e "${GREEN}[OK]${NC} Configuration removed"
else
    echo -e "${YELLOW}[--]${NC} Configuration kept at ~/.config/katten"
fi

# Restart KRunner
echo
echo "Restarting KRunner..."
kquitapp6 krunner 2>/dev/null || kquitapp5 krunner 2>/dev/null || true

echo
echo "========================================"
echo -e "${GREEN}Katten uninstalled!${NC}"
echo "========================================"
echo

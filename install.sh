#!/bin/bash
#
# Katten - Unofficial Mistral Vibe plugin for KRunner
# Copyright (C) 2026  Emilio González Longoria
#
# Installer script - supports Debian/Ubuntu (apt), Fedora (dnf), openSUSE (zypper), Arch/Manjaro (pacman)
# Supports per-user and system-wide installation

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- DISTRO DETECTION ---
DETECT_DISTRO() {
    if [ -f /etc/arch-release ] || [ -f /etc/manjaro-release ]; then
        DISTRO="arch"
        PKG_MANAGER="sudo pacman -S --needed"
        PYTHON_DBUS="python-dbus"
        PYTHON_GOBJECT="python-gobject"
        PYTHON_PYQT6="python-pyqt6"
        XCLIP="xclip"
    elif [ -f /etc/fedora-release ]; then
        DISTRO="fedora"
        PKG_MANAGER="sudo dnf install -y"
        PYTHON_DBUS="python3-dbus"
        PYTHON_GOBJECT="python3-gobject"
        PYTHON_PYQT6="python3-PyQt6"
        XCLIP="xclip"
    elif grep -qi "opensuse" /etc/os-release 2>/dev/null; then
        DISTRO="opensuse"
        PKG_MANAGER="sudo zypper install -y"
        PYTHON_DBUS="python3-dbus"
        PYTHON_GOBJECT="python3-gobject"
        PYTHON_PYQT6="python3-qt6"
        XCLIP="xclip"
    elif command -v apt &> /dev/null; then
        DISTRO="debian"
        PKG_MANAGER="sudo apt install -y"
        PYTHON_DBUS="python3-dbus"
        PYTHON_GOBJECT="python3-gi gir1.2-glib-2.0"
        PYTHON_PYQT6="python3-pyqt6"
        XCLIP="xclip"
    else
        echo -e "${RED}Unsupported distribution.${NC}"
        echo "Supported: Debian/Ubuntu (apt), Fedora (dnf), openSUSE (zypper), Arch/Manjaro (pacman)"
        exit 1
    fi
}

# --- INSTALLATION PATHS ---
# Determine if system-wide (root) or per-user
if [ "$(id -u)" -eq 0 ]; then
    INSTALL_MODE="system"
    PLUGIN_DIR="/usr/share/katten"
    KRUNNER_DIR="/usr/share/kservices5/krunner"
    DBUS_DIR="/usr/share/dbus-1/services"
    BIN_DIR="/usr/bin"
    ICON_DIR="/usr/share/icons/hicolor"
    echo -e "${BLUE}=== SYSTEM-WIDE INSTALLATION (requires root) ===${NC}"
else
    INSTALL_MODE="user"
    PLUGIN_DIR="$HOME/.local/share/katten"
    KRUNNER_DIR="$HOME/.local/share/krunner/dbusplugins"
    DBUS_DIR="$HOME/.local/share/dbus-1/services"
    BIN_DIR="$HOME/.local/bin"
    ICON_DIR="$HOME/.local/share/icons/hicolor"
    echo -e "${BLUE}=== PER-USER INSTALLATION ===${NC}"
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- DEPENDENCY CHECK ---
echo -e "${BLUE}Checking dependencies...${NC}"
DETECT_DISTRO
echo "Detected: $DISTRO"

# Define markdown package name for each distro
if [ "$DISTRO" = "arch" ]; then
    PYTHON_MARKDOWN="python-markdown"
elif [ "$DISTRO" = "fedora" ]; then
    PYTHON_MARKDOWN="python3-markdown"
elif [ "$DISTRO" = "opensuse" ]; then
    PYTHON_MARKDOWN="python3-markdown"
else
    # Debian/Ubuntu
    PYTHON_MARKDOWN="python3-markdown"
fi

MISSING=()
python3 -c "import dbus" 2>/dev/null || MISSING+=("$PYTHON_DBUS")
python3 -c "from gi.repository import GLib" 2>/dev/null || MISSING+=("$PYTHON_GOBJECT")

PYQT_OK=false
python3 -c "from PyQt6.QtWidgets import QApplication" 2>/dev/null && PYQT_OK=true
python3 -c "from PyQt5.QtWidgets import QApplication" 2>/dev/null && PYQT_OK=true
[ "$PYQT_OK" = false ] && MISSING+=("$PYTHON_PYQT6")

python3 -c "import markdown" 2>/dev/null || MISSING+=("$PYTHON_MARKDOWN")

command -v kdialog &>/dev/null || echo -e "${YELLOW}kdialog not found (optional fallback)${NC}"
command -v xclip &>/dev/null || command -v wl-copy &>/dev/null || MISSING+=("$XCLIP")

if [ ${#MISSING[@]} -ne 0 ]; then
    echo -e "${YELLOW}Missing packages: ${MISSING[*]}${NC}"
    read -p "Install missing dependencies now? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $PKG_MANAGER "${MISSING[@]}"
    else
        echo -e "${RED}Dependencies are required. Install manually and re-run.${NC}"
        exit 1
    fi
fi

# --- CREATE DIRECTORIES ---
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p "$PLUGIN_DIR"
mkdir -p "$KRUNNER_DIR"
mkdir -p "$DBUS_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "${ICON_DIR}/128x128/apps"
mkdir -p "${ICON_DIR}/scalable/apps"
mkdir -p "$HOME/.config/katten"

# --- COPY FILES ---
echo -e "${BLUE}Installing files...${NC}"

# Main plugin
cp "$SCRIPT_DIR/katten.py" "$PLUGIN_DIR/"
chmod +x "$PLUGIN_DIR/katten.py"

# Preview panel
if [ -f "$SCRIPT_DIR/quicklook_panel.py" ]; then
    cp "$SCRIPT_DIR/quicklook_panel.py" "$PLUGIN_DIR/"
    chmod +x "$PLUGIN_DIR/quicklook_panel.py"
fi

# First-run panel
if [ -f "$SCRIPT_DIR/first_run_panel.py" ]; then
    cp "$SCRIPT_DIR/first_run_panel.py" "$PLUGIN_DIR/"
    chmod +x "$PLUGIN_DIR/first_run_panel.py"
fi

# Icons
if [ -f "$SCRIPT_DIR/katten-icon.svg" ]; then
    cp "$SCRIPT_DIR/katten-icon.svg" "$PLUGIN_DIR/"
    cp "$SCRIPT_DIR/katten-icon.svg" "${ICON_DIR}/scalable/apps/"
elif [ -f "$SCRIPT_DIR/katten-icon.png" ]; then
    cp "$SCRIPT_DIR/katten-icon.png" "$PLUGIN_DIR/"
    cp "$SCRIPT_DIR/katten-icon.png" "${ICON_DIR}/128x128/apps/"
fi

# KRunner plugin registration
cp "$SCRIPT_DIR/katten.desktop" "$KRUNNER_DIR/"

# D-Bus service
cp "$SCRIPT_DIR/org.kde.katten.service" "$DBUS_DIR/"

# Autostart configuration (so plugin starts automatically on login)
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

# Create autostart .desktop file
cat > "$AUTOSTART_DIR/katten.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Katten (Mistral Vibe)
Comment=Start Katten KRunner plugin automatically
Exec=python3 $PLUGIN_DIR/katten.py
OnlyShowIn=KDE;
NoDisplay=true
StartupNotify=false
Terminal=false
EOF
chmod +x "$AUTOSTART_DIR/katten.desktop"

# Config tool
cp "$SCRIPT_DIR/katten-config" "$BIN_DIR/"
chmod +x "$BIN_DIR/katten-config"

# Update icon cache
echo -e "${BLUE}Updating icon cache...${NC}"
gtk-update-icon-cache -f "${ICON_DIR}" 2>/dev/null || true

# --- RESTART SERVICES ---
echo -e "${BLUE}Stopping any existing plugin...${NC}"
pkill -f "katten.py" 2>/dev/null || true

echo -e "${BLUE}Restarting KRunner...${NC}"
kquitapp6 krunner 2>/dev/null || kquitapp5 krunner 2>/dev/null || true
sleep 1

# --- SUCCESS ---
echo
echo "========================================"
echo -e "${GREEN}Installation complete!${NC}"
echo "========================================"
echo
echo "Installation mode: $INSTALL_MODE"
echo "Plugin directory: $PLUGIN_DIR"
echo
echo -e "${BLUE}IMPORTANT: Set up your Mistral API key:${NC}"
echo
echo "   Run: katten-config"
echo
echo "   (If command not found, use: $BIN_DIR/katten-config)"
echo
echo "For full markdown rendering support (tables, code blocks, etc.):"
echo -e "   Ensure python3-markdown is installed: ${YELLOW}sudo apt install python3-markdown${NC}"
echo
echo "Then test in KRunner (Alt+Space):"
echo -e "   ${YELLOW}katten Hello, how are you?${NC}"
echo

echo "IMPORTANT: For the plugin to work automatically on login:"
echo -e "   ${YELLOW}Log out and log back in${NC} to activate the autostart configuration"
echo "   (or restart your session)"

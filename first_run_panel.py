#!/usr/bin/python3
"""
First-run configuration panel for Katten.

This provides a simple, native KDE Plasma dialog for entering the Mistral API key
on first use. It's intentionally minimal to reduce bug surface area.

Copyright 2026 Emilio González Longoria.
Katten is distributed under the terms of the GNU General Public License v3.
"""

import sys
import subprocess
import json
from pathlib import Path

# Try PyQt6 first, fall back to PyQt5
try:
    from PyQt6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QWidget,
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    PYQT_VERSION = 6
    WA_DeleteOnClose = Qt.WidgetAttribute.WA_DeleteOnClose
    WindowType_Window = Qt.WindowType.Window
    WindowType_Close = Qt.WindowType.WindowCloseButtonHint
    Key_Return = Qt.Key.Key_Return
    Key_Enter = Qt.Key.Key_Enter
except ImportError:
    from PyQt5.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QWidget,
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QIcon
    PYQT_VERSION = 5
    WA_DeleteOnClose = Qt.WA_DeleteOnClose
    WindowType_Window = Qt.Window
    WindowType_Close = Qt.WindowCloseButtonHint
    Key_Return = Qt.Key_Return
    Key_Enter = Qt.Key_Enter


CONFIG_DIR = Path.home() / ".config" / "katten"
CONFIG_FILE = CONFIG_DIR / "config.json"


class FirstRunPanel(QDialog):
    """Simple first-run configuration dialog for entering Mistral API key."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Katten - First Run Setup")
        self.setWindowFlags(WindowType_Window | WindowType_Close)
        self.setAttribute(WA_DeleteOnClose, True)
        self.setMinimumSize(480, 200)
        self.resize(520, 220)

        # Try to use plugin icon
        icon_path = Path.home() / ".local" / "share" / "katten" / "katten-icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title
        title = QLabel("<b>Welcome to Katten!</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Katten connects KRunner to Mistral AI's Le Chat service."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Info about API key
        info = QLabel(
            "<small>An API key is <b>not required</b> to use the plugin, "
            "but may be needed to access all of Le Chat's functions.</small>"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)

        # Spacer
        layout.addSpacing(12)

        # API Key label
        api_label = QLabel("Mistral API Key:")
        layout.addWidget(api_label)

        # API Key input
        self._api_input = QLineEdit()
        self._api_input.setPlaceholderText(
            "Enter your API key from https://console.mistral.ai/api-keys"
        )
        self._api_input.setEchoMode(QLineEdit.EchoMode.Normal)
        self._api_input.returnPressed.connect(self._save_and_close)
        layout.addWidget(self._api_input)

        # Buttons row
        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        # Save button
        save_btn = QPushButton("Save & Continue")
        save_btn.clicked.connect(self._save_and_close)
        save_btn.setDefault(True)
        buttons.addWidget(save_btn)

        # CLI Settings button
        cli_btn = QPushButton("Open CLI Settings")
        cli_btn.clicked.connect(self._open_cli_settings)
        buttons.addWidget(cli_btn)

        layout.addLayout(buttons)

        # Bottom info
        bottom_info = QLabel(
            "<small><i>You can also run 'katten-config' from the terminal anytime.</i></small>"
        )
        bottom_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(bottom_info)

    def _save_and_close(self):
        """Save the API key and close the dialog."""
        api_key = self._api_input.text().strip()

        if api_key:
            # Save to config
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            config = {"api_key": api_key}

            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=2)
                # Set restrictive permissions
                CONFIG_FILE.chmod(0o600)
            except Exception as e:
                # Non-blocking: show error but still close
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Save Error",
                    f"Could not save API key: {e}"
                )

        self.accept()

    def _open_cli_settings(self):
        """Open the CLI configuration tool in a terminal."""
        try:
            # Try different terminal emulators
            terminals = [
                ("konsole", ["konsole", "-e", "katten-config"]),
                ("xfce4-terminal", ["xfce4-terminal", "-e", "katten-config"]),
                ("gnome-terminal", ["gnome-terminal", "--", "katten-config"]),
                ("xterm", ["xterm", "-e", "katten-config"]),
            ]

            # Also try direct paths
            direct_commands = [
                ["katten-config"],
                ["bash", "-c", "katten-config"],
                ["python3", "~/.local/bin/katten-config"],
            ]

            # Try all options
            for name, cmd in terminals + direct_commands:
                try:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return  # Success - exit on first working option
                except FileNotFoundError:
                    continue

            # If we get here, no terminal worked - show message
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Terminal Not Found",
                "Could not find a terminal emulator. "
                "Please run 'katten-config' manually from your terminal."
            )
        except Exception:
            pass


def show_first_run_panel():
    """Show the first-run panel. Returns True if user saved a key, False otherwise."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setApplicationName("Katten First Run")
        # Set a default style if available
        try:
            from PyQt6.QtWidgets import QStyleFactory
            if "Breeze" in QStyleFactory.keys():
                app.setStyle("Breeze")
        except Exception:
            pass

    panel = FirstRunPanel()
    result = panel.exec()

    # If we created the app, we need to handle it
    if QApplication.instance() == app and app is not None:
        # Don't quit - let caller handle app lifecycle
        pass

    return result == QDialog.DialogCode.Accepted


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Katten First Run")
    show_first_run_panel()
    sys.exit(0)

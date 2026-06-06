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
import threading
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Try PyQt6 first, fall back to PyQt5
try:
    from PyQt6.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QWidget, QSizePolicy,
    )
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QIcon, QDesktopServices
    from PyQt6.QtCore import QUrl
    PYQT_VERSION = 6
    WA_DeleteOnClose = Qt.WidgetAttribute.WA_DeleteOnClose
    WindowType_Window = Qt.WindowType.Window
    WindowType_Close = Qt.WindowType.WindowCloseButtonHint
    Key_Return = Qt.Key.Key_Return
    Key_Enter = Qt.Key.Key_Enter
    SizePolicy_Expanding = QSizePolicy.Policy.Expanding
    SizePolicy_MinimumExpanding = QSizePolicy.Policy.MinimumExpanding
except ImportError:
    from PyQt5.QtWidgets import (
        QApplication, QDialog, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QWidget, QSizePolicy,
    )
    from PyQt5.QtCore import Qt, QTimer, QUrl
    from PyQt5.QtGui import QIcon, QDesktopServices
    PYQT_VERSION = 5
    WA_DeleteOnClose = Qt.WA_DeleteOnClose
    WindowType_Window = Qt.Window
    WindowType_Close = Qt.WindowCloseButtonHint
    Key_Return = Qt.Key_Return
    Key_Enter = Qt.Key_Enter
    SizePolicy_Expanding = QSizePolicy.Expanding
    SizePolicy_MinimumExpanding = QSizePolicy.MinimumExpanding


CONFIG_DIR = Path.home() / ".config" / "katten"
CONFIG_FILE = CONFIG_DIR / "config.json"

# API validation constants
TEST_PROMPT = (
    "This prompt is a test to verify the correct connection to Mistral AI. "
    "Reply correctsetup if you are ready to receive more prompts. "
    "Do not reply anything other than correctsetup or error."
)


class FirstRunPanel(QDialog):
    """Simple first-run configuration dialog for entering Mistral API key."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Katten - First Run Setup")
        self.setWindowFlags(WindowType_Window | WindowType_Close)
        self.setAttribute(WA_DeleteOnClose, True)
        self.setMinimumSize(560, 400)
        self.resize(600, 450)

        # Try to use plugin icon
        icon_path = Path.home() / ".local" / "share" / "katten" / "katten-icon.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # State variables
        self._validation_in_progress = False
        self._api_valid = False
        
        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("<b><big>Welcome to Katten!</big></b>")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "Katten connects KRunner to Mistral AI's Vibe service. "
            "You can ask questions and get answers directly from your desktop."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignLeft)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Info about API key - left aligned and with hyperlink
        info_text = (
            "To access all features, you need a Mistral API key. "
            "You can generate one at <a href='https://console.mistral.ai/api-keys'>console.mistral.ai/api-keys</a>."
        )
        info = QLabel(f"<small>{info_text}</small>")
        info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        info.setWordWrap(True)
        info.setMargin(8)
        info.setOpenExternalLinks(True)
        layout.addWidget(info)

        # Spacer
        layout.addSpacing(16)

        # API Key label
        api_label = QLabel("Mistral API Key:")
        api_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(api_label)

        # API Key input
        self._api_input = QLineEdit()
        self._api_input.setPlaceholderText("Enter your Mistral API key")
        self._api_input.setEchoMode(QLineEdit.EchoMode.Normal)
        self._api_input.textChanged.connect(self._on_api_text_changed)
        self._api_input.returnPressed.connect(self._validate_and_save)
        self._api_input.setMinimumHeight(32)
        self._api_input.setSizePolicy(SizePolicy_Expanding, SizePolicy_Expanding)
        layout.addWidget(self._api_input)

        # Paste button
        paste_btn = QPushButton("Paste")
        paste_btn.clicked.connect(self._paste_api_key)
        paste_btn.setSizePolicy(SizePolicy_MinimumExpanding, QSizePolicy.Policy.Fixed)
        paste_btn.setMinimumHeight(32)
        paste_btn.setMaximumHeight(32)
        layout.addWidget(paste_btn)

        # Throbber (loading indicator)
        self._throbber_label = QLabel()
        self._throbber_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._throbber_label.setVisible(False)
        self._throbber_label.setMinimumHeight(20)
        layout.addWidget(self._throbber_label)

        # Error message label
        self._error_label = QLabel()
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._error_label.setWordWrap(True)
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setVisible(False)
        self._error_label.setMinimumHeight(20)
        layout.addWidget(self._error_label)

        # Add stretch to allow vertical expansion
        layout.addStretch(1)

        # Buttons row
        buttons = QHBoxLayout()
        buttons.setSpacing(16)
        buttons.addStretch()

        # CLI Settings button
        cli_btn = QPushButton("Open CLI Settings")
        cli_btn.clicked.connect(self._open_cli_settings)
        cli_btn.setSizePolicy(SizePolicy_MinimumExpanding, SizePolicy_Expanding)
        cli_btn.setMinimumHeight(36)
        buttons.addWidget(cli_btn)

        # Save button - primary button
        self._save_btn = QPushButton("Save and continue")
        self._save_btn.clicked.connect(self._validate_and_save)
        self._save_btn.setDefault(True)
        self._save_btn.setSizePolicy(SizePolicy_MinimumExpanding, SizePolicy_Expanding)
        self._save_btn.setMinimumHeight(36)
        self._save_btn.setEnabled(False)  # Disabled until API key is entered
        
        # Make it primary button (blue accent on KDE Breeze)
        if PYQT_VERSION == 6:
            self._save_btn.setStyleSheet("QPushButton { background-color: #3daee9; color: white; border: none; padding: 8px; border-radius: 4px; } QPushButton:disabled { background-color: #e0e0e0; color: #999999; }")
        else:
            self._save_btn.setStyleSheet("QPushButton { background-color: #3daee9; color: white; border: none; padding: 8px; border-radius: 4px; } QPushButton:disabled { background-color: #e0e0e0; color: #999999; }")
        
        buttons.addWidget(self._save_btn)

        buttons.addStretch()
        layout.addLayout(buttons)

        # Add a spacer before bottom info
        layout.addSpacing(12)
        
        # Bottom info
        bottom_info = QLabel(
            "<small><i>You can also run 'katten-config' from the terminal anytime.</i></small>"
        )
        bottom_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_info.setMargin(8)
        layout.addWidget(bottom_info)

    def _on_api_text_changed(self, text):
        """Handle text changes in the API key input field."""
        # Enable/disable save button based on whether there's text
        has_text = bool(text.strip())
        self._save_btn.setEnabled(has_text)
        
        # Clear error message when user starts typing again
        if has_text and self._error_label.isVisible():
            self._error_label.setVisible(False)
            self._api_valid = False

    def _paste_api_key(self):
        """Paste API key from clipboard."""
        try:
            clipboard = QApplication.clipboard()
            if clipboard:
                text = clipboard.text().strip()
                if text:
                    self._api_input.setText(text)
                    self._api_input.setFocus()
        except Exception:
            pass

    def _show_throbber(self, show=True):
        """Show or hide the throbber with animated dots."""
        if show:
            self._throbber_label.setText("<i>Verifying API key...</i>")
            self._throbber_label.setVisible(True)
            # Start animation
            self._throbber_dots = 0
            self._throbber_timer = QTimer(self)
            self._throbber_timer.timeout.connect(self._update_throbber)
            self._throbber_timer.start(300)
        else:
            if hasattr(self, '_throbber_timer'):
                self._throbber_timer.stop()
            self._throbber_label.setVisible(False)

    def _update_throbber(self):
        """Update the throbber animation."""
        dots = "." * (self._throbber_dots % 4)
        self._throbber_label.setText(f"<i>Verifying API key{dots}</i>")
        self._throbber_dots += 1

    def _validate_api_key(self, api_key):
        """Test the API key by sending a test prompt to Mistral API."""
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": TEST_PROMPT}],
        }
        try:
            req = Request(url, method="POST", headers=headers)
            req.data = json.dumps(payload).encode()
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                choices = data.get("choices", [])
                if not choices:
                    return False, "Empty response from API"
                reply = choices[0].get("message", {}).get("content", "").strip().lower()
                if reply == "correctsetup":
                    return True, ""
                return False, f"Unexpected reply from API"
        except HTTPError as e:
            body = e.read().decode() if e.fp else str(e)
            try:
                msg = json.loads(body).get("message", body)
            except Exception:
                msg = body
            return False, f"HTTP {e.code}: {msg[:200]}"
        except URLError as e:
            return False, f"Network error: {e.reason}"
        except Exception as e:
            return False, str(e)

    def _validate_and_save(self):
        """Validate the API key and save if valid."""
        api_key = self._api_input.text().strip()
        
        if not api_key:
            return
        
        # Show throbber and disable buttons during validation
        self._show_throbber(True)
        self._save_btn.setEnabled(False)
        self._validation_in_progress = True
        self._error_label.setVisible(False)
        
        # Perform validation in a background thread to avoid freezing the UI
        def validation_task():
            try:
                ok, error_msg = self._validate_api_key(api_key)
                
                # Use QTimer to update UI from main thread
                QTimer.singleShot(0, lambda: self._complete_validation(ok, error_msg, api_key))
            except Exception as e:
                QTimer.singleShot(0, lambda: self._complete_validation(False, str(e), api_key))
        
        # Start validation thread
        threading.Thread(target=validation_task, daemon=True).start()

    def _complete_validation(self, ok, error_msg, api_key):
        """Complete the validation process and update UI."""
        self._show_throbber(False)
        self._validation_in_progress = False
        self._api_valid = ok
        
        if ok:
            # API key is valid - save and close
            self._save_config(api_key)
            self.accept()
        else:
            # Show error and re-enable save button
            self._error_label.setText(f"<small>{error_msg}</small>")
            self._error_label.setVisible(True)
            self._save_btn.setEnabled(True)

    def _save_config(self, api_key):
        """Save the API key to config file."""
        if api_key:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            config = {"api_key": api_key}
            
            try:
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=2)
                # Set restrictive permissions
                CONFIG_FILE.chmod(0o600)
            except Exception as e:
                # Non-blocking: show error but still close
                if PYQT_VERSION == 6:
                    from PyQt6.QtWidgets import QMessageBox
                else:
                    from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Save Error",
                    f"Could not save API key: {e}"
                )

    def _save_and_close(self):
        """Legacy method for backward compatibility - now redirects to validation."""
        self._validate_and_save()

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
            if PYQT_VERSION == 6:
                from PyQt6.QtWidgets import QMessageBox
            else:
                from PyQt5.QtWidgets import QMessageBox
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

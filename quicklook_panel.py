#!/usr/bin/python3
"""
Preview panel for Katten - Unofficial Mistral Le Chat plugin for KRunner.

Copyright 2026 Emilio González Longoria.
Katten is distributed under the terms of the GNU General Public License v3.
See https://www.gnu.org/licenses/gpl-3.0.html for details.

Approach:
  - NO WA_TranslucentBackground.  That attribute makes every child widget
    transparent too, which is why QTextBrowser showed no text.
  - The window is fully opaque and uses the system palette (Breeze/Oxygen/etc.)
    so it looks native in any KDE theme.
  - Blur-behind is still requested via xprop so KWin applies it as a
    compositor decoration hint — this works independently of transparency.
  - Content is loaded from a JSON temp file passed as --response-file to
    avoid command-line length / shell-quoting issues.
"""

import sys
import subprocess
import argparse
import re
import os
import json
import logging
import tempfile
from pathlib import Path

# -------------------------------------------------------------------
# Logging to a temp file so we can see errors without a terminal
# -------------------------------------------------------------------
_log_path = Path(tempfile.gettempdir()) / "katten-panel.log"
logging.basicConfig(
    filename=str(_log_path),
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("katten-panel")

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTextBrowser, QPushButton, QFrame, QStyleFactory,
    )
    from PyQt6.QtCore import Qt, QUrl, QTimer
    from PyQt6.QtGui import (
        QPalette, QIcon, QShortcut, QKeySequence, QDesktopServices,
    )
    PYQT_VERSION = 6
    WA_DeleteOnClose  = Qt.WidgetAttribute.WA_DeleteOnClose
    WindowType_Window   = Qt.WindowType.Window
    WindowType_Close    = Qt.WindowType.WindowCloseButtonHint
    WindowType_Minimize = Qt.WindowType.WindowMinimizeButtonHint
    HLine               = QFrame.Shape.HLine
    Sunken              = QFrame.Shadow.Sunken
    Key_Space           = Qt.Key.Key_Space
    Key_Escape          = Qt.Key.Key_Escape
    log.info("PyQt6 loaded")
except ImportError as e:
    log.warning("PyQt6 not found (%s), trying PyQt5", e)
    try:
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QTextBrowser, QPushButton, QFrame, QStyleFactory,
        )
        from PyQt5.QtCore import Qt, QUrl, QTimer
        from PyQt5.QtGui import (
            QPalette, QIcon, QShortcut, QKeySequence, QDesktopServices,
        )
        PYQT_VERSION = 5
        WA_DeleteOnClose  = Qt.WA_DeleteOnClose
        WindowType_Window   = Qt.Window
        WindowType_Close    = Qt.WindowCloseButtonHint
        WindowType_Minimize = Qt.WindowMinimizeButtonHint
        HLine               = QFrame.HLine
        Sunken              = QFrame.Sunken
        Key_Space           = Qt.Key_Space
        Key_Escape          = Qt.Key_Escape
        log.info("PyQt5 loaded")
    except ImportError as e2:
        log.critical("Neither PyQt6 nor PyQt5 found: %s", e2)
        print("Error: PyQt6 or PyQt5 is required. Install with:  sudo apt install python3-pyqt6")
        sys.exit(1)

# ---------------------------------------------------------------------------
# Markdown → HTML (using system markdown library)
# ---------------------------------------------------------------------------

try:
    import markdown as _md_lib
    HAS_MARKDOWN = True
    log.info("markdown library available")
except ImportError as _e:
    HAS_MARKDOWN = False
    log.warning("markdown library not available (%s) - will use plain text fallback", _e)
    # Log a user-friendly error message
    log.error("MARKDOWN NOT AVAILABLE: For full markdown rendering (tables, code blocks, etc.), "
               "please install: sudo apt install python3-markdown")


def markdown_to_html(text: str) -> str:
    """Convert markdown to HTML using the markdown library."""
    if HAS_MARKDOWN:
        try:
            # Use nl2br to convert single newlines to <br>, which helps
            # with formatting but can interfere with tables.
            # We process the text to protect table blocks first.
            md = _md_lib.Markdown(
                extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
            )
            return md.convert(text)
        except Exception as e:
            log.error("markdown conversion failed: %s", e)
            # Fallback to plain text with line breaks
            from html import escape
            return '<p>' + escape(text).replace('\n\n', '</p><p>').replace('\n', '<br>') + '</p>'
    # No markdown library - show plain text with line breaks AND a user-visible note
    from html import escape
    plain_html = '<p>' + escape(text).replace('\n\n', '</p><p>').replace('\n', '<br>') + '</p>'
    # Add a subtle note about markdown not being available
    plain_html += '<p><small><i>Note: For full markdown support, install python3-markdown package</i></small></p>'
    return plain_html


# ---------------------------------------------------------------------------
# Palette helpers
# ---------------------------------------------------------------------------

def _pcol(role6, role5=None):
    pal = QApplication.instance().palette()
    if PYQT_VERSION == 6:
        return pal.color(role6)
    return pal.color(role5 if role5 is not None else role6)


def _is_dark() -> bool:
    if PYQT_VERSION == 6:
        bg = _pcol(QPalette.ColorRole.Window)
    else:
        bg = _pcol(QPalette.Window)
    return (0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()) < 128


def _build_html(body_html: str) -> str:
    if PYQT_VERSION == 6:
        text_c = _pcol(QPalette.ColorRole.Text).name()
        link_c = _pcol(QPalette.ColorRole.Link).name()
        hi_c   = _pcol(QPalette.ColorRole.Highlight).name()
        mid_c  = _pcol(QPalette.ColorRole.Mid).name()
        base_c = _pcol(QPalette.ColorRole.Base).name()
    else:
        text_c = _pcol(QPalette.Text).name()
        link_c = _pcol(QPalette.Link).name()
        hi_c   = _pcol(QPalette.Highlight).name()
        mid_c  = _pcol(QPalette.Mid).name()
        base_c = _pcol(QPalette.Base).name()

    dark = _is_dark()
    code_bg = "rgba(128,128,128,0.18)"
    pre_bg  = "rgba(0,0,0,0.10)" if dark else "rgba(0,0,0,0.05)"

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* {{ box-sizing: border-box; }}
body {{
    font-family: sans-serif;
    font-size: 11pt;
    line-height: 1.55;
    color: {text_c};
    background: {base_c};
    margin: 0;
    padding: 4px 8px;
}}
h1,h2,h3,h4,h5,h6 {{ color: {hi_c}; margin: 14px 0 6px; }}
h1 {{ font-size: 17pt; }}
h2 {{ font-size: 14pt; }}
h3 {{ font-size: 12pt; }}
p  {{ margin: 0 0 10px 0; }}
a  {{ color: {link_c}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
code {{
    background: {code_bg};
    padding: 1px 4px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 10pt;
}}
pre {{
    background: {pre_bg};
    padding: 10px 12px;
    font-family: monospace;
    font-size: 10pt;
    line-height: 1.4;
    margin: 8px 0;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
pre code {{ background: transparent; padding: 0; }}
ul,ol {{ margin: 6px 0; padding-left: 22px; }}
li {{ margin: 3px 0; }}
blockquote {{
    border-left: 3px solid {hi_c};
    margin: 8px 0;
    padding-left: 10px;
    opacity: .85;
}}
table {{ border-collapse: collapse; margin: 10px 0; width: 100%; }}
th,td {{ border: 1px solid {mid_c}; padding: 6px 10px; text-align: left; }}
th {{ background: {code_bg}; }}
hr {{ border: none; border-top: 1px solid {mid_c}; margin: 14px 0; }}
</style></head><body>
{body_html}
</body></html>"""


# ---------------------------------------------------------------------------
# KWin blur-behind (X11)
# ---------------------------------------------------------------------------

def _request_blur(win_id: int):
    try:
        subprocess.run(
            ["xprop", "-id", str(win_id),
             "-f", "_KDE_NET_WM_BLUR_BEHIND_REGION", "32c",
             "-set", "_KDE_NET_WM_BLUR_BEHIND_REGION", "0"],
            capture_output=True, timeout=3,
        )
        log.debug("blur-behind requested for win %s", win_id)
    except Exception as exc:
        log.debug("blur request failed: %s", exc)


# ---------------------------------------------------------------------------
# PreviewPanel
# ---------------------------------------------------------------------------

class PreviewPanel(QMainWindow):

    def __init__(self, title="Katten", content="", prompt="",
                 url="https://chat.mistral.ai/"):
        super().__init__()
        self._content = content
        self._prompt  = prompt
        self._url     = url

        self._setup_window(title)
        self._build_ui()
        self._setup_shortcuts()
        self._show_content(content)

        QTimer.singleShot(200, self._apply_blur)
        log.info("PreviewPanel created: title=%r content_len=%d", title, len(content))

    # ------------------------------------------------------------------
    # Window setup
    # ------------------------------------------------------------------

    def _setup_window(self, title: str):
        self.setWindowTitle(title)
        self.setMinimumSize(560, 360)
        self.resize(700, 520)
        # No maximize button
        self.setWindowFlags(
            WindowType_Window | WindowType_Close | WindowType_Minimize
        )
        # DO NOT set WA_TranslucentBackground — it makes child widgets transparent
        # and causes QTextBrowser to render invisible text.
        self.setAttribute(WA_DeleteOnClose, True)

        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.availableGeometry()
            self.move(
                (sg.width()  - self.width())  // 2,
                (sg.height() - self.height()) // 2,
            )

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(10)

        sep = QFrame()
        sep.setFrameShape(HLine)
        sep.setFrameShadow(Sunken)
        outer.addWidget(sep)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.setOpenLinks(True)
        outer.addWidget(self._browser, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._copy_btn = QPushButton("Copy")
        self._copy_btn.setIcon(QIcon.fromTheme("edit-copy"))
        self._copy_btn.clicked.connect(self._copy)
        self._copy_btn.setToolTip("Copy full response to clipboard")
        btn_row.addWidget(self._copy_btn)

        self._open_btn = QPushButton("Open in Browser")
        for name in ("internet-services", "applications-internet", "emblem-web"):
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                self._open_btn.setIcon(icon)
                break
        self._open_btn.clicked.connect(self._open_browser)
        self._open_btn.setToolTip(
            "Open chat.mistral.ai in your default browser.\n"
            "Note: API conversations are separate from your Le Chat web account."
        )
        btn_row.addWidget(self._open_btn)

        btn_row.addStretch()
        outer.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Shortcuts
    # ------------------------------------------------------------------

    def _setup_shortcuts(self):
        for key in (Key_Space, Key_Escape):
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(self.close)

    def keyPressEvent(self, event):
        if event.key() in (Key_Space, Key_Escape):
            self.close()
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Blur
    # ------------------------------------------------------------------

    def _apply_blur(self):
        try:
            _request_blur(int(self.winId()))
        except Exception as exc:
            log.debug("_apply_blur error: %s", exc)

    # ------------------------------------------------------------------
    # Content
    # ------------------------------------------------------------------

    def _show_content(self, text: str):
        self._content = text
        try:
            body  = markdown_to_html(text)
            html  = _build_html(body)
            self._browser.setHtml(html)
            log.info("content rendered, html length=%d", len(html))
        except Exception as exc:
            log.exception("render error")
            # Last-resort: show plain text so the user sees something
            self._browser.setPlainText(text)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _copy(self):
        QApplication.clipboard().setText(self._content)
        orig = self._copy_btn.text()
        self._copy_btn.setText("Copied!")
        QTimer.singleShot(1500, lambda: self._copy_btn.setText(orig))

    def _open_browser(self):
        try:
            # Try xdg-open first (respects user's default browser on Linux)
            result = subprocess.run(
                ["xdg-open", self._url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if result.returncode != 0:
                raise Exception("xdg-open failed")
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            # Fallback to Qt's desktop services if xdg-open fails
            try:
                QDesktopServices.openUrl(QUrl(self._url))
            except Exception as e:
                log.error("Failed to open URL: %s", e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    log.info("panel starting, args=%s", sys.argv)

    parser = argparse.ArgumentParser(description="Katten preview panel")
    parser.add_argument("--response-file", default="", dest="response_file")
    parser.add_argument("--title",   default="Katten")
    parser.add_argument("--content", default="")
    parser.add_argument("--prompt",  default="")
    parser.add_argument("--url",     default="https://chat.mistral.ai/")
    args = parser.parse_args()

    title   = args.title
    content = args.content
    prompt  = args.prompt
    url     = args.url

    if args.response_file:
        log.info("loading response file: %s", args.response_file)
        try:
            with open(args.response_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            title   = data.get("title",   title)
            content = data.get("content", content)
            prompt  = data.get("prompt",  prompt)
            url     = data.get("url",     url)
            log.info("response file loaded ok, content_len=%d", len(content))
        except Exception as exc:
            log.exception("failed to load response file")
            content = f"**Error reading response:** {exc}"
        finally:
            try:
                os.unlink(args.response_file)
            except Exception:
                pass

    if not content:
        log.warning("no content to display — aborting")
        # Nothing to show; exit silently so the user only sees the notification
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setApplicationName("Katten")

    styles_lower = [s.lower() for s in QStyleFactory.keys()]
    if "breeze" in styles_lower:
        app.setStyle("Breeze")
        log.info("Breeze style applied")

    # Prefer SVG icon, fall back to PNG
    icon_path = Path.home() / ".local" / "share" / "katten" / "katten-icon.svg"
    if not icon_path.exists():
        icon_path = Path.home() / ".local" / "share" / "katten" / "katten-icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    panel = PreviewPanel(title=title, content=content, prompt=prompt, url=url)
    panel.show()
    log.info("panel.show() called")

    sys.exit(app.exec() if PYQT_VERSION == 6 else app.exec_())


if __name__ == "__main__":
    main()

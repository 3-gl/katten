Katten v0.4.1 (Beta)
==================
Unofficial Mistral Vibe plugin for KRunner

Developed by Emilio Longoria.
This plugin is not affiliated with Mistral AI or its products.


DESCRIPTION
-----------
Katten is a KDE Plasma 6 KRunner plugin that lets you send prompts to
Mistral AI's Vibe and see responses in a beautiful preview panel
with full markdown rendering (tables, code blocks, etc.).


FEATURES
--------
- Send prompts to Mistral AI directly from KRunner
- Web search enabled by default (Vibe searches the internet)
- Preview panel with:
  - Background blur and transparency
  - Full markdown rendering (headers, code blocks, tables, lists, links)
  - Copy to clipboard button
  - Open in Browser button to continue conversation
  - Close with Spacebar, Escape, or close button
- Persistent loading notification while generating
- Multiple trigger keywords: katten, lechat, lc, mistral (customizable)
- Support for custom Mistral agents from your account
- Custom SVG plugin icon
- Conversation history logged to XML file
- Uses system python3-markdown package (no isolated venv needed)


REQUIREMENTS
------------
- KDE Plasma 6.x (Kubuntu 24.04, KDE neon, or later)
- Python 3.x
- python3-dbus package
- python3-gi package (GObject Introspection)
- python3-pyqt6 or python3-pyqt5 package (for preview panel)
- python3-markdown package (for full markdown rendering)
- xclip or wl-copy (for clipboard support)

Optional:
- kdialog (fallback if PyQt6/PyQt5 is unavailable)
- xprop (for KWin blur effect)


INSTALLATION
------------

### Method 1: From Debian/Ubuntu Package (Recommended)

If a .deb package is available:

   sudo apt install ./krunner-lechat_*.deb

### Method 2: Manual Installation

1. Open a terminal in this folder

2. Make the install script executable:
   chmod +x install.sh

3. Run the installer:
   ./install.sh

   This will:
   - Check and install missing dependencies
   - Copy files to ~/.local/share/katten/
   - Register the plugin with KRunner
   - Set up the D-Bus service
   - Install the icon

4. Configure your API key:
   katten-config

5. Restart KRunner:
   kquitapp6 krunner

6. Test it! Open KRunner (Alt+Space) and type:
   katten Hello, how are you?

### Method 3: Flatpak (Cross-Distribution)

If a Flatpak is available:

   flatpak install org.kde.katten.json
   flatpak run org.kde.katten


CONFIGURATION
-------------

### First-Run Setup

Before using Katten, you MUST configure your Mistral AI API key:

   katten-config

This command will prompt you to enter your API key from:
https://console.mistral.ai/api-keys

### Configuration Options

The katten-config tool allows you to:
- Set your Mistral API key
- Customize trigger keywords (e.g., ai, ask, chat)
- Enable/disable web search by default
- Select a default custom agent

Configuration file location:
  ~/.config/katten/config.json


USAGE
-----
Open KRunner with Alt+Space or Alt+F2, then type any trigger keyword:

TRIGGER KEYWORDS (configurable):
  katten    - Primary keyword
  lechat    - Alternative keyword
  lc        - Short alias
  mistral   - Alternative keyword

COMMANDS:

  katten <your question>
    Example: katten What is quantum computing?
    Sends your question to Mistral AI with web search enabled.

  katten web <question>
    Forces web search for this specific query.

  katten noweb <question>
    Disables web search for this specific query.

  katten agents
    Lists all your custom Mistral agents.

  katten use agent <name>
    Sets a custom agent as the default for all queries.
    Example: katten use agent My Helper

  katten clear agent
    Clears the default agent, returns to using the base model.

  katten show
    Shows the last response again.

You can use any trigger keyword interchangeably:
  lc What is Python?
  mistral Explain machine learning


PREVIEW PANEL
-------------
Responses are displayed in a native preview panel with KDE Plasma integration:

- Background blur with transparency
- Full markdown rendering:
  - Headers (# ## ###)
  - Bold and italic text
  - Code blocks with syntax highlighting
  - Inline code
  - Tables
  - Bulleted and numbered lists
  - Clickable hyperlinks
- Copy button: Copy the full response to clipboard
- Open in Browser button: Opens Vibe in your default browser
- Close with: Spacebar, Escape, or the close button

If PyQt6/PyQt5 is not available, kdialog is used as a fallback.


TROUBLESHOOTING
---------------

"API key not configured" error:
  Run: katten-config
  Enter your Mistral API key from console.mistral.ai

Plugin not appearing in KRunner:
  1. Check if files are installed:
     ls ~/.local/share/katten/
     ls ~/.local/share/krunner/dbusplugins/
     ls ~/.local/share/dbus-1/services/
  
  2. Manually start the plugin to check for errors:
     python3 ~/.local/share/katten/katten.py
  
  3. In another terminal, restart KRunner:
     kquitapp6 krunner
  
  4. The plugin should auto-start when you open KRunner.

Preview panel not showing blur:
  - Blur requires KDE Plasma compositing to be enabled
  - Check Desktop Effects in System Settings
  - On some systems, you may need "Better Blur" effect
  - Falls back to semi-transparent background if blur unavailable

"Not recognized" / Account features:
  The Mistral API does not have access to your Vibe web account's
  personal data or conversation history. This is by design for privacy.
  However, you can use custom agents created at console.mistral.ai

API errors (404, 400):
  - Verify your API key is valid at console.mistral.ai
  - Try disabling web search: katten noweb <question>
  - Clear the cached agent: katten-config

Markdown not rendering:
  - Install python3-markdown: sudo apt install python3-markdown
  - Without markdown, responses will show as plain text with a note
  - Check /tmp/katten-panel.log for detailed errors


UNINSTALLING
------------
Run the uninstall script:
   ./uninstall.sh

Or manually remove:
   rm -rf ~/.local/share/katten/
   rm -f ~/.local/share/krunner/dbusplugins/katten.desktop
   rm -f ~/.local/share/dbus-1/services/org.kde.katten.service
   rm -f ~/.local/bin/katten-config
   rm -f ~/.local/share/icons/hicolor/scalable/apps/katten-icon.svg
   rm -rf ~/.config/katten/
   kquitapp6 krunner


API COSTS
---------
This plugin uses the Mistral AI API which may incur costs depending on
your usage. Check your usage and pricing at console.mistral.ai.

The plugin uses:
- mistral-medium-latest model for both web search and non-web queries

Note: The first time you use web search, the plugin creates a helper
agent in your Mistral account called "Katten WebSearch".


PACKAGING
---------
For distributors: Katten includes Debian packaging and Flatpak manifest.

Debian/Ubuntu:
  The debian/ directory contains standard Debian packaging files.
  Dependencies: python3, python3-dbus, python3-gi, python3-pyqt6 | python3-pyqt5,
               xclip | wl-copy, python3-markdown

Flatpak:
  See org.kde.katten.json for the Flatpak manifest.


DISCLAIMER
----------
Katten is an unofficial, community-developed plugin.
It is NOT affiliated with, endorsed by, or sponsored by Mistral AI.
"Vibe" and "Mistral" are trademarks of Mistral AI.

Use of this plugin requires a valid Mistral AI API key and is subject
to Mistral AI's terms of service and usage policies.


LICENSE
-------
GPL-3.0+ - See the COPYING file or https://www.gnu.org/licenses/gpl-3.0.html

Copyright (c) 2026 Emilio Gonzalez Longoria

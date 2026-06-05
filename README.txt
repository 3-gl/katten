Katten v3.0 beta
================
Unofficial Mistral Le Chat plugin for KRunner

Developed by Emilio Longoria.
This plugin is not affiliated with Mistral AI or its products.


DESCRIPTION
-----------
Katten is a KDE Plasma 6 KRunner plugin that lets you send prompts to
Mistral AI's Le Chat and see responses in a beautiful preview panel
with full markdown rendering (tables, code blocks, etc.).


FEATURES
--------
- Send prompts to Mistral AI directly from KRunner
- Web search enabled by default (Le Chat searches the internet)
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
- Isolated Python venv with markdown library (no system-wide install needed)


REQUIREMENTS
------------
- KDE Plasma 6.x (Kubuntu 24.04 or later)
- Python 3.x
- python3-dbus package
- python3-gi package (GObject Introspection)
- python3-pyqt6 package (for preview panel)
- Mistral AI API key (get one at https://console.mistral.ai/api-keys)

Optional:
- xclip or wl-copy (for clipboard support)
- kdialog (fallback if PyQt6 is unavailable)
- xprop (for KWin blur effect)

Note: The markdown library is automatically installed in an isolated
Python venv at ~/.local/share/katten/venv/ during setup.
No system-wide Python packages are needed!


INSTALLATION
------------
1. Open a terminal in this folder

2. Make the install script executable:
   chmod +x install.sh

3. Run the installer:
   ./install.sh

4. Configure your API key:
   katten-config

5. Test it! Open KRunner (Alt+Space) and type:
   katten Hello, how are you?


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
- Open in Browser button: Opens Le Chat in your default browser
- Close with: Spacebar, Escape, or the close button

If PyQt6/PyQt5 is not available, kdialog is used as a fallback.


CONFIGURATION
-------------
Run the configuration tool to modify settings:
   katten-config

Options include:
- Mistral API key
- Trigger keywords (customize or reset to defaults)
- Web search enabled/disabled by default
- Default agent selection

Config file location:
  ~/.config/katten/config.json


CONVERSATION HISTORY
--------------------
All prompts and responses are automatically logged to an XML file:
  ~/.config/katten/history.xml

Each entry contains:
- timestamp: ISO 8601 format (UTC)
- prompt: Your question
- web_search: "yes" or "no"
- response: The AI's answer

Example:
  <?xml version="1.0" encoding="utf-8"?>
  <history>
    <entry>
      <timestamp>2024-12-20T15:30:45.123456+00:00</timestamp>
      <prompt>What is the capital of France?</prompt>
      <web_search>yes</web_search>
      <response>The capital of France is Paris.</response>
    </entry>
  </history>

To disable logging, delete the history.xml file - it won't be recreated
until you make another query.


CUSTOMIZING KEYWORDS
--------------------
To change the trigger keywords:

1. Run: katten-config

2. Select option 3 for custom keywords

3. Enter your keywords separated by commas:
   Example: ai, ask, chat

4. Restart KRunner:
   kquitapp6 krunner && kstart krunner


CUSTOM ICON
-----------
The plugin comes with a custom SVG icon. To use your own:

1. Create an SVG icon (or 128x128 PNG)
2. Replace the file at:
   ~/.local/share/katten/katten-icon.svg
3. Also copy it to:
   ~/.local/share/icons/hicolor/scalable/apps/katten-icon.svg
4. Update the icon cache:
   gtk-update-icon-cache -f ~/.local/share/icons/hicolor/


TROUBLESHOOTING
---------------

"API key not configured" error:
  Run: krunner-lechat-config
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
  The Mistral API does not have access to your Le Chat web account's
  personal data or conversation history. This is by design for privacy.
  However, you can use custom agents created at console.mistral.ai

API errors (404, 400):
  - Verify your API key is valid at console.mistral.ai
  - Try disabling web search: katten noweb <question>
  - Clear the cached agent: krunner-lechat-config

Responses not formatted:
  - The markdown library is installed in the venv at:
    ~/.local/share/katten/venv/
  - If rendering fails, check /tmp/katten-panel.log for errors
  - Try reinstalling the venv: rm -rf ~/.local/share/katten/venv/
    then run ./install.sh again


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
- mistral-medium-2505 model for web search queries
- mistral-large-latest model for non-web queries

Note: The first time you use web search, the plugin creates a helper
agent in your Mistral account called "Katten WebSearch".


DISCLAIMER
----------
Katten is an unofficial, community-developed plugin.
It is NOT affiliated with, endorsed by, or sponsored by Mistral AI.
"Le Chat" and "Mistral" are trademarks of Mistral AI.

Use of this plugin requires a valid Mistral AI API key and is subject
to Mistral AI's terms of service and usage policies.


LICENSE
-------
MIT License - Feel free to modify and share.

Copyright (c) 2024 Emilio Longoria

#!/usr/bin/python3
"""
Katten - Unofficial Mistral Vibe plugin for KRunner

Copyright 2026 Emilio González Longoria.
Katten is distributed under the terms of the GNU General Public License v3.
See https://www.gnu.org/licenses/gpl-3.0.html for details.

Allows sending prompts to Mistral AI and viewing responses directly in KRunner.
Supports web search and custom agents.

This plugin is not affiliated with Mistral AI or its products.

Version 0.4.1 (Beta):
- Initial public release
- Multiple trigger keywords (katten, lechat, lc, mistral, vibe, mv)
- Preview panel with full markdown support (tables, code blocks)
- Web search enabled by default
- Fallback to simple API when web search fails
- Warning message when fallback is used
- Persistent loading notification
- Opens conversation in default browser
- XML conversation history logging
- Custom SVG icon
- Uses system python3-markdown package (no venv required)
"""

import os
import sys
import json
import signal
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)

# KRunner DBus configuration
OBJPATH = "/katten"
IFACE = "org.kde.krunner1"
SERVICE = "org.kde.katten"

# Configuration file path
CONFIG_DIR = Path.home() / ".config" / "katten"
CONFIG_FILE = CONFIG_DIR / "config.json"
PLUGIN_DIR = Path.home() / ".local" / "share" / "katten"
ICON_PATH = PLUGIN_DIR / "katten-icon.svg"
LOG_FILE = CONFIG_DIR / "history.xml"

# Default trigger keywords
DEFAULT_KEYWORDS = ["katten", "lechat", "lc", "mistral", "vibe", "mv"]

# Default model (used when web search is disabled)
DEFAULT_MODEL = "mistral-medium-latest"

# Model for web search agent
# Updated to use current Mistral model with web search capability
WEB_SEARCH_MODEL = "mistral-medium-latest"

# Maximum characters to show per result line
MAX_LINE_LENGTH = 200

# KWallet constants
KWALLET_SERVICE = "org.kde.kwalletd"
KWALLET_OBJECT_PATH = "/modules/kwalletd"
KWALLET_INTERFACE = "org.kde.KWallet"
KWALLET_NAME = "katten"
KWALLET_KEY = "mistral_api_key"


class KWalletManager:
    """Manage API key storage in KWallet with D-Bus."""
    
    def __init__(self):
        self.bus = None
        self.wallet_open = False
        
    def _get_kwallet_interface(self):
        """Get the KWallet D-Bus interface."""
        if self.bus is None:
            try:
                self.bus = dbus.SessionBus()
            except Exception:
                return None
        
        try:
            kwallet_obj = self.bus.get_object(KWALLET_SERVICE, KWALLET_OBJECT_PATH)
            return dbus.Interface(kwallet_obj, KWALLET_INTERFACE)
        except Exception:
            return None
    
    def is_available(self):
        """Check if KWallet service is available."""
        try:
            # Check if the service is registered on the bus
            bus = dbus.SessionBus()
            bus.get_object(KWALLET_SERVICE, KWALLET_OBJECT_PATH)
            return True
        except Exception:
            return False
    
    def read_api_key(self):
        """Read API key from KWallet. Returns the key or None if not found/error."""
        interface = self._get_kwallet_interface()
        if interface is None:
            return None
        
        try:
            # ReadPassword(wallet, key, w_id)
            password = interface.ReadPassword(KWALLET_NAME, KWALLET_KEY, 0)
            if password and password != b"":
                return password.decode('utf-8') if isinstance(password, bytes) else str(password)
            return None
        except dbus.exceptions.DBusException as e:
            # Entry doesn't exist
            if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                return None
            logging.warning(f"Failed to read from KWallet: {e}")
            return None
        except Exception as e:
            logging.warning(f"Failed to read from KWallet: {e}")
            return None
    
    def write_api_key(self, api_key):
        """Write API key to KWallet. Returns True if successful."""
        interface = self._get_kwallet_interface()
        if interface is None:
            return False
        
        try:
            # Ensure wallet is open
            if not self.wallet_open:
                if not self.open_wallet():
                    return False
            
            # WritePassword(wallet, key, password, w_id)
            interface.WritePassword(KWALLET_NAME, KWALLET_KEY, api_key, 0)
            return True
        except Exception as e:
            logging.warning(f"Failed to write to KWallet: {e}")
            return False
    
    def open_wallet(self):
        """Open the KWallet wallet. Returns True if successful."""
        interface = self._get_kwallet_interface()
        if interface is None:
            return False
        
        try:
            # Open the wallet: wallet_name, w_id (window ID, 0 for CLI), window_title
            interface.Open(KWALLET_NAME, 0, "Katten")
            self.wallet_open = True
            return True
        except dbus.exceptions.DBusException as e:
            # Wallet might already be open
            if "already open" in str(e).lower():
                self.wallet_open = True
                return True
            logging.warning(f"Failed to open KWallet: {e}")
            return False
        except Exception as e:
            logging.warning(f"Failed to open KWallet: {e}")
            return False


def load_config():
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "api_key": os.environ.get("MISTRAL_API_KEY", ""),
        "default_agent_id": None,
        "web_search_enabled": True,
        "websearch_agent_id": None,
        "keywords": DEFAULT_KEYWORDS.copy()
    }


def save_config(config):
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def show_kwallet_fallback_dialog():
    """
    Show a system dialog asking user what to do when KWallet is not available.
    Returns: 'retry', 'config_file', or 'cancel'
    """
    try:
        # Try PyQt6 first
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox
            PYQT_VERSION = 6
        except ImportError:
            # Fall back to PyQt5
            try:
                from PyQt5.QtWidgets import QApplication, QMessageBox
                PYQT_VERSION = 5
            except ImportError:
                # No Qt available, use native tools
                return _show_kwallet_fallback_native()
        
        # Create application if it doesn't exist
        app = QApplication.instance()
        create_new_app = False
        if app is None:
            app = QApplication(sys.argv)
            app.setApplicationName("Katten KWallet Setup")
            create_new_app = True
        
        # Create dialog
        msg_box = QMessageBox()
        msg_box.setWindowTitle("KWallet Not Available")
        msg_box.setText("KWallet service is not available for secure API key storage.")
        msg_box.setInformativeText("How would you like to proceed?")
        
        # Add custom buttons
        retry_btn = msg_box.addButton("Try Again", QMessageBox.ActionRole)
        config_btn = msg_box.addButton("Use Config File", QMessageBox.ActionRole)
        cancel_btn = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        
        msg_box.setDefaultButton(retry_btn)
        msg_box.setEscapeButton(cancel_btn)
        
        # Show dialog and get response
        msg_box.exec()
        
        # Determine which button was clicked
        clicked = msg_box.clickedButton()
        
        # Cleanup if we created the app
        if create_new_app and app is not None:
            app.quit()
        
        if clicked == retry_btn:
            return "retry"
        elif clicked == config_btn:
            return "config_file"
        else:
            return "cancel"
            
    except Exception as e:
        logging.warning(f"Failed to show Qt dialog: {e}")
        return _show_kwallet_fallback_native()


def _show_kwallet_fallback_native():
    """Show fallback dialog using native tools (zenity/kdialog)."""
    import subprocess
    
    # Try zenity (GNOME)
    try:
        result = subprocess.run([
            "zenity", "--list", "--title=KWallet Not Available",
            "--text=KWallet service is not available. How would you like to proceed?",
            "--column=Option", "Try Again", "Use Config File", "Cancel"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            choice = result.stdout.strip()
            if choice == "Try Again":
                return "retry"
            elif choice == "Use Config File":
                return "config_file"
            else:
                return "cancel"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Try kdialog (KDE)
    try:
        result = subprocess.run([
            "kdialog", "--title=KWallet Not Available",
            "--msgbox=KWallet service is not available. How would you like to proceed?",
            "--yesno"
        ], capture_output=True, text=True, timeout=30)
        
        # kdialog is limited for this use case, so fall back to simple text
        return _show_kwallet_fallback_text()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fall back to text-based
    return _show_kwallet_fallback_text()


def _show_kwallet_fallback_text():
    """Show fallback dialog using text input."""
    print("KWallet service is not available for secure API key storage.")
    print("How would you like to proceed?")
    print("1. Try Again")
    print("2. Use Config File")
    print("3. Cancel")
    print("Enter your choice (1-3): ", end="")
    
    try:
        choice = input().strip()
        if choice == "1":
            return "retry"
        elif choice == "2":
            return "config_file"
        else:
            return "cancel"
    except (EOFError, KeyboardInterrupt):
        return "cancel"


def get_keywords():
    """Get trigger keywords from config."""
    config = load_config()
    keywords = config.get("keywords", DEFAULT_KEYWORDS)
    return [kw.lower() for kw in keywords] if keywords else DEFAULT_KEYWORDS


def get_api_key(_retrying=False):
    """Get API key from KWallet, environment, or config file with fallback strategy.
    
    Args:
        _retrying: Internal flag to prevent infinite recursion when retrying
    
    Returns:
        API key string, or empty string if user cancelled
    """
    # Try KWallet first (preferred)
    kwallet = KWalletManager()
    
    # Check if KWallet is available
    if kwallet.is_available():
        api_key = kwallet.read_api_key()
        if api_key:
            return api_key
        # KWallet available but no key stored - fall through to other methods
    else:
        # KWallet not available - show fallback dialog (unless we're already retrying)
        if not _retrying:
            user_choice = show_kwallet_fallback_dialog()
            
            if user_choice == "retry":
                # User wants to try again - give KWallet a moment to start
                import time
                time.sleep(1)  # Brief delay to allow KWallet to start
                return get_api_key(_retrying=True)  # Recursive call with retry flag
            elif user_choice == "cancel":
                # User chose to cancel - return empty to disable Katten
                return ""
            # user_choice == "config_file" - fall through to config file method
    
    # Try environment variable next
    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if api_key:
        return api_key
    
    # Fall back to config file
    config = load_config()
    return config.get("api_key", "")


def save_api_key(api_key, _retrying=False):
    """Save API key to KWallet or config file with fallback strategy.
    
    Args:
        api_key: The API key to save
        _retrying: Internal flag to prevent infinite recursion
    
    Returns:
        True if saved successfully, False otherwise
    """
    kwallet = KWalletManager()
    
    # Try KWallet first (preferred)
    if kwallet.is_available():
        if kwallet.write_api_key(api_key):
            # Also save to config file for backwards compatibility
            # (in case user switches away from KWallet later)
            config = load_config()
            config["api_key"] = api_key
            save_config(config)
            return True
        else:
            # KWallet failed, show fallback dialog (unless already retrying)
            if not _retrying:
                user_choice = show_kwallet_fallback_dialog()
                
                if user_choice == "retry":
                    import time
                    time.sleep(1)
                    return save_api_key(api_key, _retrying=True)  # Retry with flag
                elif user_choice == "cancel":
                    return False  # Don't save
                # user_choice == "config_file" - fall through
    else:
        # KWallet not available, show fallback dialog (unless already retrying)
        if not _retrying:
            user_choice = show_kwallet_fallback_dialog()
            
            if user_choice == "retry":
                import time
                time.sleep(1)
                return save_api_key(api_key, _retrying=True)  # Retry with flag
            elif user_choice == "cancel":
                return False  # Don't save
            # user_choice == "config_file" - fall through
    
    # Save to config file (fallback)
    config = load_config()
    config["api_key"] = api_key
    save_config(config)
    return True


def get_icon():
    """Get the icon path or fallback to a system icon."""
    if ICON_PATH.exists():
        return str(ICON_PATH)
    # Try PNG fallback
    png_path = PLUGIN_DIR / "katten-icon.png"
    if png_path.exists():
        return str(png_path)
    return "accessories-dictionary"


def mistral_request(endpoint, method="GET", data=None):
    """Make a request to the Mistral AI API."""
    api_key = get_api_key()
    if not api_key:
        return None, "API key not configured. Run: katten-config"

    url = f"https://api.mistral.ai/v1/{endpoint}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        req = Request(url, method=method, headers=headers)
        if data:
            req.data = json.dumps(data).encode("utf-8")

        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8")), None
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get("message", error_body)
        except:
            error_msg = error_body
        return None, f"API error ({e.code}): {error_msg}"
    except URLError as e:
        return None, f"Network error: {e.reason}"
    except Exception as e:
        return None, f"Error: {str(e)}"


def list_agents():
    """List agents created via the Mistral API.
    
    NOTE: Agents created in the Vibe web UI (chat.mistral.ai) are NOT
    accessible through the API — they live in a separate system.
    Only agents created programmatically via POST /v1/agents are returned here.
    """
    result, error = mistral_request("agents")
    if error:
        return [], error
    # API returns a flat array
    if isinstance(result, list):
        return result, None
    # Defensive: handle {"data": [...]} shape if it ever changes
    if isinstance(result, dict):
        return result.get("data", []), None
    return [], None


def get_or_create_websearch_agent():
    """Get or create a web search agent for Vibe queries."""
    config = load_config()
    
    # Check if we have a cached agent
    cached_id = config.get("websearch_agent_id")
    if cached_id:
        # Verify it still exists
        result, error = mistral_request(f"agents/{cached_id}")
        if not error and result:
            return cached_id, None
        else:
            # Agent doesn't exist or failed verification - clear the cache and log it
            import logging
            logging.warning(f"Cached web search agent {cached_id} failed verification: {error}")
            config["websearch_agent_id"] = None
            save_config(config)
    
    # Create a new web search agent using the agents endpoint
    agent_data = {
        "model": WEB_SEARCH_MODEL,
        "name": "Katten WebSearch",
        "description": "Agent for Katten KRunner plugin with web search capability",
        "instructions": (
            "You are a helpful assistant who provides information to a user who is sending a query via a KRunner plugin. "
            "Perform web searches when necessary to provide current and accurate information. "
            "The user does not have the ability to answer back to you, so do not ask questions. "
            "If you need more information, context or clarification from the user, you may describe what they need to include in a new prompt - "
            "but do that as a last resort to avoid burdening the user with making a new attempt. "
            "Whenever the user sends a prompt, it is sent to a new model without context of the user. "
            "Therefore, your answers must be concise and informative - not conversational. "
            "One prompt - one answer. So make the answer count! "
            "Your answer will be displayed on a panel with support for markdown formatting."
        ),
        "tools": [{"type": "web_search"}],
        "completion_args": {
            "temperature": 0.3,
            "top_p": 0.95
        }
    }
    
    result, error = mistral_request("agents", method="POST", data=agent_data)
    if error:
        import logging
        logging.warning(f"Failed to create web search agent: {error}")
        return None, error
    
    agent_id = result.get("id")
    if agent_id:
        config["websearch_agent_id"] = agent_id
        save_config(config)
        return agent_id, None
    
    import logging
    logging.warning("Web search agent creation returned no ID")
    return None, "Failed to create web search agent"


def send_prompt_with_agent(prompt, agent_id):
    """Send a prompt using the agents/completions API."""
    data = {
        "agent_id": agent_id,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    result, error = mistral_request("agents/completions", method="POST", data=data)
    if error:
        return None, error
    
    try:
        choices = result.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if content:
                return content, None
        return "No response received.", None
    except (KeyError, IndexError, TypeError) as e:
        return None, f"Failed to parse response: {e}"


def send_prompt_with_conversation(prompt, agent_id):
    """Send a prompt using the conversations API (supports web search).
    Returns: (response_text, error, conversation_id)
    """
    data = {
        "agent_id": agent_id,
        "inputs": prompt
    }
    
    result, error = mistral_request("conversations", method="POST", data=data)
    if error:
        return None, error, None
    
    try:
        # Extract conversation ID for opening in browser
        conversation_id = result.get("conversation_id") or result.get("id")
        
        outputs = result.get("outputs", [])
        if outputs:
            for output in outputs:
                if output.get("type") == "message.output":
                    content = output.get("content", "")
                    if isinstance(content, str):
                        return content, None, conversation_id
                    elif isinstance(content, list):
                        text_parts = []
                        for chunk in content:
                            if isinstance(chunk, dict) and chunk.get("type") == "text":
                                text_parts.append(chunk.get("text", ""))
                            elif isinstance(chunk, str):
                                text_parts.append(chunk)
                        if text_parts:
                            return "\n".join(text_parts), None, conversation_id
        return "No response received.", None, conversation_id
    except (KeyError, IndexError, TypeError) as e:
        return None, f"Failed to parse response: {e}", None


def send_prompt_simple(prompt):
    """Send a prompt using the regular Chat Completions API (no web search)."""
    data = {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    result, error = mistral_request("chat/completions", method="POST", data=data)
    if error:
        return None, error

    try:
        choices = result.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if content:
                return content, None
        return "No response received.", None
    except (KeyError, IndexError, TypeError) as e:
        return None, f"Failed to parse response: {e}"


def send_prompt(prompt, agent_id=None, use_web_search=True):
    """Send a prompt to Mistral AI.
    Returns: (response_text, error, conversation_url, fallback_used)
    """
    fallback_used = False
    config = load_config()
    
    # If user has a specific agent set, use that
    if agent_id:
        response, error = send_prompt_with_agent(prompt, agent_id)
        return response, error, None, fallback_used
    
    if config.get("default_agent_id"):
        response, error = send_prompt_with_agent(prompt, config["default_agent_id"])
        return response, error, None, fallback_used
    
    # Use web search if enabled
    if use_web_search and config.get("web_search_enabled", True):
        ws_agent_id, error = get_or_create_websearch_agent()
        if error:
            # Fall back to simple prompt if web search agent fails
            import logging
            logging.warning(f"Web search agent creation failed, falling back to simple API: {error}")
            response, error = send_prompt_simple(prompt)
            fallback_used = True
            return response, error, None, fallback_used
        response, error, conv_id = send_prompt_with_conversation(prompt, ws_agent_id)
        # The conversation ID belongs to the API account, not the Vibe web
        # account, so we can't deep-link to it. Always open the Vibe home.
        conv_url = "https://chat.mistral.ai/"
        
        # Check if web search returned an apology/fallback message
        # If so, retry with simple chat API (non-web search model)
        if response and not error:
            apology_phrases = [
                "I'm sorry", "sorry, but", "couldn't retrieve", 
                "couldn't find", "unable to", "failed to"
            ]
            if any(phrase.lower() in response.lower() for phrase in apology_phrases):
                # Log the web search failure to a debug file
                try:
                    with open("/tmp/katten-debug.log", "a") as f:
                        f.write(f"[{datetime.now()}] Web search failed for: '{prompt}'\n")
                        f.write(f"Response: '{response[:200]}'\n")
                        f.write(f"Falling back to simple API\n\n")
                except Exception:
                    pass
                # Web search failed to get useful results, fall back to simple API
                response, error = send_prompt_simple(prompt)
                fallback_used = True
                if error:
                    # If simple also fails, return the web search response with error note
                    return response, error, conv_url, fallback_used
                return response, error, None, fallback_used
        
        return response, error, conv_url, fallback_used
    
    response, error = send_prompt_simple(prompt)
    return response, error, None, fallback_used


def open_browser_url(url: str, browser_name: str = None) -> tuple:
    """
    Open a URL in the specified browser or the default browser.
    
    Args:
        url: The URL to open
        browser_name: Browser keyword (ff/firefox, ch/chrome, ed/edge, fk/falkon, 
                      kq/kon/konqueror, ug/uc/ung/uch/ungoogled/ungoogledchromium)
                      If None, uses xdg-open (default browser)
    
    Returns:
        (success: bool, error_message: str or None)
    """
    try:
        if browser_name is None:
            # Use default browser via xdg-open
            result = subprocess.run(
                ["xdg-open", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if result.returncode == 0:
                return True, None
            else:
                return False, "Failed to open browser"
        
        # Map browser keywords to executable names
        browser_map = {
            "ff": "firefox", "firefox": "firefox",
            "ch": "google-chrome", "chrome": "google-chrome",
            "ed": "microsoft-edge", "edge": "microsoft-edge",
            "fk": "falkon", "falkon": "falkon",
            "kq": "konqueror", "kon": "konqueror", "konqueror": "konqueror",
            "ug": "ungoogled-chromium", "uc": "ungoogled-chromium",
            "ung": "ungoogled-chromium", "uch": "ungoogled-chromium",
            "ungoogled": "ungoogled-chromium", "ungoogledchromium": "ungoogled-chromium",
        }
        
        browser_exec = browser_map.get(browser_name.lower())
        if not browser_exec:
            return False, f"Unknown browser: {browser_name}"
        
        # Try to find and launch the browser
        result = subprocess.run(
            [browser_exec, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        
        if result.returncode == 0:
            return True, None
        else:
            return False, f"Failed to launch {browser_exec}"
    
    except FileNotFoundError:
        return False, f"Browser not found: {browser_name or 'default browser'}"
    except subprocess.TimeoutExpired:
        # Browser may still open even if timeout occurs
        return True, None
    except Exception as e:
        return False, str(e)


def log_conversation(prompt: str, response: str, web_search: bool):
    """
    Log a conversation to the XML history file.
    Format:
    <history>
      <entry>
        <timestamp>ISO 8601</timestamp>
        <prompt>user prompt</prompt>
        <web_search>yes|no</web_search>
        <response>Vibe's answer</response>
      </entry>
      ...
    </history>
    """
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing history or create new
        if LOG_FILE.exists():
            try:
                tree = ET.parse(LOG_FILE)
                root = tree.getroot()
            except ET.ParseError:
                root = ET.Element("history")
        else:
            root = ET.Element("history")
        
        # Create new entry
        entry = ET.SubElement(root, "entry")
        
        ts = ET.SubElement(entry, "timestamp")
        ts.text = datetime.now(timezone.utc).isoformat()
        
        p = ET.SubElement(entry, "prompt")
        p.text = prompt
        
        ws = ET.SubElement(entry, "web_search")
        ws.text = "yes" if web_search else "no"
        
        r = ET.SubElement(entry, "response")
        r.text = response
        
        # Write back
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        with open(LOG_FILE, "wb") as f:
            tree.write(f, encoding="utf-8", xml_declaration=True)
    except Exception:
        pass  # Silently fail - logging should never break the main functionality


def split_response_into_lines(text, max_length=MAX_LINE_LENGTH):
    """Split a long response into multiple displayable lines."""
    text = " ".join(text.split())
    
    lines = []
    words = text.split(" ")
    current_line = ""
    
    for word in words:
        if len(current_line) + len(word) + 1 <= max_length:
            current_line = f"{current_line} {word}".strip()
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    return lines if lines else ["(empty response)"]


def _notify(title, body, icon="", timeout=0, notif_id=0, hints=None):
    """
    Send a desktop notification via org.freedesktop.Notifications.
    Returns the notification ID assigned by the server.
    timeout=0 means persistent (never auto-closes).
    Pass notif_id != 0 to replace/close an existing notification.
    """
    try:
        bus    = dbus.SessionBus()
        proxy  = bus.get_object("org.freedesktop.Notifications",
                                "/org/freedesktop/Notifications")
        iface  = dbus.Interface(proxy, "org.freedesktop.Notifications")
        h = dbus.Dictionary(hints or {}, signature="sv")
        nid = iface.Notify(
            "Katten",                # app name
            dbus.UInt32(notif_id),   # replaces_id (0 = new)
            icon or get_icon(),      # icon
            title,                   # summary
            body,                    # body
            dbus.Array([], "s"),     # actions
            h,                       # hints
            dbus.Int32(timeout),     # timeout ms (0 = persistent)
        )
        return int(nid)
    except Exception:
        return 0


def _close_notification(nid: int):
    """Close a notification by its ID."""
    if not nid:
        return
    try:
        bus   = dbus.SessionBus()
        proxy = bus.get_object("org.freedesktop.Notifications",
                               "/org/freedesktop/Notifications")
        iface = dbus.Interface(proxy, "org.freedesktop.Notifications")
        iface.CloseNotification(dbus.UInt32(nid))
    except Exception:
        pass


def show_loading_notification(prompt: str) -> int:
    """
    Show a persistent notification while Katten is generating an answer.
    Returns the notification ID so it can be closed later.
    
    Note: KDE Plasma's x-kde-progress hint only works for taskbar progress,
    not for notification progress bars. The notification shows a simple
    loading message that stays visible until dismissed.
    """
    hints = {
        # Keep alive until explicitly closed
        "resident":  dbus.Boolean(True),
        "transient": dbus.Boolean(False),
        "urgency":   dbus.Byte(1),  # normal urgency
    }
    return _notify(
        title   = "Katten",
        body    = "Generating answer... please wait",
        hints   = hints,
        timeout = 0,  # persistent until we close it
    )


def show_preview_panel(title, content, prompt="", conversation_url="", fallback_used=False):
    """
    Launch the preview panel with the ready answer.

    The content is written to a temp file and its path passed to the panel
    rather than being put on the command line.  This avoids argument-length
    limits and shell-quoting issues that silently swallow the response text.
    
    Args:
        fallback_used: True if web search failed and we fell back to simple API
    """
    panel_script = PLUGIN_DIR / "quicklook_panel.py"

    if not panel_script.exists():
        try:
            subprocess.Popen(
                ["kdialog", "--title", title, "--msgbox", content],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass
        return None

    # Write content + metadata to a temp file
    try:
        import tempfile
        fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="katten_resp_")
        os.close(fd)
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump({
                "title":   title,
                "content": content,
                "prompt":  prompt,
                "url":     conversation_url or "https://chat.mistral.ai/",
                "fallback_used": fallback_used,
            }, fh)
    except Exception as exc:
        # Fallback: try kdialog with plain text
        try:
            subprocess.Popen(
                ["kdialog", "--title", title, "--msgbox", content[:4000]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass
        return None

    # Log file — same one quicklook_panel.py uses so all errors are together
    log_path = Path("/tmp") / "katten-panel.log"
    try:
        log_fh = open(log_path, "a")
    except Exception:
        log_fh = subprocess.DEVNULL

    try:
        # Use system Python with system-wide python3-markdown package
        return subprocess.Popen(
            [
                sys.executable, str(panel_script),
                "--response-file", tmp_path,
            ],
            stdout=log_fh,
            stderr=log_fh,
        )
    except Exception as exc:
        # Write the launch error to the log before falling back
        try:
            with open(log_path, "a") as f:
                f.write(f"[katten.py] failed to launch panel: {exc}\n")
        except Exception:
            pass
        try:
            subprocess.Popen(
                ["kdialog", "--title", title, "--msgbox", content[:4000]],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass
        return None


class Runner(dbus.service.Object):
    """KRunner DBus service for Katten (Mistral AI) integration."""

    def __init__(self):
        dbus.service.Object.__init__(
            self,
            dbus.service.BusName(SERVICE, dbus.SessionBus()),
            OBJPATH
        )
        self.last_response = None
        self.last_prompt = None
        self.last_conversation_url = "https://chat.mistral.ai/"
        self.last_fallback_used = False

    def _matches_keyword(self, query):
        """Check if query starts with any configured keyword."""
        query_lower = query.lower()
        for keyword in get_keywords():
            if query_lower.startswith(keyword + " "):
                return keyword, query[len(keyword) + 1:].strip()
        return None, None

    @dbus.service.method(IFACE, in_signature='s', out_signature='a(sssida{sv})')
    def Match(self, query: str):
        """Match method called by KRunner when user types."""
        query = query.strip()
        icon = get_icon()

        # Check for any trigger keyword
        keyword, prompt = self._matches_keyword(query)
        if keyword is None:
            return []

        if not prompt:
            keywords = ", ".join(get_keywords())
            return [(
                "help",
                "Katten - Type your question",
                icon,
                100,
                1.0,
                {"subtext": dbus.String(f"Keywords: {keywords}. Example: katten What is AI?", variant_level=1)}
            )]

        # Check for special commands
        if prompt.lower() == "agents":
            return self._list_agents_matches(icon)

        if prompt.lower().startswith("use agent "):
            agent_name = prompt[10:].strip()
            return self._set_agent_matches(agent_name, icon)

        if prompt.lower() == "clear agent":
            config = load_config()
            config["default_agent_id"] = None
            save_config(config)
            return [(
                "cleared",
                "Agent cleared - using default model",
                icon,
                100,
                1.0,
                {"subtext": dbus.String(f"Now using {DEFAULT_MODEL} with web search", variant_level=1)}
            )]

        # Handle "open" command - open Vibe in browser
        if prompt.lower() == "open":
            success, error = open_browser_url("https://chat.mistral.ai/chat")
            if success:
                return [(
                    "open_browser",
                    "Opening Vibe in default browser",
                    icon,
                    100,
                    1.0,
                    {"subtext": dbus.String("https://chat.mistral.ai/chat", variant_level=1)}
                )]
            else:
                return [(
                    "open_error",
                    f"Error opening browser: {error}",
                    icon,
                    100,
                    1.0,
                    {"subtext": dbus.String("Try specifying a browser: katten open firefox", variant_level=1)}
                )]

        # Handle "open <browser>" command
        if prompt.lower().startswith("open "):
            browser_arg = prompt[5:].strip().lower()
            success, error = open_browser_url("https://chat.mistral.ai/chat", browser_arg)
            if success:
                return [(
                    "open_browser",
                    f"Opening Vibe in {browser_arg}",
                    icon,
                    100,
                    1.0,
                    {"subtext": dbus.String("https://chat.mistral.ai/chat", variant_level=1)}
                )]
            else:
                return [(
                    "open_error",
                    f"Error: {error}",
                    icon,
                    100,
                    1.0,
                    {"subtext": dbus.String("Supported: firefox, chrome, edge, falkon, konqueror, ungoogled-chromium", variant_level=1)}
                )]

        if prompt.lower() == "show":
            if self.last_response:
                return self._response_matches(self.last_response, self.last_prompt, icon)
            return [(
                "no_response",
                "No previous response to show",
                icon,
                100,
                1.0,
                {"subtext": dbus.String("Ask a question first", variant_level=1)}
            )]

        # Web search modifiers
        if prompt.lower().startswith("web "):
            actual_prompt = prompt[4:].strip()
            return self._query_matches(actual_prompt, icon, force_web=True)

        if prompt.lower().startswith("noweb "):
            actual_prompt = prompt[6:].strip()
            return self._query_matches(actual_prompt, icon, force_web=False)

        return self._query_matches(prompt, icon)

    def _response_matches(self, response, prompt, icon):
        """Create match items from a response."""
        lines = split_response_into_lines(response)
        matches = []
        
        header = f"Katten: {prompt[:40]}{'...' if len(prompt) > 40 else ''}"
        matches.append((
            json.dumps({"action": "show_panel", "text": response, "prompt": prompt}),
            header,
            icon,
            100,
            1.0,
            {"subtext": dbus.String(lines[0], variant_level=1)}
        ))
        
        for i, line in enumerate(lines[1:10], start=2):
            matches.append((
                json.dumps({"action": "show_panel", "text": response, "prompt": prompt}),
                f"[{i}/{len(lines)}] {line}",
                icon,
                100,
                0.9 - (i * 0.01),
                {"subtext": dbus.String("Press Enter to open response panel", variant_level=1)}
            ))
        
        if len(lines) > 10:
            matches.append((
                json.dumps({"action": "show_panel", "text": response, "prompt": prompt}),
                f"... {len(lines) - 10} more lines",
                icon,
                100,
                0.5,
                {"subtext": dbus.String("Press Enter to open full response", variant_level=1)}
            ))
        
        return matches

    def _query_matches(self, prompt, icon, force_web=None):
        """Generate matches for a chat prompt."""
        config = load_config()
        
        api_key = get_api_key()
        if not api_key:
            # Launch first-run panel as a separate process
            self._launch_first_run_panel()
            # Return a loading state
            return [(
                "first_run",
                "Katten - Setup Required",
                icon,
                100,
                1.0,
                {"subtext": dbus.String("Please enter your API key in the configuration panel", variant_level=1)}
            )]

        use_web = force_web if force_web is not None else config.get("web_search_enabled", True)
        
        agent_info = " (agent)" if config.get("default_agent_id") else ""
        web_info = " +web" if use_web else ""

        return [(
            json.dumps({"prompt": prompt, "web": use_web}),
            f"Ask Katten: {prompt[:60]}{'...' if len(prompt) > 60 else ''}",
            icon,
            100,
            1.0,
            {"subtext": dbus.String(f"Press Enter to send{agent_info}{web_info}", variant_level=1)}
        )]

    def _list_agents_matches(self, icon):
        """List agents created via the Mistral API."""
        agents, error = list_agents()
        if error:
            return [(
                "error",
                "Failed to list agents",
                "dialog-error",
                100,
                1.0,
                {"subtext": dbus.String(str(error)[:200], variant_level=1)}
            )]

        if not agents:
            return [(
                "no_agents",
                "No API-created agents found",
                icon,
                100,
                1.0,
                {
                    "subtext": dbus.String(
                        "Note: agents made on chat.mistral.ai are not accessible via the API. "
                        "Create agents via the Mistral API or console.mistral.ai.",
                        variant_level=1
                    )
                }
            )]

        matches = []
        for agent in agents[:10]:
            name = agent.get("name", "Unnamed")
            agent_id = agent.get("id", "")
            description = agent.get("description", "No description")[:80]
            matches.append((
                json.dumps({"action": "select_agent", "id": agent_id, "name": name}),
                f"Agent: {name}",
                "user-identity",
                100,
                0.9,
                {"subtext": dbus.String(description, variant_level=1)}
            ))

        return matches

    def _set_agent_matches(self, agent_name, icon):
        """Find and set an agent by name."""
        agents, error = list_agents()
        if error:
            return [(
                "error",
                "Failed to search agents",
                "dialog-error",
                100,
                1.0,
                {"subtext": dbus.String(str(error)[:200], variant_level=1)}
            )]

        matches = []
        agent_name_lower = agent_name.lower()
        for agent in agents:
            name = agent.get("name", "")
            if agent_name_lower in name.lower():
                agent_id = agent.get("id", "")
                description = agent.get("description", "No description")[:60]
                matches.append((
                    json.dumps({"action": "select_agent", "id": agent_id, "name": name}),
                    f"Use agent: {name}",
                    "user-identity",
                    100,
                    0.9,
                    {"subtext": dbus.String(f"Set as default. {description}", variant_level=1)}
                ))

        if not matches:
            return [(
                "not_found",
                f"No agent matching '{agent_name}'",
                "dialog-warning",
                100,
                1.0,
                {"subtext": dbus.String("Type 'lechat agents' to see all agents", variant_level=1)}
            )]

        return matches

    @dbus.service.method(IFACE, out_signature='a(sss)')
    def Actions(self):
        """Return available actions for matches."""
        return [
            ("panel", "Open Response Panel", "view-preview"),
            ("copy", "Copy to Clipboard", "edit-copy"),
        ]

    @dbus.service.method(IFACE, in_signature='ss')
    def Run(self, data: str, action_id: str):
        """Execute when user selects a match."""
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            if data in ("help", "no_key", "cleared", "no_agents", "not_found", "error", "no_response", "open_browser", "open_error"):
                # Special handling for open_browser/open_error to trigger browser opening
                if data == "open_browser":
                    # Browser was already opened during Match() call
                    return
                return
            parsed = {"prompt": data}

        # Handle open browser actions
        if data == "open_browser" or parsed.get("action") == "open_browser":
            # Browser was already opened in Match() call - nothing to do here
            return

        # Handle show panel action — use stored last_response so we don't
        # re-embed the full text inside a JSON action_id string (arg-length risk)
        if parsed.get("action") == "show_panel":
            text   = self.last_response or parsed.get("text", "")
            prompt = self.last_prompt   or parsed.get("prompt", "")
            url    = self.last_conversation_url
            show_preview_panel(f"Katten: {prompt[:50]}", text, prompt, url, 
                               fallback_used=self.last_fallback_used)
            return

        # Handle copy action
        if parsed.get("action") == "copy" or action_id == "copy":
            text = parsed.get("text", "")
            self._copy_to_clipboard(text)
            self._show_notification("Copied", "Response copied to clipboard")
            return

        # Handle agent selection
        if parsed.get("action") == "select_agent":
            config = load_config()
            config["default_agent_id"] = parsed.get("id")
            save_config(config)
            self._show_notification(
                "Agent Selected",
                f"Now using: {parsed.get('name', 'Unknown')}"
            )
            return

        # Handle chat prompt
        prompt = parsed.get("prompt")
        if prompt:
            use_web    = parsed.get("web", True)
            panel_title = f"Katten: {prompt[:50]}"

            # Show persistent notification with indeterminate progress bar
            nid = show_loading_notification(prompt)

            try:
                # Fetch the response (blocks until done)
                response, error, conversation_url, fallback_used = send_prompt(prompt, use_web_search=use_web)
            finally:
                # Always dismiss the loading notification, even if send_prompt raises an exception
                _close_notification(nid)

            if error:
                _notify("Katten - Error", str(error)[:200],
                        icon="dialog-error", timeout=8000)
            else:
                self.last_response         = response
                self.last_prompt           = prompt
                self.last_conversation_url = conversation_url or "https://chat.mistral.ai/"
                self.last_fallback_used    = fallback_used

                # Log to XML history
                log_conversation(prompt, response, use_web)

                show_preview_panel(
                    panel_title,
                    response,
                    prompt,
                    self.last_conversation_url,
                    fallback_used=self.last_fallback_used,
                )

    def _launch_first_run_panel(self):
        """Launch the first-run configuration panel as a separate process."""
        try:
            # Try to launch the first-run panel script
            panel_script = PLUGIN_DIR / "first_run_panel.py"
            if panel_script.exists():
                subprocess.Popen(
                    [sys.executable, str(panel_script)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                # Fallback: try to find it in the script directory
                script_dir = Path(__file__).parent
                fallback_script = script_dir / "first_run_panel.py"
                if fallback_script.exists():
                    subprocess.Popen(
                        [sys.executable, str(fallback_script)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
        except Exception as e:
            # Log the error but don't block the plugin
            import logging
            logging.getLogger("katten").error(f"Failed to launch first-run panel: {e}")

    def _copy_to_clipboard(self, text):
        """Copy text to clipboard using xclip or wl-copy."""
        try:
            proc = subprocess.run(
                ["wl-copy", text],
                capture_output=True,
                timeout=5
            )
            if proc.returncode == 0:
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        try:
            proc = subprocess.run(
                ["xclip", "-selection", "clipboard"],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=5
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    def _show_notification(self, title, message, timeout=3000, critical=False):
        """Show a desktop notification."""
        try:
            bus = dbus.SessionBus()
            notify = bus.get_object(
                "org.freedesktop.Notifications",
                "/org/freedesktop/Notifications"
            )
            iface = dbus.Interface(notify, "org.freedesktop.Notifications")
            
            hints = {
                "urgency": dbus.Byte(2 if critical else 1),
            }
            
            icon_path = get_icon()
            
            iface.Notify(
                "Vibe",
                0,
                icon_path,
                title,
                message,
                [],
                hints,
                timeout
            )
        except Exception:
            try:
                urgency = "critical" if critical else "normal"
                timeout_arg = ["-t", str(timeout)] if timeout > 0 else []
                subprocess.Popen(
                    ["notify-send", "-u", urgency, "-a", "Vibe"] + timeout_arg + [title, message],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except FileNotFoundError:
                pass


def main():
    """Main entry point."""
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    try:
        runner = Runner()
        loop = GLib.MainLoop()
        loop.run()
    except Exception as e:
        print(f"Failed to start Vibe KRunner plugin: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

# Katten

**Katten** is an unofficial, Qt-native desktop client for [Mistral AI](https://mistral.ai)'s
**Vibe**, built specifically for **KDE Plasma 6**. It lets you chat with Vibe in a native
window — no browser required — with full multi-turn conversations and rich-text answers.

Katten is **not affiliated with, endorsed by, or sponsored by Mistral AI**.
"Mistral" and "Vibe" are trademarks of Mistral AI.

> Version 0.5 rebuilt the project from scratch as a real KDE application. Earlier versions
> (0.4.x) were a Python-based KRunner D-Bus plugin with a separately spawned preview panel;
> the known issues of that approach (multiple panel instances, theme typography not being
> picked up, plain-text API key storage, one-prompt-one-answer) are resolved by the new
> architecture: a single-instance Kirigami application, KWallet for secrets, and the
> Mistral Conversations API for real conversations.

## Features

- **Fully Qt-native and Plasma-integrated**: a Kirigami application whose colours, fonts,
  icons and controls come entirely from your Plasma theme and settings (Breeze or custom).
- **Works out of the box**: install the package and run it. Only Qt 6 and KDE Frameworks 6
  libraries that ship with a standard Plasma 6 desktop are required — no Python, no extra
  interpreters, no pip packages.
- **Real conversations**: messages are appended to a server-side conversation
  (`POST /v1/conversations/{id}/messages`), so Vibe sees the full context of the chat.
  Conversations are also stored locally (owner-only permissions) and listed in the sidebar.
- **Rich-text answers**: a built-in Markdown renderer (no external library) displays
  headings, **bold**, *italic*, `code`, fenced code blocks, nested lists, blockquotes,
  pipe tables, [hyperlinks](https://mistral.ai) and ` ```chart ` blocks rendered as SVG
  bar/line charts (via QtSvg, rasterised locally).
- **Web search**: optional, using Mistral's built-in `web_search` tool (enabled per
  conversation at creation).
- **Secure credential storage**: your Mistral API key is stored in **KWallet**
  (folder `Katten`, key `mistral-api-key`) and is never written to a plain-text file.
  The `MISTRAL_API_KEY` environment variable is honoured as a fallback.
- **KRunner integration**: an optional, separately packaged plugin (`katten-krunner`)
  lets you type `katten <prompt>` in KRunner (Alt+Space); the prompt is handed to the
  Katten window over D-Bus, starting the app via D-Bus activation if needed. The main
  application works perfectly without the plugin installed.
- **Languages**: British English (`en_GB`) and Danish (`da`).

## Requirements

- KDE Plasma 6 (Qt 6.6+, KDE Frameworks 6.0+); e.g. Kubuntu 24.10+, KDE neon, Fedora KDE, openSUSE Tumbleweed
- `kwallet` (ships with Plasma) for API key storage
- A Mistral API key from <https://console.mistral.ai> (API keys). There is no official
  keyless API for Vibe's web chat, so a key is required; it is stored in KWallet.

Build-time dependencies (not needed at runtime beyond what Plasma ships):
`cmake`, `extra-cmake-modules`, Qt 6 dev packages (`qt6-base-dev`, `qt6-declarative-dev`,
`qt6-svg-dev`), and KF6 dev packages (`libkf6coreaddons-dev`, `libkf6i18n-dev`,
`libkf6config-dev`, `libkf6wallet-dev`, `libkf6dbusaddons-dev`, `libkf6iconthemes-dev`,
`libkirigami-dev`, plus `libkf6runner-dev` for the KRunner plugin).

## Building

```sh
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build
sudo cmake --install build        # or: cmake --install build --prefix ~/.local
```

Build the KRunner plugin separately (optional):

```sh
cmake -B build -S . -DKATTEN_BUILD_KRUNNER_PLUGIN=ON
```

Run the unit tests:

```sh
cmake -B build -S . -DBUILD_TESTING=ON
cmake --build build
ctest --test-dir build
```

## Installing

### Debian/Ubuntu package

The `debian/` directory builds two packages:

- `katten` — the application
- `katten-krunner` — the optional KRunner plugin (depends on `katten`)

```sh
dpkg-buildpackage -us -uc -b     # or: debuild -us -uc -b
sudo apt install ./katten_*.deb ./katten-krunner_*.deb
```

Alternatively, use CPack to produce a release source tarball:

```sh
cmake -B build -S . && cmake --build build
cpack --config build/CPackConfig.cmake            # writes katten-0.5.0.tar.gz
```

### From source

```sh
cmake -B build -S . -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build
sudo cmake --install build
```

After installing, register the icon cache if needed (`kbuildsycoca6` is run automatically
by the package) and start **Katten** from the application launcher.

## Usage

1. On first start, open **Settings** (sidebar) and paste your Mistral API key. It is saved
   to KWallet — you will only be asked for the wallet password once per session (or never,
   with kwallet-pam).
2. Type a question in the input field and press **Enter** (Shift+Enter for a new line).
3. Continue the conversation: every message is appended to the same server-side
   conversation, and the whole chat is shown and stored locally.
4. Use the sidebar to switch between conversations or start a new one.

### From KRunner

With the `katten-krunner` package installed, open KRunner (Alt+Space) and type:

```
katten What is the capital of Denmark?
```

(also `lechat`, `lc`, `mistral`, `vibe`). Press Enter: Katten opens (or is raised) with a
new conversation containing your prompt, which is sent immediately. Trigger keywords can
be customised with the `keywords` entry (comma-separated) in the `[Runners][katten]`
group of `krunnerrc`.

### Command line

```
katten                    # open/raise the window
katten --prompt "..."     # open a new conversation with this prompt (also via D-Bus)
katten "..."              # same as --prompt
```

## Configuration

| What | Where |
| --- | --- |
| API key | KWallet, folder `Katten` (never plain text); `MISTRAL_API_KEY` env var as fallback |
| Model, web search default | `~/.config/kattenrc`, group `[General]` |
| Conversations | `~/.local/share/katten/conversations/*.json` (mode 0600) |
| KRunner keywords | `~/.config/krunnerrc`, group `[Runners][katten]`, key `keywords` |

## How it talks to Mistral

Katten uses the public Mistral API (`https://api.mistral.ai/v1`) with your API key:

- `POST /v1/conversations` — create a conversation (optionally with the built-in
  `web_search` tool) and get the first answer; returns `conversation_id`
- `POST /v1/conversations/{id}/messages` — append a message to an existing conversation
  (this is what makes multi-turn chats possible)
- `GET /v1/models` — list available models for the settings dialog

Responses are parsed from the `outputs` array (`message.output` entries, text chunks).
Using the API may incur costs depending on your plan; see <https://console.mistral.ai>.

## Development

- `src/` — C++ core (API client, KWallet store, conversation store/models, markdown
  renderer, D-Bus interface) and the Kirigami QML interface in `src/qml/`
- `krunner/` — the KRunner plugin (separate package component)
- `tests/` — QtTest-based unit tests for the markdown renderer and the conversation store
- `po/` — translations (`Messages.sh` regenerates the pot file)

## License

GPL-3.0-or-later — see [LICENSE](LICENSE). Copyright 2026 Emilio González Longoria.

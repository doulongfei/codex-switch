# codex-switch

[![macOS](https://img.shields.io/badge/platform-macOS-black)](https://www.apple.com/macos/)
[![Ubuntu](https://img.shields.io/badge/platform-Ubuntu-E95420)](https://ubuntu.com/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A lightweight switcher for Codex's native authentication modes: **ChatGPT OAuth subscription** and the **official OpenAI Platform API key**. Supports macOS and Ubuntu. No custom model provider, proxy, or gateway; `config.toml` is left untouched, and the tool never runs `codex logout`.

## One-line install (automatic initialization)

Run on macOS or Ubuntu:

```bash
curl -fsSL https://raw.githubusercontent.com/doulongfei/codex-switch/main/install.sh | bash
```

The installer automatically:

1. Checks the OS and Python 3.8+.
2. Downloads the CLI and verifies its SHA-256 checksum.
3. Installs to `~/.local/bin/codex-switch` (`CODEX_SWITCH_INSTALL_DIR` can override this).
4. Checks the Codex credential storage mode and only accepts `File`.
5. Inspects the existing `~/.codex/auth.json` for native ChatGPT OAuth or API-key credentials.
6. Safely imports the existing credentials into `~/.codex/codex-switch/` and atomically replaces `auth.json` with a relative symlink.

An existing ChatGPT OAuth login is reused; no re-login is required. An existing API-key login is imported and remains active. If `auth.json` does not exist, the CLI is installed without creating a dangling symlink. Unsupported auth types, non-`File` storage modes, or detected auth environment-variable overrides stop the credential migration without overwriting the original credentials.

If `~/.local/bin` is not on `PATH`, the installer prints the shell configuration line to add. Reopen the terminal or use `~/.local/bin/codex-switch` directly.

## Quick start

Configure your official OpenAI API key once:

```bash
codex-switch setup-api
```

Then switch modes:

```bash
# OpenAI Platform API key (usage-based billing)
codex-switch api

# ChatGPT OAuth subscription
codex-switch sub

# Show current mode and credential availability
codex-switch status
```

`setup-api` invokes the native `codex login --with-api-key` command inside an isolated temporary `CODEX_HOME`, validates the resulting native `auth.json`, and then stores it as `auth-api.json`. The Codex CLI must be installed. The key is read through a hidden prompt; it is not passed as a command-line argument or written to shell history. If OAuth is currently active, configuring the API key does not switch modes or overwrite OAuth.

## Commands

| Command | Description |
|---|---|
| `codex-switch api` | Switch to the official OpenAI API key |
| `codex-switch sub` | Switch to ChatGPT OAuth subscription |
| `codex-switch setup-api` | Configure or update the official OpenAI API key |
| `codex-switch status` | Show active auth mode, symlink target, and credential availability |
| `codex-switch uninstall` | Materialize the active credential as a regular `auth.json`; keep credential data |
| `codex-switch --version` | Show version |

The installer's internal `_install` command is not intended for manual use.

## How it works

The tool manages Codex's native authentication files, not model providers:

```text
~/.codex/
├── config.toml                         # never modified
├── auth.json -> codex-switch/auth-subscription.json
└── codex-switch/
    ├── auth-subscription.json          # ChatGPT OAuth
    ├── auth-api.json                   # OpenAI API key
    ├── auth.json.codex-switch.bak      # original credential backup from first migration
    ├── state.json                      # active mode; no secrets
    └── switch.lock
```

`auth.json` remains the active authentication entry point read by Codex. `codex-switch sub` and `codex-switch api` atomically replace that entry point using a temporary symlink and `rename`, without copying or editing `config.toml`.

The current Codex File credential backend resolves the `auth.json` symlink before saving credentials, then writes through a temporary file and atomic replacement. Therefore, when Codex refreshes OAuth tokens, it updates the target `auth-subscription.json` while leaving the symlink intact. Implementation references:

- [Codex `resolve_auth_file`](https://github.com/openai/codex/blob/main/codex-rs/login/src/auth/storage_file.rs)
- [Codex `FileAuthStorage::save`](https://github.com/openai/codex/blob/main/codex-rs/login/src/auth/storage.rs)

This behavior relies on the current Codex File backend implementation and should be revalidated if Codex changes its credential-writing behavior.

## Credential storage requirement

This tool only supports Codex's `cli_auth_credentials_store = "file"` mode:

- `File`: stores credentials in `CODEX_HOME/auth.json`; supported.
- `Keyring`: stores credentials in the OS keyring; this tool will not migrate or modify it.
- `Auto`: may select the keyring; rejected to avoid an ineffective switch.
- `Ephemeral`: stores credentials only in process memory; unsupported.

Codex's current default credential storage mode is `file`. During installation and switching, the tool prefers the `auth storage mode` reported by `codex doctor`; if unavailable, it checks an explicit `config.toml` value, then falls back to Codex's current default.

## Security and usage notes

- `~/.codex/codex-switch/` has directory mode `700`; OAuth, API-key, and backup files have mode `600`.
- The API key is stored in `auth-api.json`, not in `config.toml`, an environment variable, or a command-line argument. Like Codex's native `auth.json`, this is a plaintext local credential protected by filesystem permissions, not encrypted at rest.
- Fully quit Codex Desktop and stop active Codex CLI sessions before switching, so no running process refreshes or writes credentials during the switch.
- Restart Codex Desktop after switching. Existing sessions do not hot-switch.
- Both modes share the same `CODEX_HOME`, so Codex config, session history, MCP servers, and plugins remain shared. Model access and billing still depend on the active credential.
- `codex logout` removes the active `auth.json` symlink, but does not delete the credentials under `codex-switch/`. Run `codex-switch sub` or `codex-switch api` to recreate the active link.
- If you run `codex login` directly and it creates a new regular `auth.json`, the next `codex-switch sub` or `codex-switch api` invocation imports that new credential before switching.
- Environment variables such as `OPENAI_API_KEY`, `CODEX_API_KEY`, and `CODEX_ACCESS_TOKEN` may affect Codex authentication. The tool refuses to switch when it can detect these overrides; unset them before switching.
- This release provides manual switching only. It does not monitor subscription quota or automatically fall back when quota is exhausted.

## Uninstall

```bash
codex-switch uninstall
rm -f ~/.local/bin/codex-switch
```

`uninstall` atomically materializes the currently active credential as a regular `~/.codex/auth.json` file and preserves both managed credentials and the initial backup in `~/.codex/codex-switch/`. Remove that directory manually only after confirming you no longer need either credential or the backup.

## Development and tests

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile codex-switch
bash -n install.sh
```

Uses only the Python standard library; no third-party Python packages are required.

## License

MIT License. See [LICENSE](LICENSE).

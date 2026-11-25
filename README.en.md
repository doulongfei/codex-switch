# codex-switch

A minimal CLI for switching Codex between ChatGPT subscription authentication and the official OpenAI Platform API. Supports macOS and Ubuntu. No proxy, no Codex source changes, and no `codex logout`.

## One-line install

```bash
curl -fsSL https://raw.githubusercontent.com/doulongfei/codex-switch/main/install.sh | bash
```

The installer checks the OS and Python 3.8+, downloads the CLI and installs it to `~/.local/bin`, and registers the custom OpenAI API provider in your Codex user config.

## Quick start

```bash
codex-switch set-key
codex-switch api
codex-switch sub
codex-switch status
```

Optionally select a model enabled for your OpenAI API project:

```bash
codex-switch api --model <model-id>
```

## Commands

| Command | Description |
|---|---|
| `install` | Install the current script and register/update the API provider |
| `set-key` | Securely prompt for an OpenAI Platform API key |
| `set-key --from-env` | Save the key from `OPENAI_API_KEY` |
| `api` | Switch to the official OpenAI API provider |
| `api --model <id>` | Switch provider and set an API model ID |
| `sub` | Restore the previous provider and model |
| `status` | Show the active provider and local setup status |

## Security

The API key is stored at `~/.codex/codex-switch/openai-api-key` with directory mode `700` and file mode `600`. It is not written into `config.toml` and is not printed by `status`. The key file is plaintext protected by filesystem permissions; it is not encrypted at rest. Never commit it or place it in a shared/synced directory.

Codex reads the key using a command-backed custom-provider authentication entry. This tool does not proxy, inspect, or log model requests.

## Notes and limitations

- This release switches manually; it does not monitor subscription quota or auto-fallback.
- The tool edits the user-level Codex `config.toml`. It refuses to switch when a top-level active `profile` is configured, to avoid silently overriding profile-specific settings.
- `--model` must be a model ID actually enabled for your OpenAI API project.
- API usage is billed separately by the OpenAI Platform and is not part of the ChatGPT subscription.
- Fully quit and restart Codex Desktop after changing providers. Existing sessions do not hot-switch.

## Uninstall

Run `codex-switch sub`, then remove `~/.local/bin/codex-switch`. To remove the provider and key completely, manually remove the marked provider block from `~/.codex/config.toml` and delete `~/.codex/codex-switch/`. A one-time config backup is kept at `~/.codex/config.toml.codex-switch.bak`.

## Test

```bash
python3 -m unittest discover -s tests -v
```

MIT License. See [LICENSE](LICENSE).

# codex-switch v2.0.0 design

## Goal

Switch Codex between its native ChatGPT OAuth and OpenAI API-key authentication while preserving one `CODEX_HOME` and leaving `config.toml` unchanged.

## Data layout

- `CODEX_HOME/auth.json`: active authentication path read by Codex.
- `CODEX_HOME/codex-switch/auth-subscription.json`: Codex native ChatGPT OAuth credential.
- `CODEX_HOME/codex-switch/auth-api.json`: Codex native API-key credential.
- `CODEX_HOME/codex-switch/auth.json.codex-switch.bak`: first-migration rollback copy.
- `CODEX_HOME/codex-switch/state.json`: active mode only; no secrets.

`auth.json` is a relative symlink to one of the two managed credential files.

## Install / migration

The installer downloads and verifies the CLI, installs it, then invokes the hidden `_install` command. `_install` checks the effective credential storage mode and accepts only `File`. It validates the existing `auth.json` before changing anything. A supported existing credential is copied to its matching managed file with mode `0600`; the original is backed up once; then `auth.json` is atomically replaced with a relative symlink. Repeated installation is idempotent and does not overwrite an already managed target.

If no `auth.json` exists, installation does not create a dangling symlink. Unsupported auth types, invalid JSON, broken links, or non-File storage modes cause a safe stop without overwriting the original credential.

## API key setup

`setup-api` prompts for the key without echo, creates a private temporary directory under the managed data directory, and runs:

```bash
CODEX_HOME=<temporary-directory> codex login --with-api-key
```

The key is sent over stdin, not argv. The resulting native `auth.json` is validated as `auth_mode = "apikey"` and copied atomically to `auth-api.json`. The temporary directory is removed. If OAuth was active, OAuth remains active; if no credential was active, the new API credential becomes active.

## Switching

1. Acquire an exclusive local lock.
2. If `auth.json` is a regular file or an external symlink, validate and import it first.
3. Validate the target managed credential.
4. Create a temporary relative symlink in `CODEX_HOME`.
5. Use `os.replace` to atomically replace `auth.json` with the new symlink.
6. Persist the active mode in `state.json`.

Codex's current File backend resolves symlinks before writing credentials and uses atomic replacement for the target. This allows OAuth refreshes to update the managed subscription file. This is an implementation compatibility assumption, not a guarantee about future Codex versions.

## Safety boundaries

- Only `chatgpt` and `apikey` auth payloads are managed. External `chatgptAuthTokens`, Agent Identity, PAT, headers, and Bedrock credentials are rejected.
- Only the File credential backend is supported. Keyring, Auto, and Ephemeral are not migrated. Auth environment-variable overrides (`OPENAI_API_KEY`, `CODEX_API_KEY`, `CODEX_ACCESS_TOKEN`) are rejected when detected.
- No API request proxy, Gateway, custom provider, or config.toml edit is performed.
- The user should close Codex Desktop and active CLI sessions before switching to avoid concurrent credential refresh/write races.
- The API key is stored in a local JSON credential file with mode `0600`, like Codex's native auth file; it is not encrypted at rest.

## Platform support

macOS and Linux (Ubuntu tested in CI). Requires Python 3.8+, Codex CLI for `setup-api`, and filesystem symlink support.

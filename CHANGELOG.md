# Changelog

## 2.0.0

- Replaced custom Provider/config.toml switching with Codex native auth-file switching.
- Installer now automatically detects and imports an existing ChatGPT OAuth or API-key login.
- Added managed OAuth/API credential files and an atomic `auth.json` symlink switch.
- Added `setup-api`, which invokes Codex native API-key login in an isolated temporary `CODEX_HOME`.
- Added safe refusal for non-File credential stores and unsupported auth types.
- Added `status` and `uninstall` behavior for the symlink-based layout.
- Updated Chinese and English documentation.

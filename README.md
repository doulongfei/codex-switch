# codex-switch

[![macOS](https://img.shields.io/badge/platform-macOS-black)](https://www.apple.com/macos/)
[![Ubuntu](https://img.shields.io/badge/platform-Ubuntu-E95420)](https://ubuntu.com/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个轻量的 Codex 原生认证切换工具，在 **ChatGPT OAuth 订阅** 与 **OpenAI 官方 API Key** 之间切换。支持 macOS 和 Ubuntu，不使用自定义 Provider、代理服务或 Gateway，不修改 `config.toml`，也不执行 `codex logout`。

## 一键安装（安装时自动初始化）

在 macOS 或 Ubuntu 终端执行：

```bash
curl -fsSL https://raw.githubusercontent.com/doulongfei/codex-switch/main/install.sh | bash
```

安装程序会自动：

1. 检查操作系统和 Python 版本（Python 3.8+）。
2. 下载 CLI，并校验 SHA-256。
3. 安装到 `~/.local/bin/codex-switch`（可通过 `CODEX_SWITCH_INSTALL_DIR` 自定义）。
4. 检查 Codex 凭证存储模式；仅接受 `File`。
5. 检查现有 `~/.codex/auth.json`，识别 Codex 原生 ChatGPT OAuth 或 API Key。
6. 将现有认证安全迁移到 `~/.codex/codex-switch/`，并将 `auth.json` 原子替换为相对软连接。

如果检测到现有 ChatGPT OAuth，安装会直接复用，不要求重新登录。如果检测到现有 API Key，则将它纳入管理并保持 API 模式。如果没有 `auth.json`，安装只部署 CLI，不创建失效软连接。如果认证类型不支持、存储模式不是 `File`，或检测到可能覆盖文件凭证的认证环境变量，安装会停止认证迁移，不覆盖原凭证。

如果 `~/.local/bin` 不在 `PATH`，安装器会提示需要添加的 shell 配置。安装后重新打开终端，或使用 `~/.local/bin/codex-switch`。

## 快速开始

首次配置 OpenAI 官方 API Key：

```bash
codex-switch setup-api
```

随后即可切换：

```bash
# 使用 OpenAI Platform API Key，按 API 用量计费
codex-switch api

# 恢复 ChatGPT OAuth 订阅
codex-switch sub

# 查看当前模式和两份凭证是否存在
codex-switch status
```

`setup-api` 会在独立的临时 `CODEX_HOME` 中调用 Codex 原生命令 `codex login --with-api-key`，验证生成的 `auth.json` 后再保存为 `auth-api.json`。因此需要安装 Codex CLI。API Key 从隐藏输入提示读取，不会出现在命令行参数或 shell 历史中；如果当前正在使用 OAuth，配置 API Key 不会切换当前模式，也不会覆盖 OAuth。

## 命令

| 命令 | 说明 |
|---|---|
| `codex-switch api` | 切换到 OpenAI 官方 API Key |
| `codex-switch sub` | 切换到 ChatGPT OAuth 订阅 |
| `codex-switch setup-api` | 首次配置或更新 OpenAI 官方 API Key |
| `codex-switch status` | 查看当前认证模式、软连接目标和凭证状态 |
| `codex-switch uninstall` | 将当前活动凭证恢复为普通 `auth.json` 文件；保留凭证数据 |
| `codex-switch --version` | 查看版本 |

安装器内部使用的 `_install` 命令不需要用户手动执行。

## 工作原理

工具只管理 Codex 原生认证文件，不管理模型 Provider：

```text
~/.codex/
├── config.toml                         # 完全不修改
├── auth.json -> codex-switch/auth-subscription.json
└── codex-switch/
    ├── auth-subscription.json          # ChatGPT OAuth
    ├── auth-api.json                   # OpenAI API Key
    ├── auth.json.codex-switch.bak      # 首次迁移前的原始凭证备份
    ├── state.json                      # 当前模式，不含密钥
    └── switch.lock
```

`auth.json` 始终是 Codex 读取的活动认证入口。`codex-switch sub` 或 `codex-switch api` 通过同目录内的临时软连接和原子 `rename` 替换该入口，不复制或改写 `config.toml`。

当前 Codex 的 File 凭证存储实现会先解析 `auth.json` 软连接，再通过临时文件和原子替换写入目标文件。因此 Codex 自动刷新 OAuth Token 时，会更新 `auth-subscription.json` 的目标内容，软连接本身保持不变。实现依据：

- [Codex `resolve_auth_file`](https://github.com/openai/codex/blob/main/codex-rs/login/src/auth/storage_file.rs)
- [Codex `FileAuthStorage::save`](https://github.com/openai/codex/blob/main/codex-rs/login/src/auth/storage.rs)

该行为依赖 Codex 当前 File backend 的实现；如果未来 Codex 改变凭证写入方式，应重新验证兼容性。

## 凭证存储要求

本工具只支持 Codex 的 `cli_auth_credentials_store = "file"`：

- `File`：使用 `CODEX_HOME/auth.json`，支持本工具的软连接方案。
- `Keyring`：凭证在系统凭证管理器中，本工具不会迁移或修改。
- `Auto`：可能选择 Keyring，本工具拒绝使用以避免切换无效。
- `Ephemeral`：仅进程内存存储，不支持。

Codex 当前默认凭证存储模式为 `file`。安装和切换时会优先读取 `codex doctor` 的 `auth storage mode`；如果无法读取，再检查 `config.toml` 中显式配置，最后才使用 Codex 当前默认值。

## 安全与使用注意

- `~/.codex/codex-switch/` 目录权限为 `700`；OAuth、API Key 和备份文件权限为 `600`。
- API Key 保存在 `auth-api.json`，不会写入 `config.toml`、环境变量或命令行参数。它与 Codex 原生 `auth.json` 一样是本地明文凭证文件，依靠文件系统权限保护，不是加密存储。
- 切换前请完全退出 Codex Desktop，并结束正在运行的 Codex CLI 会话，避免切换期间仍有进程刷新或写入认证。
- 切换后重新启动 Codex Desktop。正在运行的会话不会热切换。
- 两种模式共用同一个 `CODEX_HOME`，因此仍使用同一套 Codex 配置、会话历史、MCP 和插件目录；模型权限与计费仍由当前认证决定。
- 如果执行 `codex logout`，Codex 会删除活动的 `auth.json` 软连接，但不会删除 `codex-switch/` 中保存的凭证。之后执行 `codex-switch sub` 或 `codex-switch api` 可以重新建立活动链接。
- 如果直接执行 `codex login` 并生成新的普通 `auth.json`，下次运行 `codex-switch sub` 或 `codex-switch api` 时，工具会先识别并导入新的认证，再切换。
- 如果环境中设置了 `OPENAI_API_KEY`、`CODEX_API_KEY` 或 `CODEX_ACCESS_TOKEN` 等认证变量，它们可能影响 Codex 的认证选择；工具会在可检测到时拒绝切换，并提示先取消这些变量。
- 当前版本提供手动切换，不监控订阅额度，也不会在额度耗尽时自动切换。

## 卸载

```bash
codex-switch uninstall
rm -f ~/.local/bin/codex-switch
```

`uninstall` 会将当前软连接指向的活动凭证原子恢复为普通 `~/.codex/auth.json` 文件，并保留 `~/.codex/codex-switch/` 中的两套凭证和首次迁移备份。确认不再需要 API Key 和 OAuth 备份后，再手动删除该目录。

## 开发与测试

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile codex-switch
bash -n install.sh
```

仅使用 Python 标准库，无需安装第三方 Python 包。

## License

MIT License. See [LICENSE](LICENSE).

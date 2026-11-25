# codex-switch

[![macOS](https://img.shields.io/badge/platform-macOS-black)](https://www.apple.com/macos/)
[![Ubuntu](https://img.shields.io/badge/platform-Ubuntu-E95420)](https://ubuntu.com/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个轻量的 Codex 命令行工具，在 **ChatGPT 订阅认证** 与 **OpenAI 官方 API Key** 之间切换。支持 macOS 和 Ubuntu，不需要代理服务、不修改 Codex 源码，也不会执行 `codex logout`。

## 一键安装

在 macOS 或 Ubuntu 终端执行：

```bash
curl -fsSL https://raw.githubusercontent.com/doulongfei/codex-switch/main/install.sh | bash
```

安装器会：

1. 检查操作系统和 Python 版本（Python 3.8+）。
2. 下载命令行程序。
3. 安装到 `~/.local/bin/codex-switch`（可通过 `CODEX_SWITCH_INSTALL_DIR` 自定义）。
4. 备份现有 `~/.codex/config.toml`，注册 OpenAI API 自定义 Provider。

如果安装目录不在 `PATH`，安装器会提示需要添加的 shell 配置。安装后重新打开终端，或直接使用 `~/.local/bin/codex-switch`。

## 快速开始

```bash
# 1. 安全录入 OpenAI Platform API Key（输入不回显）
codex-switch set-key

# 2. 切换到 OpenAI 官方 API 计费
codex-switch api

# 3. 用完后恢复切换前的 Provider（通常为 ChatGPT 订阅）
codex-switch sub

# 查看当前状态
codex-switch status
```

可选：切换到 API 时指定一个已在你的 OpenAI API 项目中启用的模型 ID：

```bash
codex-switch api --model <model-id>
```

工具会在切换时记录原模型，并在执行 `codex-switch sub` 时恢复。

## 命令

| 命令 | 说明 |
|---|---|
| `codex-switch install` | 注册/更新 OpenAI API Provider，并安装当前脚本到 `~/.local/bin` |
| `codex-switch set-key` | 交互式保存 OpenAI Platform API Key |
| `codex-switch set-key --from-env` | 从 `OPENAI_API_KEY` 环境变量读取并保存密钥 |
| `codex-switch api` | 切换到 OpenAI 官方 API Provider |
| `codex-switch api --model <id>` | 切换到 API Provider，并指定 API 模型 |
| `codex-switch sub` | 恢复切换前的 Provider 和模型 |
| `codex-switch status` | 查看当前模式、Provider 注册和 Key 配置状态 |
| `codex-switch --version` | 查看版本 |

## API Key 存储与安全

- Key 保存在 `~/.codex/codex-switch/openai-api-key`。
- 目录权限设置为 `700`，Key 文件权限设置为 `600`。
- Key 不会写入 `config.toml`，也不会显示在 `status` 输出中。
- Codex 通过本工具注册的 command-backed authentication 配置读取 Key。
- Key 文件是明文存储，依靠当前用户的文件系统权限保护；本工具不会对其加密。请勿将其加入 Git、云同步目录或公开日志。

## 工作原理

本工具只管理 Codex 用户级配置文件（默认 `~/.codex/config.toml`）：

- 安装时注册一个独立的 `openai` 官方 API Provider，使用 `https://api.openai.com/v1` 和 Responses API。
- `codex-switch api` 将顶层 `model_provider` 指向该 Provider。
- `codex-switch sub` 恢复切换前的 Provider；原有 ChatGPT OAuth 凭证不会被删除或覆盖。
- 不启动本地代理，不转发或记录模型请求。

Codex Desktop 已打开时，配置变更不会热切换当前会话。请完全退出并重新启动 Desktop。Codex CLI 的新进程会读取更新后的配置。

## 限制

- 当前版本是**手动切换工具**，不会检测订阅额度，也不会在额度耗尽时自动切换。
- 本工具修改的是用户级 `config.toml`。如果你通过 `--profile` 或顶层 `profile` 使用独立配置 Profile，当前版本会拒绝自动切换，以免错误覆盖 Profile 设置。
- `--model` 需要使用你的 OpenAI API 项目实际可用的模型 ID；工具不会猜测或验证模型权限。
- API 请求会按照 OpenAI Platform 的 API 价格单独计费，与 ChatGPT Pro 订阅额度分开。

## 卸载

先恢复订阅/原 Provider：

```bash
codex-switch sub
```

然后删除命令：

```bash
rm -f ~/.local/bin/codex-switch
```

如需彻底移除配置中的 Provider 区块和本地 Key，请先确认不再需要 API 模式，再手动删除 `~/.codex/config.toml` 中由 `codex-switch` 标记的区块，以及 `~/.codex/codex-switch/` 目录。原始配置备份位于 `~/.codex/config.toml.codex-switch.bak`。

## 开发与测试

```bash
python3 -m unittest discover -s tests -v
```

仅使用 Python 标准库，无需安装第三方依赖。

## License

MIT License. See [LICENSE](LICENSE).

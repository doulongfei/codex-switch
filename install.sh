#!/usr/bin/env bash
set -euo pipefail

REPO="doulongfei/codex-switch"
BRANCH="main"
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"
INSTALL_DIR="${CODEX_SWITCH_INSTALL_DIR:-${HOME}/.local/bin}"
TARGET="${INSTALL_DIR}/codex-switch"
TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t codex-switch)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM

say() { printf '[codex-switch] %s\n' "$*"; }
die() { printf '[codex-switch] Error: %s\n' "$*" >&2; exit 1; }

case "$(uname -s)" in
  Darwin) OS="macOS" ;;
  Linux) OS="Linux" ;;
  *) die "仅支持 macOS 和 Linux（Ubuntu）。当前系统：$(uname -s)" ;;
esac

command -v python3 >/dev/null 2>&1 || die "未找到 python3。请先安装 Python 3.8 或更高版本。"
python3 - <<'PY' || exit 1
import sys
if sys.version_info < (3, 8):
    raise SystemExit("需要 Python 3.8 或更高版本，当前版本：" + sys.version.split()[0])
PY

if command -v curl >/dev/null 2>&1; then
  download() { curl --fail --location --silent --show-error "$1" --output "$2"; }
elif command -v wget >/dev/null 2>&1; then
  download() { wget --quiet "$1" --output-document="$2"; }
else
  die "需要 curl 或 wget 才能下载安装文件。"
fi

say "检测到 ${OS}，安装目录：${INSTALL_DIR}"
mkdir -p "$TMP_DIR" "$INSTALL_DIR"
download "${RAW_BASE}/codex-switch" "$TMP_DIR/codex-switch" || die "下载 codex-switch 失败。"
download "${RAW_BASE}/codex-switch.sha256" "$TMP_DIR/codex-switch.sha256" || die "下载校验文件失败。"

EXPECTED="$(awk 'NR == 1 {print $1}' "$TMP_DIR/codex-switch.sha256")"
[ -n "$EXPECTED" ] || die "校验文件格式错误。"
if command -v sha256sum >/dev/null 2>&1; then
  ACTUAL="$(sha256sum "$TMP_DIR/codex-switch" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  ACTUAL="$(shasum -a 256 "$TMP_DIR/codex-switch" | awk '{print $1}')"
else
  die "找不到 sha256sum 或 shasum，无法校验下载文件。"
fi
[ "$EXPECTED" = "$ACTUAL" ] || die "SHA-256 校验失败，拒绝安装。"

chmod 755 "$TMP_DIR/codex-switch"
install -m 755 "$TMP_DIR/codex-switch" "$TARGET"

say "已安装可执行文件：${TARGET}"
"$TARGET" install --bin-dir "$INSTALL_DIR"

case ":${PATH}:" in
  *":${INSTALL_DIR}:"*) ;;
  *)
    say "安装目录当前不在 PATH 中。请将下面一行加入 ~/.zshrc 或 ~/.bashrc："
    printf '  export PATH="%s:$PATH"\n' "$INSTALL_DIR"
    ;;
esac

say "安装完成。下一步运行："
printf '  %s set-key\n' "$TARGET"
printf '  %s api\n' "$TARGET"
say "切换后请完全退出并重新启动 Codex Desktop；CLI 新进程会读取新配置。"

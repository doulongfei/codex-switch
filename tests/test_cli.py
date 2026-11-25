import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "codex-switch"

CHATGPT_AUTH = {
    "auth_mode": "chatgpt",
    "tokens": {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "id_token": "test-id-token",
    },
}
API_AUTH = {"auth_mode": "apikey", "OPENAI_API_KEY": "sk-test-not-real"}

FAKE_CODEX = r'''#!/bin/sh
if [ "$1" = "doctor" ]; then
  if [ "${FAKE_AUTH_DOCTOR_OUTPUT:-mode}" = "missing" ]; then
    printf 'Codex doctor test output without auth mode\n'
  else
    printf 'auth storage mode        %s\n' "${FAKE_AUTH_STORE_MODE:-File}"
  fi
  if [ -n "${FAKE_AUTH_ENV_VARS:-}" ]; then
    printf 'auth env vars present: %s\n' "$FAKE_AUTH_ENV_VARS"
  fi
  exit 0
fi
if [ "$1" = "login" ] && [ "$2" = "--with-api-key" ]; then
  IFS= read -r key
  mkdir -p "$CODEX_HOME"
  printf '{"auth_mode":"apikey","OPENAI_API_KEY":"%s"}\n' "$key" > "$CODEX_HOME/auth.json"
  chmod 600 "$CODEX_HOME/auth.json"
  exit 0
fi
printf 'unexpected fake codex args\n' >&2
exit 2
'''


class CodexSwitchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.codex_home = self.home / ".codex"
        self.bin = self.root / "bin"
        self.home.mkdir()
        self.bin.mkdir()
        self.env = os.environ.copy()
        self.env.update({
            "HOME": str(self.home),
            "CODEX_HOME": str(self.codex_home),
            "PATH": str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
        })
        fake = self.bin / "codex"
        fake.write_text(FAKE_CODEX, encoding="utf-8")
        fake.chmod(0o755)
        self.auth = self.codex_home / "auth.json"
        self.data = self.codex_home / "codex-switch"

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, input_text=None, check=True, extra_env=None):
        env = self.env.copy()
        if extra_env:
            env.update(extra_env)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            env=env,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
        )
        if check and result.returncode != 0:
            self.fail("command failed: %r\nstdout=%s\nstderr=%s" % (args, result.stdout, result.stderr))
        return result

    def write_auth(self, value):
        self.codex_home.mkdir(parents=True, exist_ok=True)
        self.auth.write_text(json.dumps(value), encoding="utf-8")
        self.auth.chmod(0o600)

    def read_json(self, path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_install_imports_existing_oauth_and_preserves_config(self):
        self.codex_home.mkdir(parents=True)
        self.write_auth(CHATGPT_AUTH)
        config = self.codex_home / "config.toml"
        config.write_text('model = "gpt-test"\napproval_policy = "on-request"\n', encoding="utf-8")
        before = config.read_bytes()

        result = self.run_cli("_install")

        self.assertTrue(self.auth.is_symlink())
        self.assertEqual(os.readlink(self.auth), "codex-switch/auth-subscription.json")
        self.assertEqual(self.read_json(self.data / "auth-subscription.json"), CHATGPT_AUTH)
        self.assertTrue((self.data / "auth.json.codex-switch.bak").exists())
        self.assertEqual(config.read_bytes(), before)
        self.assertIn("复用现有 ChatGPT OAuth", result.stdout)
        self.assertEqual((self.data / "auth-subscription.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.data.stat().st_mode & 0o777, 0o700)

    def test_install_imports_existing_api_key(self):
        self.write_auth(API_AUTH)
        self.run_cli("_install")
        self.assertTrue(self.auth.is_symlink())
        self.assertEqual(os.readlink(self.auth), "codex-switch/auth-api.json")
        self.assertEqual(self.read_json(self.data / "auth-api.json"), API_AUTH)

    def test_install_is_idempotent_and_does_not_overwrite_managed_files(self):
        self.write_auth(CHATGPT_AUTH)
        self.run_cli("_install")
        managed = self.data / "auth-subscription.json"
        managed.write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {"refresh_token": "refreshed"}}), encoding="utf-8")
        expected = managed.read_bytes()
        self.run_cli("_install")
        self.assertEqual(managed.read_bytes(), expected)
        self.assertTrue(self.auth.is_symlink())

    def test_codex_atomic_save_through_symlink_updates_subscription_target(self):
        self.write_auth(CHATGPT_AUTH)
        self.run_cli("_install")
        target = self.data / "auth-subscription.json"
        replacement = target.with_name(".auth-replacement")
        replacement.write_text(json.dumps({"auth_mode": "chatgpt", "tokens": {"refresh_token": "rotated-refresh"}}), encoding="utf-8")
        os.replace(replacement, target)
        self.assertTrue(self.auth.is_symlink())
        self.assertEqual(self.read_json(target)["tokens"]["refresh_token"], "rotated-refresh")

    def test_setup_api_uses_isolated_native_codex_login_and_preserves_oauth(self):
        self.write_auth(CHATGPT_AUTH)
        self.run_cli("_install")
        result = self.run_cli("setup-api", input_text="sk-test-not-real\nsk-test-not-real\n")
        self.assertTrue(self.auth.is_symlink())
        self.assertEqual(os.readlink(self.auth), "codex-switch/auth-subscription.json")
        self.assertEqual(self.read_json(self.data / "auth-subscription.json"), CHATGPT_AUTH)
        self.assertEqual(self.read_json(self.data / "auth-api.json"), API_AUTH)
        self.assertIn("Codex 原生登录流程", result.stdout)
        self.assertFalse(any(p.name.startswith(".api-login-") for p in self.data.iterdir()))

    def test_api_and_sub_switch_only_the_symlink(self):
        self.write_auth(CHATGPT_AUTH)
        self.run_cli("_install")
        self.run_cli("setup-api", input_text="sk-test-not-real\nsk-test-not-real\n")
        config = self.codex_home / "config.toml"
        config.write_text('model = "gpt-test"\n', encoding="utf-8")
        before = config.read_bytes()

        self.run_cli("api")
        self.assertEqual(os.readlink(self.auth), "codex-switch/auth-api.json")
        self.run_cli("sub")
        self.assertEqual(os.readlink(self.auth), "codex-switch/auth-subscription.json")
        self.assertEqual(config.read_bytes(), before)

    def test_status_does_not_expose_api_key(self):
        self.write_auth(CHATGPT_AUTH)
        self.run_cli("_install")
        self.run_cli("setup-api", input_text="sk-test-not-real\nsk-test-not-real\n")
        self.run_cli("api")
        result = self.run_cli("status")
        self.assertIn("OpenAI API Key", result.stdout)
        self.assertNotIn("sk-test-not-real", result.stdout)

    def test_refuses_non_file_backend_without_touching_auth(self):
        self.write_auth(CHATGPT_AUTH)
        before = self.auth.read_bytes()
        result = self.run_cli("_install", check=False, extra_env={"FAKE_AUTH_STORE_MODE": "Keyring"})
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.auth.is_symlink())
        self.assertEqual(self.auth.read_bytes(), before)

    def test_refuses_auth_environment_variable_override(self):
        self.write_auth(CHATGPT_AUTH)
        before = self.auth.read_bytes()
        result = self.run_cli("_install", check=False, extra_env={"OPENAI_API_KEY": "sk-env-test"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OPENAI_API_KEY", result.stderr)
        self.assertFalse(self.auth.is_symlink())
        self.assertEqual(self.auth.read_bytes(), before)

    def test_refuses_unknown_effective_storage_mode(self):
        self.write_auth(CHATGPT_AUTH)
        before = self.auth.read_bytes()
        result = self.run_cli("_install", check=False, extra_env={"FAKE_AUTH_DOCTOR_OUTPUT": "missing"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown", result.stderr.lower())
        self.assertFalse(self.auth.is_symlink())
        self.assertEqual(self.auth.read_bytes(), before)

    def test_refuses_unknown_auth_without_touching_auth(self):
        unknown = {"auth_mode": "agentIdentity", "agent_identity": "sensitive"}
        self.write_auth(unknown)
        before = self.auth.read_bytes()
        result = self.run_cli("_install", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.auth.is_symlink())
        self.assertEqual(self.auth.read_bytes(), before)

    def test_install_without_auth_does_not_create_broken_symlink(self):
        self.codex_home.mkdir(parents=True)
        self.run_cli("_install")
        self.assertFalse(self.auth.exists())
        self.assertFalse(self.auth.is_symlink())

    def test_sub_recovers_link_removed_by_codex_logout(self):
        self.write_auth(CHATGPT_AUTH)
        self.run_cli("_install")
        self.auth.unlink()  # Codex logout removes the auth.json link, not its target.
        self.run_cli("sub")
        self.assertTrue(self.auth.is_symlink())
        self.assertEqual(os.readlink(self.auth), "codex-switch/auth-subscription.json")

    def test_uninstall_materializes_current_auth_as_regular_file(self):
        self.write_auth(CHATGPT_AUTH)
        self.run_cli("_install")
        self.run_cli("uninstall")
        self.assertFalse(self.auth.is_symlink())
        self.assertEqual(self.read_json(self.auth), CHATGPT_AUTH)
        self.assertTrue((self.data / "auth-subscription.json").exists())

    def test_api_setup_without_existing_login_activates_api(self):
        self.codex_home.mkdir(parents=True)
        result = self.run_cli("setup-api", input_text="sk-test-not-real\nsk-test-not-real\n")
        self.assertTrue(self.auth.is_symlink())
        self.assertEqual(os.readlink(self.auth), "codex-switch/auth-api.json")
        self.assertEqual(self.read_json(self.data / "auth-api.json"), API_AUTH)
        self.assertIn("保存", result.stdout)


if __name__ == "__main__":
    unittest.main()

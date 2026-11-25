import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "codex-switch"


class CodexSwitchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.codex_home = self.home / ".codex"
        self.home.mkdir()
        self.env = os.environ.copy()
        self.env.update({"HOME": str(self.home), "CODEX_HOME": str(self.codex_home),
                         "PATH": os.environ.get("PATH", "")})
        self.config = self.codex_home / "config.toml"

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, check=True):
        result = subprocess.run(["python3", str(SCRIPT), *args], env=self.env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check and result.returncode != 0:
            self.fail(f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def test_install_registers_provider_and_preserves_existing_config(self):
        self.codex_home.mkdir(parents=True)
        original = 'model = "existing-model"\napproval_policy = "on-request"\n\n[features]\nfoo = true\n'
        self.config.write_text(original, encoding="utf-8")
        result = self.run_cli("install", "--bin-dir", str(self.home / ".local" / "bin"))
        updated = self.config.read_text(encoding="utf-8")
        self.assertIn('model = "existing-model"', updated)
        self.assertIn('approval_policy = "on-request"', updated)
        self.assertIn('[model_providers.codex_switch_openai_api]', updated)
        self.assertIn('base_url = "https://api.openai.com/v1"', updated)
        self.assertTrue((self.codex_home / "config.toml.codex-switch.bak").exists())
        self.assertIn("已安装", result.stdout)

    def test_api_then_sub_restores_original_provider_and_model(self):
        self.codex_home.mkdir(parents=True)
        self.config.write_text('model = "subscription-model"\nmodel_provider = "openai"\n', encoding="utf-8")
        self.run_cli("install", "--bin-dir", str(self.home / ".local" / "bin"))
        key_dir = self.codex_home / "codex-switch"
        key_dir.mkdir(mode=0o700, exist_ok=True)
        key = key_dir / "openai-api-key"
        key.write_text("sk-test-not-real\n", encoding="utf-8")
        key.chmod(0o600)
        self.run_cli("api", "--model", "example-api-model")
        api_config = self.config.read_text(encoding="utf-8")
        self.assertIn('model = "example-api-model"', api_config)
        self.assertIn('model_provider = "codex_switch_openai_api"', api_config)
        self.run_cli("sub")
        restored = self.config.read_text(encoding="utf-8")
        self.assertIn('model = "subscription-model"', restored)
        self.assertIn('model_provider = "openai"', restored)
        self.assertNotIn('model_provider = "codex_switch_openai_api"', restored)

    def test_status_does_not_print_api_key(self):
        self.codex_home.mkdir(parents=True)
        self.run_cli("install", "--bin-dir", str(self.home / ".local" / "bin"))
        key_dir = self.codex_home / "codex-switch"
        key_dir.mkdir(mode=0o700, exist_ok=True)
        key = key_dir / "openai-api-key"
        key.write_text("sk-test-secret-value\n", encoding="utf-8")
        key.chmod(0o600)
        result = self.run_cli("status")
        self.assertIn("已配置", result.stdout)
        self.assertNotIn("sk-test-secret-value", result.stdout)

    def test_refuses_active_profile(self):
        self.codex_home.mkdir(parents=True)
        self.config.write_text('profile = "work"\n', encoding="utf-8")
        self.run_cli("install", "--bin-dir", str(self.home / ".local" / "bin"))
        key_dir = self.codex_home / "codex-switch"
        key_dir.mkdir(mode=0o700, exist_ok=True)
        key = key_dir / "openai-api-key"
        key.write_text("sk-test-not-real\n", encoding="utf-8")
        key.chmod(0o600)
        result = self.run_cli("api", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("profile", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()

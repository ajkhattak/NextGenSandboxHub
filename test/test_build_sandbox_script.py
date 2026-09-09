from pathlib import Path
import os
import subprocess
import tempfile
import unittest


class TestBuildSandboxScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.bootstrap = (cls.repo_root / "bootstrap.sh").read_text()
        cls.script = (
            cls.repo_root / "scripts" / "bootstrap" / "build_sandbox.sh"
        ).read_text()

    def test_bootstrap_uses_internal_script_directory(self):
        self.assertIn("./scripts/bootstrap/build_sandbox.sh", self.bootstrap)
        self.assertIn("./scripts/bootstrap/build_venv_subset.sh", self.bootstrap)
        self.assertIn("./scripts/bootstrap/build_models.sh", self.bootstrap)
        self.assertIn("./scripts/bootstrap/sandbox_env.sh", self.bootstrap)
        self.assertNotIn("./utils/build_sandbox.sh", self.bootstrap)
        self.assertNotIn("./utils/sandbox_env.sh", self.bootstrap)

    def test_environment_definitions_use_internal_script_directory(self):
        self.assertIn(
            "$SANDBOX_DIR/scripts/bootstrap/venv/venv_sandbox.yaml",
            self.script,
        )
        self.assertIn(
            "$SANDBOX_DIR/scripts/bootstrap/venv/venv_forcing.yaml",
            self.script,
        )

    def test_does_not_require_uv(self):
        self.assertNotIn("uv pip install", self.script)
        self.assertNotIn("pip install uv", self.script)

    def test_installs_with_target_environment_python(self):
        self.assertIn(
            '"$SANDBOX_PYTHON" -m pip install -e \'.[test]\'',
            self.script,
        )
        self.assertIn(
            '"$FORCING_ENV/bin/python" -m pip install',
            self.script,
        )

    def test_rejects_rebuilding_active_virtual_environment(self):
        self.assertIn(
            'same_directory "$ACTIVE_PYTHON_ENV" "$SANDBOX_ENV"',
            self.script,
        )
        self.assertIn(
            "Deactivate it before rebuilding it:",
            self.script,
        )

    def test_finds_module_conda_through_conda_exe(self):
        self.assertIn('if [ -n "${CONDA_EXE:-}" ]', self.script)
        self.assertIn(
            'eval "$("$CONDA_EXE_PATH" shell.bash hook)"',
            self.script,
        )
        self.assertIn('CONDA_AVAILABLE=ON', self.script)
        self.assertIn(
            'status_ok "conda: $CONDA_EXE (from CONDA_EXE)"',
            self.bootstrap,
        )

    def test_ignores_unrelated_build_environment_variable(self):
        self.assertNotIn("BUILD_SANDBOX=${BUILD:-ON}", self.script)
        self.assertIn(
            "BUILD_SANDBOX=${BUILD_SANDBOX:-ON}",
            self.script,
        )

    def test_nonpersistent_environment_load_does_not_edit_shell_startup(self):
        environment_script = (
            self.repo_root / "scripts" / "bootstrap" / "sandbox_env.sh"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(root / "home"),
                    "SHELL": "/bin/bash",
                    "SANDBOX_BUILD_DIR": str(root / "build"),
                    "SANDBOX_DATA_DIR": str(root / "data"),
                    "SANDBOX_CONDARC": str(root / "build" / "condarc"),
                }
            )
            env.pop("SANDBOX_ENV_LOADED", None)
            (root / "home").mkdir()

            subprocess.run(
                [
                    "bash",
                    "-c",
                    f'set -u; source "{environment_script}" PERSIST=OFF',
                ],
                check=True,
                env=env,
            )

            self.assertFalse((root / "home" / ".bashrc").exists())


if __name__ == "__main__":
    unittest.main()

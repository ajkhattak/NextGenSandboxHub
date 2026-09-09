from pathlib import Path
import unittest

import yaml

from src.python.calibration_config import load_calibration_settings
from src.python.time_windows import (
    normalize_simulation_tasks,
    normalize_simulation_time_config,
)


class TestConfigurationSamples(unittest.TestCase):
    def validate_config(self, path):
        with path.open("r") as file:
            config = yaml.safe_load(file)

        self.assertIsInstance(config, dict)
        self.assertEqual(
            set(config),
            {
                "general",
                "subsetting",
                "forcings",
                "observations",
                "calibration",
                "formulations",
                "simulation",
            },
        )

        sandbox_dir = Path(__file__).resolve().parents[1]
        load_calibration_settings(config, path, sandbox_dir)
        tasks = normalize_simulation_tasks(config["simulation"])
        normalize_simulation_time_config(
            config["simulation"],
            tasks,
            config_dir=path.parent,
        )

    def test_distributed_sandbox_configs_are_valid(self):
        sandbox_dir = Path(__file__).resolve().parents[1]

        for filename in (
            "sandbox_config.yaml",
            "sandbox_config_reference.yaml",
        ):
            with self.subTest(filename=filename):
                path = sandbox_dir / "configs" / filename
                self.validate_config(path)

    def test_smoke_test_config_is_valid(self):
        sandbox_dir = Path(__file__).resolve().parents[1]
        self.validate_config(
            sandbox_dir / "test" / "configs" / "sandbox_config.yaml"
        )


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from pathlib import Path

from mac_token_broker.launchd import launch_agent_payload


class LaunchAgentTests(unittest.TestCase):
    def test_python_module_is_importable_at_startup(self):
        payload = launch_agent_payload()
        args = payload["ProgramArguments"]
        self.assertEqual(args[1:], ["-m", "mac_token_broker.cli", "serve"])
        root = Path(payload["EnvironmentVariables"]["PYTHONPATH"])
        self.assertTrue((root / "mac_token_broker" / "cli.py").is_file())
        self.assertTrue(Path(args[0]).is_file())
        self.assertEqual(payload["RunAtLoad"], True)
        self.assertEqual(payload["KeepAlive"], {"SuccessfulExit": False})


if __name__ == "__main__":
    unittest.main()

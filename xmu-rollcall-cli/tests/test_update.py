import unittest
from unittest.mock import patch

from click.testing import CliRunner

from xmu_rollcall.cli import INSTALL_URL, cli


class UpdateCommandTests(unittest.TestCase):
    def invoke(self, args, uv_path):
        with patch("xmu_rollcall.cli.setup_logging") as setup_logging, patch(
            "xmu_rollcall.cli.load_config"
        ) as load_config, patch("xmu_rollcall.cli.save_config") as save_config, patch(
            "xmu_rollcall.cli.shutil.which", return_value=uv_path
        ), patch("xmu_rollcall.cli.subprocess.run") as run:
            run.return_value.returncode = 0
            result = CliRunner().invoke(cli, args)
        return result, setup_logging, load_config, save_config, run

    def test_update_uses_uv_tool_install_when_uv_is_present(self):
        result, setup_logging, load_config, save_config, run = self.invoke(
            ["update"], "/usr/bin/uv"
        )
        self.assertEqual(result.exit_code, 0, result.output)
        run.assert_called_once_with([
            "uv", "tool", "install", "--upgrade", "--force", INSTALL_URL,
        ])
        setup_logging.assert_not_called()
        load_config.assert_not_called()
        save_config.assert_not_called()

    def test_upgrade_alias_uses_pip_when_uv_is_absent(self):
        result, setup_logging, load_config, save_config, run = self.invoke(
            ["upgrade"], None
        )
        self.assertEqual(result.exit_code, 0, result.output)
        run.assert_called_once_with(["pip", "install", "--upgrade", INSTALL_URL])
        setup_logging.assert_not_called()
        load_config.assert_not_called()
        save_config.assert_not_called()

    def test_menu_update_returns_to_the_menu(self):
        with patch("xmu_rollcall.cli.setup_logging"), patch(
            "xmu_rollcall.cli.load_config", return_value={}
        ), patch("xmu_rollcall.cli.shutil.which", return_value="/usr/bin/uv"), patch(
            "xmu_rollcall.cli.subprocess.run"
        ) as run:
            run.return_value.returncode = 0
            result = CliRunner().invoke(cli, input="5\n")
        self.assertEqual(result.exit_code, 0, result.output)
        run.assert_called_once()
        self.assertIn("Goodbye", result.output)
        self.assertEqual(result.output.count("Welcome back"), 2)


if __name__ == "__main__":
    unittest.main()

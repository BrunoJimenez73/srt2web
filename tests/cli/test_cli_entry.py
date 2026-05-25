from __future__ import annotations

from click.testing import CliRunner

from cli.main import cli


class TestCLIEntry:
    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_health_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["health", "--help"])
        assert result.exit_code == 0

    def test_status_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0

    def test_config_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0

    def test_logs_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["logs", "--help"])
        assert result.exit_code == 0

    def test_pipeline_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "stop" in result.output
        assert "restart" in result.output

    def test_tui_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["tui", "--help"])
        assert result.exit_code == 0

    def test_module_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["module", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "toggle" in result.output
        assert "debug" in result.output

    def test_output_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["output", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "add" in result.output
        assert "remove" in result.output
        assert "toggle" in result.output

    def test_preset_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["preset", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "save" in result.output
        assert "apply" in result.output
        assert "delete" in result.output

    def test_recording_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["recording", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "delete" in result.output

    def test_input_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["input", "--help"])
        assert result.exit_code == 0
        assert "info" in result.output
        assert "play" in result.output
        assert "pause" in result.output
        assert "seek" in result.output

    def test_network_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["network", "--help"])
        assert result.exit_code == 0
        assert "info" in result.output

from typer.testing import CliRunner

from ny_oca_conviction.cli import app


def test_cli_help_smoke():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "discover-sources" in result.stdout
    assert "fetch-supplemental-pretrial" in result.stdout
    assert "build-supplemental-pretrial-policy-sample" in result.stdout
    assert "build-supplemental-pretrial-policy-tables" in result.stdout
    assert "build-supplemental-pretrial-policy-effects" in result.stdout
    assert "build-public-figures" in result.stdout
    assert "replicate-supplemental-pretrial" in result.stdout
    assert "analyze-race-association" in result.stdout

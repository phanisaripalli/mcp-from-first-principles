from __future__ import annotations

import pytest

from examples.mcp_trade_demo import args_from_cli


def test_trade_demo_defaults_to_germany_lithium_china_path() -> None:
    assert args_from_cli([]) == ("DEU", 2023, "CHN")


def test_trade_demo_accepts_importer_year_and_exporter() -> None:
    assert args_from_cli(["deu", "2022", "chn"]) == ("DEU", 2022, "CHN")


def test_trade_demo_accepts_importer_year_without_exporter() -> None:
    assert args_from_cli(["deu", "2022"]) == ("DEU", 2022, None)


def test_trade_demo_rejects_wrong_argument_count() -> None:
    with pytest.raises(ValueError, match="Usage:"):
        args_from_cli(["DEU"])


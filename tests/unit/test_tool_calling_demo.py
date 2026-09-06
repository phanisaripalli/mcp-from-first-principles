from __future__ import annotations

import pytest

from examples.tool_calling_demo import country_from_args


def test_country_from_args_defaults_to_germany() -> None:
    assert country_from_args([]) == "DEU"


def test_country_from_args_accepts_one_country_code() -> None:
    assert country_from_args(["ind"]) == "IND"


def test_country_from_args_rejects_more_than_one_argument() -> None:
    with pytest.raises(ValueError, match="Usage:"):
        country_from_args(["IND", "USA"])


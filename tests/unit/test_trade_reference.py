from __future__ import annotations

import pytest

from trade_intel.trade.reference import (
    parse_country_codes,
    parse_product_codes,
    rank_product_matches,
)


def test_parse_country_codes_normalizes_reporters() -> None:
    codes = parse_country_codes(
        {
            "results": [
                {
                    "reporterCode": 276,
                    "reporterDesc": "Germany",
                    "reporterCodeIsoAlpha3": "DEU",
                }
            ]
        },
        endpoint="https://comtradeapi.un.org/files/v1/app/reference/Reporters.json",
        role="reporter",
    )

    assert codes[0].code == 276
    assert codes[0].iso3 == "DEU"
    assert codes[0].name == "Germany"
    assert codes[0].entry_expired_date is None
    assert codes[0].provenance.source == "UN Comtrade reference data"


def test_parse_product_codes_and_rank_lithium_ion_match() -> None:
    products = parse_product_codes(
        {
            "className": "Combined HS",
            "results": [
                {
                    "id": "8507",
                    "text": "8507 - Electric accumulators, including separators",
                    "parent": "85",
                    "isLeaf": "0",
                    "aggrLevel": 4,
                    "standardUnitAbbr": "n/a",
                },
                {
                    "id": "850760",
                    "text": (
                        "850760 - Electric accumulators; lithium-ion, including "
                        "separators, whether or not rectangular (including square)"
                    ),
                    "parent": "8507",
                    "isLeaf": "1",
                    "aggrLevel": 6,
                    "standardUnitAbbr": "u",
                },
            ],
        },
        endpoint="https://comtradeapi.un.org/files/v1/app/reference/HS.json",
    )

    matches = rank_product_matches(products, "lithium ion batteries", limit=5)

    assert matches[0].hs_code == "850760"
    assert matches[0].is_leaf is True
    assert matches[0].standard_unit == "u"
    assert matches[0].provenance.notes == "Combined HS"


def test_empty_product_query_is_rejected() -> None:
    with pytest.raises(ValueError, match="query must not be empty"):
        rank_product_matches([], " ", limit=5)

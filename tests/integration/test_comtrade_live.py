from __future__ import annotations

import asyncio
import os

import pytest

from trade_intel.trade import TradeClient


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_COMTRADE_TESTS") != "1",
    reason="Set RUN_LIVE_COMTRADE_TESTS=1 to call the live UN Comtrade API.",
)
def test_live_comtrade_product_lookup_and_imports() -> None:
    async def scenario():
        async with TradeClient() as client:
            products = await client.find_product_code("lithium-ion batteries", limit=5)
            flow = await client.get_imports(
                "DEU",
                products[0].hs_code,
                2023,
                exporter="CHN",
            )
            return products, flow

    products, flow = asyncio.run(scenario())

    assert products[0].hs_code == "850760"
    assert flow.importer_code == "DEU"
    assert flow.importer_comtrade_code == 276
    assert flow.exporter_code == "CHN"
    assert flow.exporter_comtrade_code == 156
    assert flow.trade_value_usd > 0
    assert flow.provenance.source == "UN Comtrade public preview API"


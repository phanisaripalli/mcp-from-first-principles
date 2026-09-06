from __future__ import annotations

import asyncio
import os

import pytest

from trade_intel.worldbank import WorldBankClient


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_WORLD_BANK_TESTS") != "1",
    reason="Set RUN_LIVE_WORLD_BANK_TESTS=1 to call the live World Bank API.",
)
def test_live_country_and_indicator_lookup() -> None:
    async def scenario():
        async with WorldBankClient() as client:
            profile = await client.get_country_profile("DEU")
            observations = await client.get_indicator(["DEU"], "SP.POP.TOTL", 2020, 2021)
            return profile, observations

    profile, observations = asyncio.run(scenario())

    assert profile.country_code == "DEU"
    assert profile.name == "Germany"
    assert observations
    assert all(observation.provenance.source == "World Bank Indicators API" for observation in observations)


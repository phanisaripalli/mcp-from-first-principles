from __future__ import annotations

import asyncio

from trade_intel.worldbank import WorldBankClient


async def main() -> None:
    async with WorldBankClient() as client:
        profile = await client.get_country_profile("DEU")
        observations = await client.get_indicator(["DEU"], "NY.GDP.MKTP.CD", 2022, 2023)

    print(f"{profile.name}: {profile.region_name}, {profile.income_level_name}")
    for observation in observations:
        print(
            f"{observation.year}: {observation.indicator_name} = "
            f"{observation.value} ({observation.source})"
        )


if __name__ == "__main__":
    asyncio.run(main())


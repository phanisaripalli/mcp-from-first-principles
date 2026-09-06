class WorldBankError(Exception):
    """Base class for World Bank client errors."""


class WorldBankHTTPError(WorldBankError):
    """The upstream API returned an HTTP error or could not be reached."""


class WorldBankAPIError(WorldBankError):
    """The upstream API returned a structured API error."""


class WorldBankNotFoundError(WorldBankError):
    """The requested country, indicator, or observation was not found."""


class WorldBankResponseError(WorldBankError):
    """The upstream API response did not match the expected shape."""


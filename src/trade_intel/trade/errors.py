class TradeDataError(Exception):
    """Base class for trade-data client errors."""


class TradeDataHTTPError(TradeDataError):
    """The upstream trade API returned an HTTP error or could not be reached."""


class TradeDataNotFoundError(TradeDataError):
    """A requested country, product code, or trade flow was not found."""


class TradeDataResponseError(TradeDataError):
    """The upstream trade API response did not match the expected shape."""


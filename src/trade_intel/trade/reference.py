from __future__ import annotations

import re
from typing import Any

from trade_intel.provenance import Provenance
from trade_intel.trade.errors import TradeDataResponseError
from trade_intel.trade.models import CountryCode, ProductCodeCandidate


WORD_RE = re.compile(r"[a-z0-9]+")


def parse_country_codes(
    payload: dict[str, Any],
    *,
    endpoint: str,
    role: str,
) -> list[CountryCode]:
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise TradeDataResponseError("Expected Comtrade reference response with results")

    codes: list[CountryCode] = []
    provenance = Provenance(
        source="UN Comtrade reference data",
        endpoint=endpoint,
        query_params={},
        total=len(rows),
    )
    for row in rows:
        if not isinstance(row, dict):
            raise TradeDataResponseError("Expected country reference rows to be objects")
        if role == "reporter":
            code = row.get("reporterCode")
            iso3 = row.get("reporterCodeIsoAlpha3")
            name = row.get("reporterDesc")
            expired = row.get("entryExpiredDate")
        else:
            code = row.get("PartnerCode")
            iso3 = row.get("PartnerCodeIsoAlpha3")
            name = row.get("PartnerDesc")
            expired = row.get("entryExpiredDate")
        if not isinstance(code, int) or not isinstance(iso3, str) or not isinstance(name, str):
            continue
        codes.append(
            CountryCode(
                code=code,
                iso3=iso3.upper(),
                name=name.strip(),
                role=role,
                entry_expired_date=_optional_str(expired),
                provenance=provenance,
            )
        )
    return codes


def parse_product_codes(
    payload: dict[str, Any],
    *,
    endpoint: str,
) -> list[ProductCodeCandidate]:
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise TradeDataResponseError("Expected Comtrade HS response with results")

    provenance = Provenance(
        source="UN Comtrade HS reference data",
        endpoint=endpoint,
        query_params={},
        total=len(rows),
        notes=_optional_str(payload.get("className")),
    )
    products: list[ProductCodeCandidate] = []
    for row in rows:
        if not isinstance(row, dict):
            raise TradeDataResponseError("Expected HS reference rows to be objects")
        hs_code = row.get("id")
        text = row.get("text")
        if not isinstance(hs_code, str) or not isinstance(text, str):
            continue
        products.append(
            ProductCodeCandidate(
                hs_code=hs_code,
                description=_strip_code_prefix(text, hs_code),
                parent=_optional_str(row.get("parent")),
                is_leaf=str(row.get("isLeaf")) == "1",
                aggregation_level=int(row.get("aggrLevel") or 0),
                standard_unit=_optional_str(row.get("standardUnitAbbr")),
                provenance=provenance,
            )
        )
    return products


def rank_product_matches(
    products: list[ProductCodeCandidate],
    query: str,
    *,
    limit: int,
) -> list[ProductCodeCandidate]:
    query_tokens = set(_tokens(query))
    if not query_tokens:
        raise ValueError("query must not be empty")

    scored: list[tuple[int, ProductCodeCandidate]] = []
    normalized_query = " ".join(_tokens(query))
    for product in products:
        normalized_description = " ".join(_tokens(product.description))
        description_tokens = set(_tokens(f"{product.hs_code} {product.description}"))
        overlap = len(query_tokens & description_tokens)
        exact_bonus = 3 if normalized_query in normalized_description else 0
        phrase_bonus = 3 if "lithium ion" in normalized_query and "lithium ion" in normalized_description else 0
        code_bonus = 2 if query.strip() == product.hs_code else 0
        leaf_bonus = 1 if product.is_leaf else 0
        score = overlap + exact_bonus + phrase_bonus + code_bonus + leaf_bonus
        if score > 0:
            scored.append((score, product))

    scored.sort(key=lambda item: (-item[0], item[1].aggregation_level, item[1].hs_code))
    return [product for _score, product in scored[:limit]]


def _tokens(value: str) -> list[str]:
    return [_normalize_token(token) for token in WORD_RE.findall(value.lower())]


def _normalize_token(token: str) -> str:
    if token in {"accumulator", "accumulators", "battery", "batteries"}:
        return "battery"
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _strip_code_prefix(text: str, hs_code: str) -> str:
    prefix = f"{hs_code} - "
    if text.startswith(prefix):
        return text[len(prefix) :].strip()
    return text.strip()


def _optional_str(value: Any) -> str | None:
    if value in (None, "", "n/a"):
        return None
    if not isinstance(value, str):
        return str(value)
    return value.strip()

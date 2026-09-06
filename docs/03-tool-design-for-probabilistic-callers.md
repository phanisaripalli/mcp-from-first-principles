# 03 - Tool Design For Probabilistic Callers

Tool design matters because an LLM is not a normal programmer.

A programmer can read source code, understand hidden conventions, and fix a bad call after seeing a stack trace. A model only sees the tool metadata the host gives it. Names, descriptions, and schemas become part of the model's decision context.

## A Poor Tool

```json
{
  "name": "query_worldbank",
  "description": "Query World Bank.",
  "input_schema": {
    "path": "string",
    "params": "object"
  }
}
```

This is technically flexible, but it asks the model to know too much:

- which endpoint path to use
- which query parameters are valid
- how country codes are represented
- how date ranges are encoded
- what kind of result will come back

It leaks the upstream API instead of exposing the project capability.

## A Better Tool

```json
{
  "name": "get_country_profile",
  "description": "Fetch normalized World Bank metadata for a country...",
  "input_schema": {
    "country": {
      "type": "string",
      "description": "ISO country code or World Bank country code, such as DEU."
    }
  }
}
```

This tool is narrower and easier to choose. It says what it does in domain language, and the schema makes the expected argument clear.

## The Tradeoff

Generic tools are flexible for humans but brittle for models. Domain-specific tools are less general, but they reduce ambiguity and keep bad calls away from the data layer.

That is why this project prefers tools such as:

- `search_development_indicators`
- `get_development_indicator`
- `get_country_profile`

over a single `query_worldbank` escape hatch.

## Validation Is Part Of The Lesson

Validation is not just defensive programming. It is how the deterministic part of the system refuses malformed requests from the probabilistic part.

In this milestone, validation catches:

- missing required arguments
- arguments with the wrong type
- extra unsupported arguments
- integer values outside simple bounds
- empty strings and empty arrays

Good validation makes failures legible. A tool should return a useful error rather than letting a malformed request wander into an upstream API call.


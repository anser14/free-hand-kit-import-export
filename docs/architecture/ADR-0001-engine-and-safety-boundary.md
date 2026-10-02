# ADR-0001: use django-import-export behind a Freehand API boundary

## Status

Accepted for the `0.x` foundation.

## Decision

Use `django-import-export` for model resource construction, dataset conversion,
validation, relationship widgets, and transactions. Freehand Kit owns resource
registration, field safety, DRF workflow endpoints, OpenAPI, permissions, job audit,
CSV safety, and future queue adapters.

## Consequences

`django-import-export` remains a replaceable implementation dependency. No public
Freehand endpoint exposes arbitrary model labels or the dependency's private API.
An alternative engine must preserve the configured resource contract and observable
import results before replacement.

## Rejected alternative

Building a complete CSV/model engine first would require Freehand Kit to immediately
own parsing, type coercion, relation mapping, transactions, upserts, errors, bulk
behavior, encoding, and compatibility edge cases already handled by the dependency.

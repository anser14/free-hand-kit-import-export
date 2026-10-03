# Testing

Test each resource with scalar fields, foreign keys, many-to-many values, duplicate
identifiers, invalid cells, unauthorized callers, owner isolation, source tampering,
row and byte limits, relationship filters, pagination, CSV formula values, export
limits, queue confirmation idempotency, worker completion, stale-job recovery,
retry exhaustion, sanitized error reports, tenant/queryset scopes, and a replay of the
same confirmation. Also test configured retention with a dry run, source-only deletion,
full terminal-job deletion, storage failure handling, and protection of nonterminal
jobs. Test lifecycle callbacks after a real database commit and verify a failing receiver
does not affect the import outcome. Package CI must validate the OpenAPI schema and both
wheel and source distribution.

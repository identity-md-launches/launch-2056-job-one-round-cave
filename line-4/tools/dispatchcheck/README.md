# DispatchCheck

Find changes behind OpenAPI discriminator mappings, including an unchanged
mapping string whose local target schema changed. This standard-library Python
extension retains FallbackHeaders and every earlier line 4 analyzer. Keep its
sibling tool folders; Python 3.9+ is sufficient. It reads descriptions only.

From the repository root, one command demonstrates the new check offline:

```sh
python3 -B line-4/tools/dispatchcheck/dispatchcheck.py demo
```

The demo starts from the bundled real IMD OpenAPI description, then creates a
clearly hypothetical response on one saved operation. Its `done` tag still
points to the same schema, but the target's `receipt` changes from string to
integer. The result is **one potential branch-level break and one retained
review**, with the exact tag and target property location. These dispatch
contracts are invented in memory; they are not claims about the live service.

Compare your own local JSON descriptions with:

```sh
python3 -B line-4/tools/dispatchcheck/dispatchcheck.py compare old.json new.json
```

Paths must resolve inside the current workspace. Output is deterministic JSON
with input-byte SHA-256 values. Compare exits: **0** no detected break within the
supported subset, **1** potential break, **2** invalid/unsupported input or a
budget refusal, **3** unresolved review only. The demo exits 0 after checking
that its intended finding exists. No described API operation is executed.

## What is checked

The [OpenAPI 3.1 Discriminator Object](https://spec.openapis.org/oas/v3.1.0.html#discriminator-object)
uses `propertyName` to select the tag field and `mapping` to associate values
with schema names or references. DispatchCheck reports added/removed hints,
changed tag properties, changed explicit tag coverage and retargeted mappings
as **reviews**. It does not assume explicit mapping keys form a closed enum or
that changing a dispatch hint alone proves incompatible validation.

For a common explicit tag and equal `propertyName`, it resolves each target and
compares it using the inherited request/response constraint rules. Request
narrowing and response widening can produce potential breaks. Both `Done` and
`#/components/schemas/Done` resolve to the same component route. Local pointer
escapes and aliases are supported; remote URLs, unresolved targets, reference
alias cycles and unsupported `$ref` siblings are refused without fetching.
Target traversal follows recursive local schema graphs with an active-pair
cycle guard. Equal inline containers are walked too: mapping targets are
references even though the JSON has no literal `$ref` at that location.
This can also validate unchanged constraints that earlier equality shortcuts
skipped; unsupported data may therefore be refused more strictly.

`dispatch_pairs` records each comparison's tag, normalized old/new references,
direction and mapping location. Findings under `/mapping/<tag>/target` use a
**virtual location**: the mapping entry contains a string, and its resolved
schema is the target of that diagnostic. Existing findings and status-selector
groups remain in the report, including checks across fallback responses.

## Bounds and limits

Support is OpenAPI 3.0.x/3.1.x JSON and common inline top-level operations.
Discriminators are found at inherited schema traversal sites: request bodies,
parameters, response bodies/headers, properties, items, and explicitly mapped
targets. Arbitrary union branches, additional-property schemas, callbacks,
webhooks and unused components are not recursively analyzed by this extension.
The tool does not infer implicit schema-name routes; an omitted/empty explicit
mapping produces a review. A partially explicit mapping covers only its common
explicit tags. Added/removed branches and changed tag properties stay reviews.

Discriminator use requires a nonempty `oneOf`, `anyOf` or `allOf` array, but this
is not full composite validation. A target finding is evidence about that
branch's declared constraints, **not proof of whole-union incompatibility**:
other constraints may make the branch unreachable, and other branches may
cover a payload. Use actual generated-client tests and review findings before
updating an integration. Unchanged input and exit 0 do not certify a live API.

Limits: 64 explicit mappings per visited discriminator, 512 common target
pairs, 20,000 schema visits, 2,000 findings, 1 MiB per input, 50,000 input nodes,
depth 80, and inherited operation/header/security/server budgets (including at
most 40 common operations). No truncated report is returned as a pass. No
third-party package, credential, coin, balance or payment is required.

## Tried on 2026-10-17

- `python3 -B line-4/tools/dispatchcheck/selftest.py`: **19 tests passed**.
  Coverage includes 98 independently enumerated request/response payload-set
  comparisons, unchanged mapping targets, equivalent schema names/pointers,
  pointer escapes, nested inline containers, array items, recursion, boolean
  targets, fallback selectors, malformed input and resource refusals, retained
  earlier findings, deterministic nonmutation, and all CLI exit outcomes.
- `python3 -B line-4/check-36.py --live`: **250 tests passed in 16 suites**.
  Earlier sources were unchanged; test temporary directories were redirected
  into the authorized `test/scratch/` area. The new demo behaved as described.
- A read-only GET of `https://api.imd.fun/openapi.json` with User-Agent
  `Pepeolithic-DispatchCheck/36.0` returned 23,132 bytes matching the bundled
  capture. Five operations compared with zero findings. That real description
  has no dispatch pairs at the visited sites, so it verifies integration and
  unchanged behavior, not live discriminator behavior. No described endpoint
  was called. Evidence is in `line-4/check-results-36.json` and
  `line-4/live-openapi-36.json`.

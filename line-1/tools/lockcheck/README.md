# Lockcheck — shared tools, finite capacity

A two-worker plan can still reserve the same GPU twice. Lockcheck checks a
complete proposed schedule against shared renewable resource capacities, after
Plancheck validates durations, dependencies, worker overlap and the deadline.
It reports the exact peak usage and every conflicting interval with its active
tasks and excess units. It never executes task names or acquires actual locks.

From the repository root, Python standard library only:

```sh
python3 -B line-1/tools/lockcheck/lockcheck.py --demo
```

Observed: both workers fit the original three-minute plan, but GPU usage is two
against capacity one during minutes 1–3. Moving preview to minutes 3–5 removes
the conflict and still meets the five-minute budget. Demo exit 0 means the two
examples ran; inspect each example's `valid` value.

## Check your own plan

Keep the existing sibling `plancheck/` folder; it is the only runtime dependency.
Use the same task and full-plan schemas as Plancheck and these arguments:

```sh
python3 -B line-1/tools/lockcheck/lockcheck.py --tasks line-1/tools/lockcheck/tasks.json --plan line-1/tools/lockcheck/plan.json --limits line-1/tools/lockcheck/limits.json --workers 2 --budget 5
```

The included files are the conflicting demo, so this command intentionally exits
2. Exit 0 means a valid schedule with no resource conflict; 2 means schedule or
resource infeasibility; 1 means bad input or a read error. Invalid schedules
withhold all resource conclusions. Producer claims of optimality are ignored.

Limits format:

```json
{"capacities":{"gpu":1},"demands":{"render":{"gpu":1},"preview":{"gpu":1}}}
```

Every task must have an explicit demand mapping, even `{}` for no resources.
There are 1–64 resources, named with 1–100 nonblank characters; capacity and each
listed demand are positive integers at most one billion (booleans rejected).
Omit zero demands. Unknown resources, missing tasks and unknown tasks fail.
Demands larger than capacity are reported as conflicts, rather than schema errors.
There may be up to 500 tasks. Each input is an ordinary workspace-local JSON
file of at most 100 KB; duplicate keys and nonfinite numbers are refused.

A task reserves all its units for its entire half-open `[start, finish)` interval.
Reservations ending at a time can be reused immediately at that time. Adjacent
conflict rows may remain separate when the active task set changes. Times are
exact decimal strings in output, without floating-point tolerances or rounding.
Unused declared resources report peak zero. Resource names are opaque labels.

This checks a fixed schedule, and does not generate a resource-aware schedule,
reorder tasks, model partial-task reservations, reserve real hardware, enforce
calendars or certify actual runtime. A capacity is reusable after a task; it is
not a consumable budget. Caller estimates and declared requirements must be
complete. No network, coin, key, wallet, environment access or payment is needed.

## Verification

```sh
python3 -B line-1/tools/lockcheck/selftest.py
```

Tests include an independent minute-grid oracle on 200 seeded schedules, exact
decimal boundaries, multiple resources, whole-plan refusal, strict schemas,
input immutability and the file-input CLI. See `../../check-results-36.json`
for this round's actual local observations, which are not independent certification.

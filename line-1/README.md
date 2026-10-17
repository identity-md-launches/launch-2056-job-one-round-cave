# Line 1 — Paths Before Footsteps

## Latest piece: round 36 — The Shared Bowl

[Lockcheck](tools/lockcheck/README.md) checks shared renewable resource capacities
on a complete offline plan. Even when each worker is free, tasks can double-book
a GPU or workspace. It validates the whole schedule first, then reports exact
peak usage and conflicting intervals with the tasks responsible.

```sh
python3 -B line-1/tools/lockcheck/lockcheck.py --demo
```

Observed: the original two-worker schedule double-books one GPU during minutes
1–3; moving preview to minutes 3–5 clears the conflict and meets the budget.
Ten new tests pass, including 200 seeded schedules checked against a separate
minute-grid oracle; all fifteen Plancheck tests pass. Lockcheck checks supplied
full-task reservations, and does not reserve hardware or reschedule work.

A small ochre bowl with two charcoal pestles marks the shared resource. The
1254 × 1254 PNG is `artifacts/line-1/wall-v17.png` and identical continuing
`wall.png`; record 36 and its 512 × 512 JPEG are in `dist/line-1/`.
[Review](review-36.json) records dimensions, formats and visual limits;
all 1,564,725 pixels outside the shaped addition mask remain identical.

## Earlier piece: round 35 — The Smallest Crew

[Crewfit](tools/crewfit/README.md) proves the smallest crew, up to four workers,
that can meet a final budget and named intermediate handoffs. It uses Gateplan's
bounded exact search for each candidate count and returns a full checked plan.
An incomplete lower search yields a candidate rather than a false minimum.

```sh
python3 -B line-1/tools/crewfit/crewfit.py --demo
```

Observed: one worker cannot meet the four-minute budget; two finish at minute
4 and meet the handoff at minute 3. Seven tests pass, including 60 small graphs
compared with an independent minute-grid scheduler. Three ochre paths converge
on a chalk pebble on bare upper-right rock. The finished 1254 × 1254 wall is
`artifacts/line-1/wall-v16.png` and continuing `wall.png`; record 35 and its
512 × 512 JPEG are in `dist/line-1/`. [Review](review-35.json) records format,
preservation and visual limits.

## Earlier piece: round 34 — The Handoff Stones

[Gateplan](tools/gateplan/README.md) finds a shortest bounded offline schedule
that meets both a final budget and named intermediate handoff deadlines. It
searches intentional worker idle time and returns either a complete plan, a
proof of infeasibility, or an explicit state-limit refusal.

```sh
python3 -B line-1/tools/gateplan/gateplan.py --demo --workers 1 --budget 7
```

Observed: release and handoff finish by minute 3, then background work finishes
at minute 7. Six built-in checks and 120 independent small-graph oracle cases
passed. The new converging ochre stones sit on bare upper-right rock. The
finished 1254 × 1254 wall is `artifacts/line-1/wall-v15.png` and continuing
`wall.png`; record 34 and its 512 × 512 preview are in `dist/line-1/`.
[Review](review-34.json) records formats, preservation and visual limits.

## Earlier piece: round 32 — The Measured Gate

[Gatecheck](tools/gatecheck/README.md) checks named intermediate handoff
deadlines against a complete schedule already accepted by Plancheck. For each
gate it reports the latest finish among its named tasks and exact deadline
slack; it withholds milestone results when the full schedule is infeasible.

```sh
python3 -B line-1/tools/gatecheck/gatecheck.py --demo
```

Observed: the demo returns `valid: true`; the draft meets minute 7 exactly and
the handoff finishes one minute before its minute 10 deadline. Eight self-checks
and both valid and late-gate CLI examples pass. Estimates and worker
availability remain caller supplied; the tool does not predict actual runtime.

A small red-ochre gate and chalk pebble mark a named checkpoint. The finished
PNG is 1254 × 1254 at `artifacts/line-1/wall-v13.png`, with identical continuing
wall bytes at `wall.png`; record 32 and its 512 × 512 JPEG are in `dist/line-1/`.
[Review](review-32.json) records formats, dimensions and visual limits. All
1,556,141 pixels outside the addition patch are untouched. Pepe's two hands
and the inherited stencil each retain five digits. No writing or new hand was
added; no unmet visual requirement was observed.

## Earlier piece: round 31 — The Chosen Seed

[Goalslice](tools/goalslice/README.md) selects requested deliverables and every
declared prerequisite, then emits an exact planner-compatible task graph. Its
explanation names omitted work and shows which targets need each prerequisite.

```sh
python3 -B line-1/tools/goalslice/goalslice.py --demo --explain
```

Observed: the demo retains four tasks totaling 11 estimated work minutes and
omits two optional tasks totaling 12 work minutes. Ten new tests pass, including
200 seeded dependency closures, exact numeric round-trips, and integration with
Workplan and Plancheck. Plancheck's fifteen existing tests pass. The caller must
select every mandatory deliverable; effort totals do not guarantee a deadline.

A small ochre acorn and two leaves mark the choice. The 1254 × 1254 PNG is
`artifacts/line-1/wall-v12.png`, with identical continuing `wall.png`; record 31
and its 512 × 512 JPEG are in `dist/line-1/`. [Review](review-31.json) records
formats, dimensions and visual limits. All 1,559,736 protected pixels remain
unchanged. Pepe's two hands and the inherited stencil retain five digits each;
no hands or writing were added. The goal and older records remain unchanged.

## Earlier piece: round 30 — Room in the Nest

[Idlemap](tools/idlemap/README.md) validates a complete schedule, then explains
unused worker capacity and task waits after dependencies finish. Its exact
timeline distinguishes ready tasks waiting with spare capacity from tasks
waiting while all workers are busy. Intentional waiting remains valid.

```sh
python3 -B line-1/tools/idlemap/idlemap.py --demo
```

Observed: a seven-minute plan leaves seven worker-minutes idle; fixtures waits
ready for four minutes with a spare worker. Nine tests pass, including 120
seeded DAG schedules checked against an independent minute-grid oracle.
Plancheck's fifteen existing tests also pass. No task is executed, and the
report makes no claim of optimality or achievable speedup.

The new mark is a small ochre nest with two chalk eggs on bare rock to the
right of the sun. The 1254 × 1254 PNG is `artifacts/line-1/wall-v11.png`, with
identical continuing `wall.png`; record 30 and its 512 × 512 JPEG are in
`dist/line-1/`. [Review](review-30.json) records formats, dimensions, generation
prompts and limitations. All 1,556,136 pixels outside the addition patch remain
unchanged. Pepe's inherited hands and the hand stencil each retain five digits;
no hands or writing were added. The goal and older records remain unchanged.

### Tool directory

| Need | Tool |
| --- | --- |
| Select deliverables and all prerequisites | [Goalslice](tools/goalslice/README.md) |
| Create an offline plan | [Workplan](tools/workplan/README.md) |
| Resume from a progress snapshot | [Replan](tools/replan/README.md) |
| Find an exact bounded small integer plan | [Optplan](tools/optplan/README.md) |
| Independently validate a full schedule | [Plancheck](tools/plancheck/README.md) |
| Check intermediate handoff deadlines | [Gatecheck](tools/gatecheck/README.md) |
| Find a bounded plan meeting handoff deadlines | [Gateplan](tools/gateplan/README.md) |
| Prove the smallest crew meeting handoff deadlines | [Crewfit](tools/crewfit/README.md) |
| Explain graph slack and critical paths | [Slackmap](tools/slackmap/README.md) |
| Find ready work and impossibility bounds | [Frontier](tools/frontier/README.md) |
| Compare two validated full schedules | [Plancompare](tools/plancompare/README.md) |
| Check simultaneous duration caps in fixed worker order | [Capguard](tools/capguard/README.md) |
| Check shared resource capacity and double bookings | [Lockcheck](tools/lockcheck/README.md) |
| Explain idle capacity and ready-task waits | [Idlemap](tools/idlemap/README.md) |

Use each tool's README for its input contract and limitations. Replan's
remaining segments are not complete schedules for Plancheck, Plancompare,
Capguard or Idlemap. All tools are offline standard-library Python.

## Earlier piece: round 29 — The Beetle's Burden

[Capguard](tools/capguard/README.md) checks whether a validated offline plan
still meets a deadline when several task durations reach their supplied caps
together. It keeps worker assignments and order, removes idle gaps, and returns
an exact earliest capped schedule and a longest-path witness.

```sh
python3 -B line-1/tools/capguard/capguard.py --demo
```

Observed: the two-worker plan's baseline finish is 9 minutes. With simultaneous
caps on build and fixtures, its worst fixed-order finish is 10 minutes, exactly
meeting the 10-minute deadline. Nine local tests passed, including every
duration combination in a small four-task box. This depends on user-supplied
caps and continuous worker availability; it does not predict actual effort.

The new lower-left ochre beetle carries two pebbles beside the inherited leaves.
The 1254 × 1254 PNG is `artifacts/line-1/wall-v10.png`, identical to continuing
`wall.png`. Record 29 and its 512 × 512 JPEG are in `dist/line-1/`.
[Review](review-29.json) records dimensions, format and visual limits. Every
pixel outside the small addition mask is unchanged. Pepe's inherited hands and
the hand stencil each retain five digits; no new hands or writing were added.


## Earlier piece: round 28 — The Compared Leaves

[Plancompare](tools/plancompare/README.md) checks two complete schedules against
the same graph, workers and deadline before showing changes in task timing,
worker assignment, makespan and deadline margin. It uses exact decimal arithmetic
and refuses comparison if either schedule fails validation.

```sh
python3 -B line-1/tools/plancompare/plancompare.py --demo
```

Observed: moving fixtures to the second worker reduces finish from 7 to 5.
Eleven new tests pass, including 150 seeded plan pairs; all fifteen predecessor
Plancheck tests pass. The tool executes no work and does not prove optimality.

Two small ochre leaves mark the comparison. The finished 1254 × 1254 PNG is
`artifacts/line-1/wall-v9.png`, identical to continuing `wall.png`. Record 28
and its 512 × 512 JPEG are in `dist/line-1/`. [Review](review-28.json) records
formats, dimensions, visual limitations and the explicit JPEG placement choice.
All 1,550,520 pixels outside the addition patch are unchanged. Pepe's two hands
and the inherited hand stencil retain five digits each; no new hands or writing.
GOAL.md and older records remain unchanged.

## Earlier piece: round 25 — The Watchful Path

[Plancheck](tools/plancheck/README.md) independently checks a complete proposed
schedule against task estimates, dependencies, worker capacity and an external
deadline. It catches missing work, changed durations, early task starts,
overlapping workers and misleading finish claims. It uses exact decimal
arithmetic and never executes task labels.

```sh
python3 -B line-1/tools/plancheck/plancheck.py --demo
```

Observed: the valid example passes; a tampered early check fails for both a
dependency violation and a worker overlap. All 15 tests pass, including 150
seeded valid schedules and 150 damaged variants. Workplan and Optplan integration
examples pass. Existing planner source and the line goal are unchanged.

A worn ochre owl watches above the branching path. The final wall is
`artifacts/line-1/wall-v6.png`, with identical bytes at `wall.png`, both PNG,
1254 × 1254. Record 25 and its 512 × 512 JPEG are in `dist/line-1/`.
[Review](review-25.json) records dimensions, preservation and visual limitations;
[checks](check-results-25.json) records the local observations. No unmet visual
requirement was observed. All ancestral marks are preserved outside the addition
mask, including Pepe's five-digit hands and the five-digit handprint.

## Earlier piece: round 24 — The Patient Shortcut

[Optplan](tools/optplan/README.md) now considers intentional idle time. The
previous solver's claim that non-delay scheduling always contains an optimum
was false: a five-task fork/join job took 21 minutes in its search, although a
16-minute plan exists. The repaired search finds that plan and includes a
state limit that stops without making an optimality claim when exhausted.

```sh
python3 -B line-1/tools/optplan/optplan.py --idle-demo --workers 2
```

The new 10-test suite passes, including an independent minute-grid oracle on
120 seeded graphs and all 64 four-task DAGs under a fixed topological labeling.
Workplan and Replan remain unchanged and their checks pass. The line's one-line
goal is unchanged. No coin, chain call or task execution is needed.

A small ochre tortoise rests on bare rock above the sun: leaving room can let
two paths meet sooner. All previous marks remain pixel-identical. The final
1254 × 1254 PNG is `artifacts/line-1/wall-v5.png`, with identical continuing-wall
bytes at `artifacts/line-1/wall.png`. Record 24 and its 512 × 512 JPEG are in
`dist/line-1/`. [Review](review-24.json) records dimensions, visual checks and
the conflicting preview placement clauses; [check results](check-results-24.json)
record commands and observed results.

## Earlier piece: round 22 — A Path for the Late Snail

[Replan](tools/replan/README.md) resumes offline dependency planning from completed
and running work, keeps active tasks on their workers, and optionally adds a
margin to remaining estimates. Its documented demo finishes at minute 26 against
a 27-minute deadline; 14 tests pass, including 300 generated progress snapshots.
Workplan remains unchanged and its original self-test passes.

```sh
python3 -B line-1/tools/replan/replan.py --demo --workers 2 --budget 27
```

The new mark is an ochre snail finding a branch back to the path. The previous
painting, rock and framing were retained outside a small addition mask: 1,529,151
of 1,572,516 pixels are protected exactly. Original Pepe, hands, paths and sun
remain. [Review](review-22.json) records dimensions, hashes, visual observations,
the contradictory JPEG placement requirement, and check results.

- Required named output: `artifacts/line-1/wall-v3.png`, PNG, 1254 × 1254.
- Continuing wall: `artifacts/line-1/wall.png`, identical PNG bytes.
- Record: `dist/line-1/22.json`; preview: `dist/line-1/22.jpg`, JPEG, 512 × 512.

The number follows the instruction to count all 21 existing records, including
their placeholders. Older records and the one-line goal are untouched. No coin,
price, payment, or pool is needed for dependency planning.

## Original piece: round 01

Round 01 establishes offline dependency and deadline planning. The working piece is [Workplan](tools/workplan/README.md); its self-test passes and the two-worker demo takes 22 estimated minutes against a 25-minute budget.

## Wall and record

- `artifacts/line-1/wall.png`: PNG, 1254 × 1254 pixels, matching the supplied square cave dimensions.
- `dist/line-1/01.jpg`: JPEG, 512 × 512 pixels, generated from the finished wall with ffmpeg.
- `dist/line-1/01.json`: first numbered record, with the finished PNG's lowercase SHA-256 in its artifact URL.

The first mark shows a heavy-lidded, wide-mouthed Pepe joining ochre stepping stones into paths toward a chalk sun. Charcoal and earth pigments show the stone through their worn texture. The supplied cave was the edit reference; rock, framing, lighting, and cracks remain recognizable. There were no ancestral marks to preserve.

Visual review: both open hands have five digits each (four fingers and one thumb). No hand stencils, words, numbers, captions, border, logos, or watermarks are visible. The painting is flat pigment on the supplied cave surface. The base cave's small glowing fissures remain from the input. No unmet visual requirements were observed; generative editing can subtly alter rock texture, so pixel-exact preservation of all untouched stone is not claimed.

Only one image draft was generated and kept. The installed image-import tool copied it directly to the declared wall path; ffmpeg created the required JPEG without another saved preview.

## Run

```sh
python3 line-1/tools/workplan/workplan.py --demo --workers 2 --budget 25
```

For input format, limits, test command, and possible next steps, see the tool README. The image is a metaphor; the tool is useful independently of this wall.

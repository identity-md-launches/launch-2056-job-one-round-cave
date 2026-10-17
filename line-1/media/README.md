# Wall assembly for rounds 22–23

## Round 32 addition

`finish-wall-32.cjs` reads the inherited `wall.png` and the image editor's
`wall-v13.png`, keeps only a feathered lower-right gate patch, and writes the
final `wall-v13.png`, identical continuing `wall.png`, and
`dist/line-1/32.jpg`. It uses the unchanged local PNG codec and vendored JPEG
encoder. The PNG round trip passed; all pixels outside the edit mask remained
identical. Its measurements are in `../media-check-32.json`, with visual
observations and limitations in `../review-32.json`.

One-time command: `node line-1/media/finish-wall-32.cjs`. The generated edit is
overwritten by the assembled wall; rerunning after completion does not replay
the original edit.

## Round 30 addition

`finish-wall-30.cjs` uses the unchanged local PNG codec and vendored JPEG
encoder. It reads inherited `wall-v10.png` and the image editor's repaired
nest at `wall-v11.png`, then retains only the new bare-rock patch with a
16-pixel feather. It writes final `wall-v11.png`, identical `wall.png`,
`dist/line-1/30.jpg`, and `../media-check-30.json`. Its one-time command is
`node line-1/media/finish-wall-30.cjs`. The generated draft is overwritten;
rerunning is not a replay of generation. No media code is a Python tool
dependency. The final visual review is recorded in `../review-30.json`.

## Round 26 addition

`finish-wall-26.cjs` uses the inherited inspected codec and JPEG encoder. It
copies only a feathered 120 × 118 bare-rock rectangle containing the image
generator's balance stones, preserving every pixel outside it. The final
1254px RGB PNG and 512px JPEG were inspected; format, dimensions, byte counts,
preservation and visual limitations are recorded in `../review-26.json`.

One-time command: `node line-1/media/finish-wall-26.cjs`. Requires inherited
`wall-v6.png` and the raw generated edit at `wall-v7.png`. Overwrites the edit
with the finished wall, also writes `wall.png` and `dist/line-1/26.jpg`.
The generated raw edit is not retained; rerunning on the finished wall does
not replay generation. This helper is independent of Slackmap's runtime.

## Round 24 addition

`finish-wall-24.cjs` reuses this codec without changing earlier assembly code.
The installed image generator painted a tortoise on bare upper-right rock.
The assembler copied only its feathered rectangle, retaining every ancestral
mark and all 1,548,141 pixels outside that mask exactly. The final PNG and JPEG
were visually inspected; [review](../review-24.json) and
[measurements](../media-check-24.json) record the results.

The one-time assembly command was:

```sh
node line-1/media/finish-wall-24.cjs
```

It requires the inherited `artifacts/line-1/wall-v4.png` and the generated edit
at `artifacts/line-1/wall-v5.png`. It overwrites the latter with the finished
wall, writes identical bytes to `wall.png`, and creates `dist/line-1/24.jpg`.
The raw edit is not retained; running it after completion is not a replay of
generation. This script is media preparation, not a planner dependency.

## Earlier rounds

The installed image tool edited the inherited 1254 × 1254 PNG. Round 22 added a
red-ochre snail and trail; round 23 adds three small stepping stones and a
chalk five-digit handprint to previously bare stone. No text or new frog was
added.

`finish-wall.cjs` takes the previous wall and the generated edit, copies only
small masked areas containing the addition, and keeps every other pixel from
the preceding wall. It writes identical PNG bytes to both input paths and a
512 × 512 JPEG to the third argument. It uses Node built-ins and the vendored
encoder, needs no install/network, and is **not** part of the Python planner.

The one-time command used before the old wall was replaced was:

```sh
node line-1/media/finish-wall.cjs artifacts/line-1/wall.png artifacts/line-1/wall-v3.png artifacts/line-1/22.jpg
```

The JPEG was then moved to `dist/line-1/22.jpg` to satisfy the explicit instruction
to put a numbered preview beside the JSON. The source wall and edit are not kept
as additional images. Running the assembly again on the two final identical
PNGs is not a replay of image generation; it only re-encodes the finished wall.

`../media-check.json` records the actual assembly metrics. The PNG passed a
lossless decode/encode round trip; a comparison against the original Git blob
confirmed exact preservation outside the mask. Both final image sizes were
verified and both formats were visually inspected. The lighting, cracks,
framing, old Pepe, old paths and sun remain; the new pigment is uneven and worn.
Both ancestral hands retain their five digits. No unmet visual requirement was
observed. Subjective visual review is an agent observation, not certification.

The brief's JPEG placement clauses conflict. We retained the explicitly named
record-adjacent JPEG; that is the sole new picture outside `artifacts/`.

The JPEG encoder is the complete unmodified source from jpeg-js v0.4.4:

- <https://raw.githubusercontent.com/jpeg-js/jpeg-js/v0.4.4/lib/encoder.js>
- <https://raw.githubusercontent.com/jpeg-js/jpeg-js/v0.4.4/LICENSE>

Source attribution and license text are preserved in `jpeg-encoder.cjs` and
`JPEG-JS-LICENSE`. No submodule or external runtime dependency is used. This
assembly script is intentionally limited to these trusted opaque, noninterlaced,
8-bit RGB/RGBA 1254-pixel PNG inputs; it is not a general untrusted-image parser.

## Round 25 addition

`finish-wall-25.cjs` uses the inherited codec and JPEG encoder to retain only
the image editor's new owl on bare upper rock, with a feathered rectangle and
an exclusion ellipse protecting the old red path stone. The final 1254px PNG
and 512px JPEG were visually inspected; dimensions and preservation are recorded
in `../media-check-25.json` and `../review-25.json`.

One-time assembly command: `node line-1/media/finish-wall-25.cjs`. It requires
the preceding `wall-v5.png` and the raw generated edit at `wall-v6.png`, which
it overwrites with the finished wall. It also writes `wall.png` and
`dist/line-1/25.jpg`. The raw edit is not retained; rerunning on the finished
wall is not a replay of generation. This helper is not a worker-tool dependency.

## Round 36 addition

`finish-wall-36.cjs` uses the unchanged local PNG codec and JPEG encoder. It
reads inherited `wall-v16.png` and the image tool's `wall-v17.png`, retaining
only the new bowl ellipse and two pestle strokes with feathered edges. It
writes `wall-v17.png`, identical continuing `wall.png`, `dist/line-1/36.jpg`
and `../media-check-36.json`. All 1,564,725 pixels outside the shaped mask
remain unchanged; PNG round-trip and image structure checks passed.

One-time assembly command: `node line-1/media/finish-wall-36.cjs`. The raw
generated edit is overwritten; rerunning does not replay generation. The
completed PNG and JPEG were inspected; see `../review-36.json` for dimensions,
formats, visual observations and limits. This is media preparation only;
Lockcheck has no dependency on media code or image files.

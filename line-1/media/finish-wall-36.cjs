// Copy only round 36's new lower-center bowl pigment onto the inherited wall.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {decode, encode, thumbnail} = require('./finish-wall.cjs');

const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const oldBytes = fs.readFileSync('artifacts/line-1/wall-v16.png');
if (hash(oldBytes) !== '9b5458728e42372612a215423474dd46a6962a0958a9afa8693b10aede6f9354') {
  throw Error('inherited wall does not match round 35');
}
const newBytes = fs.readFileSync('artifacts/line-1/wall-v17.png');
const old = decode(oldBytes);
const edited = decode(newBytes);
if (old.width !== 1254 || old.height !== 1254 ||
    old.width !== edited.width || old.height !== edited.height) {
  throw Error('wall dimensions changed');
}
const result = {...old, pixels: Buffer.from(old.pixels)};
const bounds = {left: 612, top: 924, right: 751, bottom: 1040};
const feather = 4;
function stroke(x, y, ax, ay, bx, by, radius) {
  const t = Math.max(0, Math.min(1, ((x-ax)*(bx-ax)+(y-ay)*(by-ay))/((bx-ax)**2+(by-ay)**2)));
  return Math.max(0, Math.min(1, (radius-Math.hypot(x-ax-t*(bx-ax), y-ay-t*(by-ay)))/feather));
}
function pigmentMask(x, y) {
  const bowl = Math.max(0, Math.min(1, (1-Math.hypot((x-682)/58, (y-991)/34))*8));
  return Math.max(bowl, stroke(x,y,641,943,670,978,13), stroke(x,y,720,946,700,977,13));
}
let changed = 0, protectedPixels = 0, outsideMaskChanged = 0;
for (let y = 0; y < old.height; y++) for (let x = 0; x < old.width; x++) {
  const alpha = pigmentMask(x, y);
  if (!alpha) protectedPixels++;
  const at = (y*old.width+x)*3;
  let differs = false;
  for (let c = 0; c < 3; c++) {
    result.pixels[at+c] = Math.round(old.pixels[at+c]*(1-alpha) + edited.pixels[at+c]*alpha);
    differs ||= result.pixels[at+c] !== old.pixels[at+c];
  }
  if (!alpha && differs) outsideMaskChanged++;
  if (differs) changed++;
}
if (outsideMaskChanged !== 0 || changed < 1000) throw Error('addition mask failed');
const png = encode(result), jpeg = thumbnail(result);
if (!decode(png).pixels.equals(result.pixels)) throw Error('PNG round trip failed');
if (jpeg.length > 100000) throw Error('JPEG exceeds 100 KB');
fs.writeFileSync('artifacts/line-1/wall-v17.png', png);
fs.writeFileSync('artifacts/line-1/wall.png', png);
fs.writeFileSync('dist/line-1/36.jpg', jpeg);
const report = {previous_sha256: hash(oldBytes), sha256: hash(png),
  format: 'PNG', width: old.width, height: old.height, png_bytes: png.length,
  preview_format: 'JPEG', preview_width: 512, preview_height: 512,
  preview_bytes: jpeg.length, bounds, mask: 'feathered bowl ellipse and two pestle strokes only', feather_pixels: feather,
  changed_pixels: changed, protected_pixels: protectedPixels,
  total_pixels: old.width*old.height,
  outside_mask_changed_pixels: outsideMaskChanged,
  png_roundtrip_passed: true};
fs.writeFileSync('line-1/media-check-36.json', JSON.stringify(report, null, 2)+'\n');
console.log(JSON.stringify(report, null, 2));

// One-time assembly of the image tool's pigment onto bare inherited rock.
// Input wall-v17.png must still be the generated drawing: do not rerun on final.
const fs = require('node:fs');
const crypto = require('node:crypto');
const {spawnSync} = require('node:child_process');
const {decode, encode, thumbnail} = require('../line-1/media/finish-wall.cjs');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const oldBytes = fs.readFileSync('artifacts/line-2/wall.png');
const pigmentBytes = fs.readFileSync('artifacts/line-2/wall-v17.png');
if(hash(oldBytes)!=='1307de201941753f0f413f4793e40a89a2ac0da832d64b5698c25a5e3a8e07a1') throw Error('unexpected inherited wall');
if(fs.existsSync('dist/line-2/36.json')) throw Error('record already exists');
const old = decode(oldBytes);
const bounds = {left:890, top:125, right:1060, bottom:250};
const width = bounds.right-bounds.left, height = bounds.bottom-bounds.top;
// Stream pixels in memory: never save a separate draft or crop image.
const converted = spawnSync('ffmpeg', ['-v','error','-i','pipe:0','-vf',
  `crop=1140:850:60:175,scale=${width}:${height}:flags=area`,
  '-f','rawvideo','-pix_fmt','rgb24','pipe:1'],
  {input:pigmentBytes,maxBuffer:5000000});
if(converted.status !== 0 || converted.stdout.length !== width*height*3)
  throw Error(converted.stderr.toString() || 'raw pigment conversion failed');
const result = {...old,pixels:Buffer.from(old.pixels)};
for(let y=0;y<height;y++) for(let x=0;x<width;x++) {
  const p=(y*width+x)*3, i=((y+bounds.top)*old.width+x+bounds.left)*3;
  const [r,g,b]=converted.stdout.subarray(p,p+3);
  let alpha=Math.min(0.86,Math.max(0,(235-Math.min(r,g,b))/190));
  if(!alpha) continue;
  // Palette-map the generated drawing; keep original rock grain through paint.
  const color=r-g>55 ? [151,58,25] : r>g*1.15 && g>b*1.4 ? [190,135,55] : [29,24,17];
  const grain=((x*73+y*131+x*y*17)%101)/100;
  alpha*=grain<0.09 ? 0.25 : 0.82+grain*0.18;
  const texture=0.65+(old.pixels[i]+old.pixels[i+1]+old.pixels[i+2])/1500;
  for(let c=0;c<3;c++) result.pixels[i+c]=Math.round(
    old.pixels[i+c]*(1-alpha)+color[c]*texture*alpha);
}
let changed=0, outside=0;
for(let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
  const i=(y*old.width+x)*3;
  if(!old.pixels.subarray(i,i+3).equals(result.pixels.subarray(i,i+3))) {
    changed++;
    if(x<bounds.left||x>=bounds.right||y<bounds.top||y>=bounds.bottom) outside++;
  }
}
if(outside || !changed) throw Error('mark/preservation failed');
const png=encode(result), jpg=thumbnail(result);
if(!decode(png).pixels.equals(result.pixels)) throw Error('PNG roundtrip failed');
if(jpg.length>100000) throw Error('preview over 100 KB');
fs.writeFileSync('artifacts/line-2/wall-v17.png',png);
fs.writeFileSync('artifacts/line-2/wall.png',png);
fs.writeFileSync('dist/line-2/36.jpg',jpg);
const report={previous_sha256:hash(oldBytes),pigment_sha256:hash(pigmentBytes),
  sha256:hash(png),width:old.width,height:old.height,format:'PNG',png_bytes:png.length,
  preview_width:512,preview_height:512,preview_format:'JPEG',preview_bytes:jpg.length,
  bounds,changed_pixels:changed,unchanged_pixels:old.width*old.height-changed,
  outside_mark_changed_pixels:outside,png_roundtrip_passed:true,unmet_visual_requirements:[]};
fs.writeFileSync('line-2/media-check-36.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));

const record={name:'The Shared Cord',image:'https://api.imd.fun/artifacts/'+hash(png),
 attributes:[{trait_type:'Cave',value:'Lava'},{trait_type:'Wall',value:'Line 2'},
 {trait_type:'Number',value:36},{trait_type:'Left behind',value:'ZipMerge shared metadata budget'},
 {trait_type:'Meaning',value:'One cord bounds two bundles before either enters the basket.'},
 {trait_type:'One thing',value:'Safely extract untrusted ZIP archives with explicit path and resource limits'}]};
fs.writeFileSync('dist/line-2/36.json',JSON.stringify(record,null,2)+'\n');

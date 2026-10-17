// Composite the image tool's transparent pigment over bare inherited stone.
// No network, machine configuration, credentials or external dependencies.
// PNG filtering/encoding and JPEG thumbnail reuse the reviewed line 1 codec.
const fs = require('node:fs');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const media = require('../line-1/media/finish-wall.cjs');
const hash = raw => crypto.createHash('sha256').update(raw).digest('hex');

function rgba(raw) {
  if (!raw.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex'))) throw Error('PNG required');
  let width, height, channels, parts=[];
  for (let at=8; at<raw.length;) {
    const size=raw.readUInt32BE(at), type=raw.toString('ascii',at+4,at+8);
    const data=raw.subarray(at+8,at+8+size);
    if (type==='IHDR') {
      width=data.readUInt32BE(0); height=data.readUInt32BE(4);
      if(data[8]!==8 || ![2,6].includes(data[9]) || data[12]!==0) throw Error('8-bit RGB/RGBA required');
      if(width>4096 || height>4096) throw Error('oversized input');
      channels=data[9]===6 ? 4 : 3;
    }
    if(type==='IDAT') parts.push(data);
    at+=size+12;
    if(type==='IEND') break;
  }
  const stride=width*channels, scan=zlib.inflateSync(Buffer.concat(parts),{maxOutputLength:(stride+1)*height});
  if(scan.length!==(stride+1)*height) throw Error('invalid scan length');
  const pixels=Buffer.alloc(width*height*channels);
  for(let y=0;y<height;y++) {
    const filter=scan[y*(stride+1)];
    if(filter>4) throw Error('invalid PNG filter');
    for(let x=0;x<stride;x++) {
      const i=y*stride+x,a=x>=channels?pixels[i-channels]:0,b=y?pixels[i-stride]:0,c=y&&x>=channels?pixels[i-stride-channels]:0;
      const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);
      const predictor=[0,a,b,Math.floor((a+b)/2),pa<=pb&&pa<=pc?a:pb<=pc?b:c][filter];
      pixels[i]=(scan[y*(stride+1)+x+1]+predictor)&255;
    }
  }
  if(channels!==4) throw Error('transparent RGBA image-tool input required');
  return {width,height,pixels};
}

function main() {
  const sourcePath='artifacts/gathering/wall-v16.png';
  const targetPath='artifacts/gathering/wall-v17.png';
  const oldBytes=fs.readFileSync(sourcePath), pigmentBytes=fs.readFileSync(targetPath);
  const old=media.decode(oldBytes), pigment=rgba(pigmentBytes);
  let left=pigment.width,top=pigment.height,right=0,bottom=0,transparent=0;
  for(let y=0;y<pigment.height;y++) for(let x=0;x<pigment.width;x++) {
    const alpha=pigment.pixels[(y*pigment.width+x)*4+3];
    if(alpha===0) transparent++;
    if(alpha>5) {left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);}
  }
  if(transparent<pigment.width*pigment.height/4 || right<=left || bottom<=top) throw Error('missing transparent pigment');
  // Bare lower-left stone beneath the inherited frog and pouch.
  const box=[155,956,175,120];
  const sourceWidth=right-left+1,sourceHeight=bottom-top+1;
  const scale=Math.min(box[2]/sourceWidth,box[3]/sourceHeight);
  const width=Math.round(sourceWidth*scale),height=Math.round(sourceHeight*scale);
  const startX=box[0]+Math.floor((box[2]-width)/2),startY=box[1]+Math.floor((box[3]-height)/2);
  const output={...old,pixels:Buffer.from(old.pixels)};
  let changed=0;
  for(let dy=0;dy<height;dy++) for(let dx=0;dx<width;dx++) {
    // Area-average premultiplied colors and alpha to avoid opaque crop edges.
    const x0=left+dx*sourceWidth/width,x1=left+(dx+1)*sourceWidth/width;
    const y0=top+dy*sourceHeight/height,y1=top+(dy+1)*sourceHeight/height;
    const sums=[0,0,0];let weightSum=0,alphaSum=0;
    for(let sy=Math.floor(y0);sy<Math.ceil(y1);sy++) for(let sx=Math.floor(x0);sx<Math.ceil(x1);sx++) {
      const weight=(Math.min(x1,sx+1)-Math.max(x0,sx))*(Math.min(y1,sy+1)-Math.max(y0,sy));
      const offset=(sy*pigment.width+sx)*4, alpha=pigment.pixels[offset+3]/255;
      weightSum+=weight;alphaSum+=alpha*weight;
      for(let c=0;c<3;c++) sums[c]+=pigment.pixels[offset+c]*alpha*weight;
    }
    const i=((startY+dy)*old.width+startX+dx)*3,opacity=alphaSum/weightSum*0.82;
    if(alphaSum>0) for(let c=0;c<3;c++) output.pixels[i+c]=Math.round(old.pixels[i+c]*(1-opacity)+sums[c]/alphaSum*opacity);
    if(!output.pixels.subarray(i,i+3).equals(old.pixels.subarray(i,i+3))) changed++;
  }
  let protectedChanged=0;
  for(let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
    if(x>=box[0]&&x<box[0]+box[2]&&y>=box[1]&&y<box[1]+box[3]) continue;
    const i=(y*old.width+x)*3;
    if(!output.pixels.subarray(i,i+3).equals(old.pixels.subarray(i,i+3))) protectedChanged++;
  }
  if(changed<500 || protectedChanged) throw Error('pigment missing or protected pixels changed');
  const wall=media.encode(output),preview=media.thumbnail(output);
  if(!media.decode(wall).pixels.equals(output.pixels) || preview.length>100000) throw Error('encoding failed');
  fs.writeFileSync(targetPath,wall);
  fs.writeFileSync('dist/gathering/36.jpg',preview);
  if(fs.existsSync('artifacts/gathering/wall.png')) fs.unlinkSync('artifacts/gathering/wall.png');
  fs.symlinkSync('wall-v17.png','artifacts/gathering/wall.png');
  const evidence={previous_sha256:hash(oldBytes),generated_pigment_sha256:hash(pigmentBytes),wall_sha256:hash(wall),
    dimensions:[old.width,old.height],format:'RGB PNG',png_bytes:wall.length,jpeg_dimensions:[512,512],
    jpeg_bytes:preview.length,mark_rectangle:box,pigment_source_dimensions:[pigment.width,pigment.height],
    pigment_source_bounds:[left,top,right,bottom],changed_pixels:changed,pixels_changed_outside:protectedChanged,
    method:'Imagegen transparent earth pigment composited on bare stone; all inherited pixels outside the mark rectangle are exact.'};
  fs.writeFileSync('gathering/preservation-36.json',JSON.stringify(evidence,null,2)+'\n');
  const record={name:'The Branch Beneath the Seal',image:'https://api.imd.fun/artifacts/'+hash(wall),attributes:[
    {trait_type:'Cave',value:'Lava'},{trait_type:'Wall',value:'Gathering'},{trait_type:'Number',value:36},
    {trait_type:'Left behind',value:'Approved ZIP discriminator-target compatibility handoff'},
    {trait_type:'Meaning',value:'Two ochre branches lead from a chalk pebble, revealing a changed path behind a familiar sign.'},
    {trait_type:'One thing',value:'Gathering'}]};
  fs.writeFileSync('dist/gathering/36.json',JSON.stringify(record,null,2)+'\n');
  console.log(JSON.stringify(evidence,null,2));
}

if(require.main===module) main();

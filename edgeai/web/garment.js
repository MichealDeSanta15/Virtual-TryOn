'use strict';
// A selected catalog photo is SOURCE only. garmentId stays null until extraction.
let garmentSourceId=null, garmentPreparationId=null, garmentVersion=0, garmentSourceImage=null;
let garmentEraseMode=false, garmentPainting=false, garmentPrevious=null;
const garmentMaskCanvas=document.createElement('canvas'), garmentMaskContext=garmentMaskCanvas.getContext('2d');
const garmentEditor=$('garmentEditor'), garmentEditorContext=garmentEditor.getContext('2d');
function invalidateGarment(){
 garmentVersion++;garmentId=null;garmentPreparationId=null;
 $('garmentReviewed').checked=false;$('garmentReviewed').disabled=true;
 $('downloadGarment').disabled=true;$('garmentPreview').hidden=true;
 return garmentVersion;
}
function redrawGarment(){
 if(!garmentSourceImage)return;
 garmentEditorContext.clearRect(0,0,garmentEditor.width,garmentEditor.height);
 garmentEditorContext.drawImage(garmentSourceImage,0,0);
 const overlay=document.createElement('canvas');overlay.width=garmentEditor.width;overlay.height=garmentEditor.height;
 const o=overlay.getContext('2d');o.drawImage(garmentMaskCanvas,0,0);o.globalCompositeOperation='source-in';o.fillStyle='#adff69';o.fillRect(0,0,overlay.width,overlay.height);
 garmentEditorContext.save();garmentEditorContext.globalAlpha=.48;garmentEditorContext.drawImage(overlay,0,0);garmentEditorContext.restore();
}
async function setGarmentSource(key,category=null){
 const version=invalidateGarment();garmentSourceId=key;garmentSourceImage=null;
 if(category)$('category').value=category;
 updateCategoryUI();$('garmentEmpty').hidden=true;
 $('garmentPrepStatus').textContent='Loading reference. The source model photo will not be used directly.';
 $('extractGarment').disabled=true;$('applyGarmentMask').disabled=true;
 garmentEditorContext.clearRect(0,0,garmentEditor.width,garmentEditor.height);
 const image=await assetImage(key);if(version!==garmentVersion)return;
 garmentSourceImage=image;garmentEditor.width=garmentMaskCanvas.width=image.width;
 garmentEditor.height=garmentMaskCanvas.height=image.height;
 garmentMaskContext.clearRect(0,0,image.width,image.height);redrawGarment();
 $('extractGarment').disabled=false;$('applyGarmentMask').disabled=false;
 runGarmentPreparation().catch(e=>{$('garmentPrepStatus').textContent=e.message;toast(e.message);});
}
function garmentCategoryChanged(){
 invalidateGarment();
 if(garmentSourceId&&!garmentSourceImage){setGarmentSource(garmentSourceId).catch(e=>toast(e.message));return;}
 if(garmentSourceImage)runGarmentPreparation().catch(e=>{$('garmentPrepStatus').textContent=e.message;toast(e.message);});
}
async function runGarmentPreparation(mask=null){
 if(!garmentSourceId||!garmentSourceImage)throw Error('Choose a garment reference first');
 const version=invalidateGarment(),source=garmentSourceId,category=$('category').value;
 $('garmentPrepStatus').textContent=mask?'Applying garment-only selection…':'Extracting clothing on CPU. Removing model/body/background; no generative fill…';
 try{const job=await api('/api/garments/prepare',{method:'POST',body:{garment:source,category,mask}});
 await pollGarmentPreparation(job.id,version);}catch(e){if(version===garmentVersion)throw e;}
}
async function pollGarmentPreparation(id,version){
 if(version!==garmentVersion)return;
 try{
  const job=await api('/api/garments/prepare/'+id);
  if(version!==garmentVersion)return;
  if(job.state==='failed'||job.state==='cancelled'){
   $('garmentPrepStatus').textContent=(job.error||'Extraction cancelled')+' No original-photo fallback. Paint the reference mask manually and Apply.';
   $('garmentEditPanel').open=true;return;
  }
  if(job.state!=='done'){setTimeout(()=>pollGarmentPreparation(id,version),900);return;}
  const result=job.result;
  const [mask,photo]=await Promise.all([assetImage(result.mask),api('/api/assets/'+result.garment)]);
  if(version!==garmentVersion)return;
  garmentMaskContext.globalCompositeOperation='source-over';garmentMaskContext.clearRect(0,0,garmentMaskCanvas.width,garmentMaskCanvas.height);
  garmentMaskContext.drawImage(mask,0,0);
  const pixels=garmentMaskContext.getImageData(0,0,garmentMaskCanvas.width,garmentMaskCanvas.height);
  for(let i=0;i<pixels.data.length;i+=4){pixels.data[i+3]=pixels.data[i]>127?255:0;pixels.data[i]=pixels.data[i+1]=pixels.data[i+2]=255;}
  garmentMaskContext.putImageData(pixels,0,0);redrawGarment();
  if(imageURLs.has('garmentPreview'))URL.revokeObjectURL(imageURLs.get('garmentPreview'));
  const url=URL.createObjectURL(photo);imageURLs.set('garmentPreview',url);$('garmentPreview').src=url;$('garmentPreview').hidden=false;
  garmentId=result.garment;garmentPreparationId=id;
  $('garmentReviewed').disabled=false;$('downloadGarment').disabled=false;
  $('garmentPrepStatus').textContent='Garment-only preview ready. '+(result.metadata.warnings||[]).join(' ');
 }catch(e){
  if(version!==garmentVersion)return;
  $('garmentPrepStatus').textContent='Could not finish extraction: '+e.message+'. Retry extraction or apply a manual mask.';
  $('garmentEditPanel').open=true;
 }
}
$('extractGarment').onclick=safe(()=>runGarmentPreparation());
$('garmentPaint').onclick=()=>{garmentEraseMode=false;$('garmentPaint').classList.add('selected');$('garmentErase').classList.remove('selected');};
$('garmentErase').onclick=()=>{garmentEraseMode=true;$('garmentErase').classList.add('selected');$('garmentPaint').classList.remove('selected');};
function referenceEdited(){invalidateGarment();$('garmentPrepStatus').textContent='Reference mask changed. Apply corrected selection, then review the new preview.';}
$('garmentClear').onclick=()=>{if(!garmentSourceImage)return;referenceEdited();garmentMaskContext.clearRect(0,0,garmentMaskCanvas.width,garmentMaskCanvas.height);redrawGarment();};
function garmentStroke(e){
 if(!garmentPainting||!garmentSourceImage)return;e.preventDefault();
 const rect=garmentEditor.getBoundingClientRect();const pt=[(e.clientX-rect.left)*garmentEditor.width/rect.width,(e.clientY-rect.top)*garmentEditor.height/rect.height];
 const c=garmentMaskContext;c.globalCompositeOperation=garmentEraseMode?'destination-out':'source-over';c.strokeStyle='white';c.fillStyle='white';c.lineWidth=Number($('garmentBrush').value)*garmentEditor.width/rect.width;c.lineCap='round';c.lineJoin='round';
 c.beginPath();c.moveTo(...(garmentPrevious||pt));c.lineTo(...pt);c.stroke();
 if(!garmentPrevious){c.beginPath();c.arc(pt[0],pt[1],c.lineWidth/2,0,Math.PI*2);c.fill();}
 garmentPrevious=pt;redrawGarment();
}
garmentEditor.onpointerdown=e=>{if(!garmentSourceImage)return;referenceEdited();garmentPainting=true;garmentPrevious=null;garmentEditor.setPointerCapture(e.pointerId);garmentStroke(e);};
garmentEditor.onpointermove=garmentStroke;
['pointerup','pointercancel'].forEach(name=>garmentEditor.addEventListener(name,()=>{garmentPainting=false;garmentPrevious=null;}));
$('applyGarmentMask').onclick=safe(async()=>{
 if(!garmentSourceImage)throw Error('Choose a reference first');
 if(!garmentMaskContext.getImageData(0,0,garmentMaskCanvas.width,garmentMaskCanvas.height).data.some((v,i)=>i%4===3&&v>127))throw Error('Paint the garment to keep before applying');
 const version=garmentVersion;const c=document.createElement('canvas');c.width=garmentMaskCanvas.width;c.height=garmentMaskCanvas.height;
 const x=c.getContext('2d');x.fillStyle='black';x.fillRect(0,0,c.width,c.height);x.drawImage(garmentMaskCanvas,0,0);
 const blob=await new Promise(resolve=>c.toBlob(resolve,'image/png'));const key=await upload(blob,true);
 if(version!==garmentVersion)return;await runGarmentPreparation(key);
});
$('downloadGarment').onclick=safe(()=>download(garmentId,'form-extracted-garment.png'));

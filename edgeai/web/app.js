'use strict';
const $=id=>document.getElementById(id);
let token=sessionStorage.getItem('edgeai_token')||'', personId=null, garmentId=null, personImage=null, currentJob=null, lastResult=null, erase=false, painting=false, cameraMode=false, previewURL=null;
const maskCanvas=document.createElement('canvas'), maskCtx=maskCanvas.getContext('2d'), ctx=$('editor').getContext('2d');
let pollTimer=null, statusTimer=null, maskSettingsVersion=0;
const imageURLs=new Map();
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('toast').hidden=true,9500);}
async function api(path,options={}){
 const headers=new Headers(options.headers||{});headers.set('Authorization','Bearer '+token);
 if(options.body&&!(options.body instanceof FormData)){headers.set('Content-Type','application/json');options.body=JSON.stringify(options.body);}
 const r=await fetch(path,{...options,headers});
 if(!r.ok){let d=await r.json().catch(()=>({detail:r.statusText}));throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail));}
 if(r.status===204)return null;
 return (r.headers.get('content-type')||'').includes('json')?r.json():r.blob();
}
async function upload(blob,mask=false){const fd=new FormData();fd.append('file',blob,'image.png');return (await api('/api/assets?mask='+mask,{method:'POST',body:fd})).id;}
function loadImage(url){return new Promise((resolve,reject)=>{const i=new Image();i.onload=()=>resolve(i);i.onerror=()=>reject(Error('Could not decode image'));i.src=url;});}
async function assetImage(key){const b=await api('/api/assets/'+key);const u=URL.createObjectURL(b);try{return await loadImage(u);}finally{URL.revokeObjectURL(u);}}
async function showAsset(id,key){const blob=await api('/api/assets/'+key);if(imageURLs.has(id))URL.revokeObjectURL(imageURLs.get(id));const u=URL.createObjectURL(blob);imageURLs.set(id,u);$(id).src=u;$(id).hidden=false;}
async function normalize(file){if(!file)throw Error('Choose an image first');if(file.size>15*1024**2)throw Error('Image exceeds 15 MB');const u=URL.createObjectURL(file);try{const im=await loadImage(u);const c=document.createElement('canvas');const s=Math.min(1,1600/Math.max(im.width,im.height));c.width=Math.round(im.width*s);c.height=Math.round(im.height*s);c.getContext('2d').fillStyle='white';c.getContext('2d').fillRect(0,0,c.width,c.height);c.getContext('2d').drawImage(im,0,0,c.width,c.height);return await new Promise(r=>c.toBlob(r,'image/png'));}finally{URL.revokeObjectURL(u);}}
function redraw(){if(!personImage)return;ctx.clearRect(0,0,$('editor').width,$('editor').height);ctx.drawImage(personImage,0,0);ctx.save();ctx.globalAlpha=.48;ctx.drawImage(maskCanvas,0,0);ctx.restore();}
async function setPerson(id){personId=id;personImage=await assetImage(id);$('editor').width=maskCanvas.width=personImage.width;$('editor').height=maskCanvas.height=personImage.height;maskCtx.clearRect(0,0,maskCanvas.width,maskCanvas.height);$('personEmpty').hidden=true;$('editorWrap').hidden=false;$('personSize').textContent=personImage.width+' × '+personImage.height;redraw();switchMode(false);}
<<<<<<< HEAD
function switchMode(camera){cameraMode=camera;$('cameraArea').hidden=!camera;$('photoArea').hidden=camera;$('cameraTab').classList.toggle('selected',camera);$('photoTab').classList.toggle('selected',!camera);if(camera&&token)applyCameraOrientation().catch(e=>toast(e.message));}
=======
function switchMode(camera){cameraMode=camera;$('cameraArea').hidden=!camera;$('photoArea').hidden=camera;$('cameraTab').classList.toggle('selected',camera);$('photoTab').classList.toggle('selected',!camera);}
>>>>>>> origin/main
function hasMask(){return maskCtx.getImageData(0,0,maskCanvas.width,maskCanvas.height).data.some((v,i)=>i%4===3&&v>127);}
function exportMask(){const c=document.createElement('canvas');c.width=maskCanvas.width;c.height=maskCanvas.height;const x=c.getContext('2d');x.fillStyle='black';x.fillRect(0,0,c.width,c.height);x.drawImage(maskCanvas,0,0);return new Promise(r=>c.toBlob(r,'image/png'));}
let prev=null;
function point(e){const r=$('editor').getBoundingClientRect();return [(e.clientX-r.left)*maskCanvas.width/r.width,(e.clientY-r.top)*maskCanvas.height/r.height];}
function stroke(e){if(!painting||!personImage)return;e.preventDefault();const p=point(e),r=$('editor').getBoundingClientRect();maskCtx.globalCompositeOperation=erase?'destination-out':'source-over';maskCtx.strokeStyle='white';maskCtx.fillStyle='white';maskCtx.lineWidth=Number($('brush').value)*maskCanvas.width/r.width;maskCtx.lineCap='round';maskCtx.lineJoin='round';maskCtx.beginPath();maskCtx.moveTo(...(prev||p));maskCtx.lineTo(...p);maskCtx.stroke();if(!prev){maskCtx.beginPath();maskCtx.arc(p[0],p[1],maskCtx.lineWidth/2,0,Math.PI*2);maskCtx.fill();}prev=p;redraw();}
$('editor').onpointerdown=e=>{if(!personImage)return;painting=true;prev=null;$('editor').setPointerCapture(e.pointerId);stroke(e);};$('editor').onpointermove=stroke;['pointerup','pointercancel'].forEach(event=>$('editor').addEventListener(event,()=>{painting=false;prev=null;}));
function safe(fn){return async(...args)=>{try{await fn(...args);}catch(e){toast(e.message);}};}
$('pairOpen').onclick=()=>$('pairDialog').showModal();$('pairClose').onclick=()=>$('pairDialog').close();
$('pairForm').onsubmit=safe(async e=>{e.preventDefault();token=$('tokenInput').value.trim();await api('/api/status');sessionStorage.setItem('edgeai_token',token);$('tokenInput').value='';$('pairDialog').close();await status();toast('Browser paired. Upload your images to begin.');});
<<<<<<< HEAD
async function status(){if(!token)return;try{const s=await api('/api/status');$('connection').textContent='● Browser paired · local service';if(cameraMode&&!cameraOrientationPending)updateCameraFrameInfo(s.camera);$('modelStatus').textContent=s.models_present?(s.pipeline_loaded?'Model loaded':'Weights found · loads on first use'):'Weights missing · setup required';
=======
async function status(){if(!token)return;try{const s=await api('/api/status');$('connection').textContent='● Browser paired · local service';$('modelStatus').textContent=s.models_present?(s.pipeline_loaded?'Model loaded':'Weights found · loads on first use'):'Weights missing · setup required';
>>>>>>> origin/main
const mode=s.memory_mode||(s.offload?'sequential':'resident');$('memoryMode').textContent='GPU MEMORY MODE · '+mode.toUpperCase();
$('memoryHint').textContent=mode==='staged'?'Whole UNet stays on GPU during all denoising steps. VAE and safety checker run in separate phases. Low VRAM between requests is normal.':mode==='resident'?'All pipeline weights remain on GPU. Fastest transfer path, but highest memory pressure. Use Draft/Balanced first.':'Sequential layer offload: minimum VRAM, frequent transfers. For more GPU residency, restart with EDGEAI_MEMORY=staged.';}catch(e){$('connection').textContent='Pairing or connection needed';}}
$('personInput').onchange=safe(async e=>{const b=await normalize(e.target.files[0]);await setPerson(await upload(b));e.target.value='';});
$('garmentInput').onchange=safe(async e=>{const b=await normalize(e.target.files[0]);await setGarmentSource(await upload(b));e.target.value='';});
$('paint').onclick=()=>{erase=false;$('paint').classList.add('selected');$('erase').classList.remove('selected');};$('erase').onclick=()=>{erase=true;$('erase').classList.add('selected');$('paint').classList.remove('selected');};
$('clearMask').onclick=()=>{maskCtx.clearRect(0,0,maskCanvas.width,maskCanvas.height);redraw();};
function dressMaskOptions(){return {profile:$('category').value==='overall'&&$('longDress').checked?'long_dress':'standard',hem_fraction:Number($('dressHem').value)/100,flare:Number($('dressFlare').value)/100,sleeves:$('category').value!=='lower'&&$('allowSleeves').checked};}
function maskSettingsChanged(){maskSettingsVersion++;if(personImage){$('clearMask').click();toast('Mask settings changed. Click Auto mask again, then review the new region.');}}
function updateCategoryUI(){$('dressControls').hidden=$('category').value!=='overall';$('allowSleeves').disabled=$('category').value==='lower';if($('category').value==='overall'&&['draft','balanced'].includes($('preset').value))$('preset').value='dress';maskSettingsChanged();}
$('category').onchange=()=>{updateCategoryUI();garmentCategoryChanged();};
$('allowSleeves').onchange=maskSettingsChanged;
$('longDress').onchange=maskSettingsChanged;
$('dressHem').oninput=()=>{$('hemValue').textContent=$('dressHem').value+'%';};
$('dressFlare').oninput=()=>{$('flareValue').textContent=$('dressFlare').value+'%';};
$('dressHem').onchange=maskSettingsChanged;$('dressFlare').onchange=maskSettingsChanged;
$('autoMask').onclick=safe(async()=>{if(!personId)throw Error('Upload or capture a person first');$('autoMask').disabled=true;const captured=personId,category=$('category').value,version=maskSettingsVersion;try{const r=await api('/api/mask',{method:'POST',body:{person:captured,category,...dressMaskOptions()}});if(personId!==captured||$('category').value!==category||version!==maskSettingsVersion)return;const im=await assetImage(r.mask);maskCtx.globalCompositeOperation='source-over';maskCtx.clearRect(0,0,maskCanvas.width,maskCanvas.height);maskCtx.drawImage(im,0,0);const pixels=maskCtx.getImageData(0,0,maskCanvas.width,maskCanvas.height);for(let i=0;i<pixels.data.length;i+=4){pixels.data[i+3]=pixels.data[i]>127?255:0;pixels.data[i]=pixels.data[i+1]=pixels.data[i+2]=255;}maskCtx.putImageData(pixels,0,0);redraw();toast('Mask ready. Review sleeves, hem and overlapping hands before generating.');}finally{$('autoMask').disabled=false;}});
$('generate').onclick=safe(async()=>{if(!personId||!garmentId)throw Error('Add a person and prepare a garment-only reference first');if(!garmentPreparationId||!$('garmentReviewed').checked)throw Error('Review and confirm the extracted garment before generating');if(currentJob)throw Error('Wait for the current generation');if(!hasMask())throw Error('Create an auto mask or paint the clothing region before generating');$('generate').disabled=true;try{const person=personId,garment=garmentId,preparation=garmentPreparationId,category=$('category').value,preset=$('preset').value,seed=Number($('seed').value);const mask=await upload(await exportMask(),true);const r=await api('/api/jobs',{method:'POST',body:{person,garment,category,preset,seed,mask,preparation,garment_reviewed:true}});currentJob=r.id;$('progress').hidden=false;$('cancel').hidden=false;poll(r.id,person);}catch(e){$('generate').disabled=false;throw e;}});
async function poll(id,original){if(currentJob!==id)return;try{const j=await api('/api/jobs/'+id);$('jobState').textContent=j.state.toUpperCase();const elapsed=Math.round((Date.now()/1000)-(j.started||j.submitted));$('progressText').textContent=j.state+' · '+elapsed+'s · keep this tab open';if(['done','failed','cancelled'].includes(j.state)){currentJob=null;$('generate').disabled=false;$('cancel').hidden=true;$('progress').hidden=true;if(j.state==='done'){lastResult=j.result;await Promise.all([showAsset('resultImage',lastResult.image),showAsset('resultPerson',original)]);$('resultEmpty').hidden=true;$('resultArea').hidden=false;const m=lastResult.metrics;$('metrics').textContent=`${m.resolution.join(' × ')} · ${m.steps} steps · seed ${m.seed}\nDiffusion: ${m.diffusion_seconds}s  |  Total engine: ${m.total_seconds}s  |  Peak allocated VRAM: ${m.peak_allocated_gb} GB\n${m.gpu} · Memory mode ${m.memory_mode||(m.offload?'sequential':'resident')}
${m.stage_seconds?'Stages: '+JSON.stringify(m.stage_seconds)+' s | Weight transfers: '+m.weight_transfer_seconds+'s':''}`;toast('Try-on complete. Inspect the result before presenting it.');}else toast(j.error||'Generation cancelled.');await status();return;}pollTimer=setTimeout(()=>poll(id,original),1200);}catch(e){toast(e.message);pollTimer=setTimeout(()=>poll(id,original),3500);}}
$('cancel').onclick=safe(async()=>{if(currentJob){await api('/api/jobs/'+currentJob,{method:'DELETE'});toast('Cancellation requested. Active CUDA work must finish before it can be discarded.');}});
async function download(key,name){if(!key)return;const b=await api('/api/assets/'+key);const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
$('download').onclick=safe(()=>download(lastResult?.image,'form-tryon.png'));$('downloadMask').onclick=safe(()=>download(lastResult?.mask,'form-mask.png'));$('downloadRaw').onclick=safe(()=>download(lastResult?.raw,'form-raw-output.png'));$('downloadCondition').onclick=safe(()=>download(lastResult?.condition,'form-actual-garment-input.png'));
$('photoTab').onclick=()=>switchMode(false);$('cameraTab').onclick=()=>switchMode(true);
<<<<<<< HEAD
let cameraViewEpoch=0,cameraOrientationPending=false,cameraOrientationReady=false;
const cameraModes=['source','portrait_cw','portrait_ccw','cw90','ccw90','180'];
const rememberedCameraMode=sessionStorage.getItem('edgeai_camera_orientation');
if(cameraModes.includes(rememberedCameraMode))$('cameraOrientation').value=rememberedCameraMode;
function resetCameraPreview(){
 $('cameraPreview').hidden=true;$('cameraEmpty').hidden=false;
 $('cameraPreview').closest('.camera-box').classList.remove('has-frame');
}
function updateCameraFrameInfo(info){
 if(!info)return;
 if(info.error){$('cameraFrameInfo').textContent='Camera: '+info.error;return;}
 if(info.input_size&&info.output_size){
  $('cameraFrameInfo').textContent=`Stream ${info.input_size.join(' × ')} → oriented frame ${info.output_size.join(' × ')} · ${info.rotation_degrees||0}° clockwise. Capture keeps this orientation (2048px maximum side).`;
 }else $('cameraFrameInfo').textContent='Waiting for video. Preview and capture use the same orientation.';
}
async function applyCameraOrientation(){
 if(!token)throw Error('Pair this browser first');
 if(cameraOrientationPending)throw Error('Wait for the current orientation change');
 const epoch=++cameraViewEpoch;cameraOrientationPending=true;cameraOrientationReady=false;
 $('capture').disabled=true;$('cameraOrientation').disabled=true;resetCameraPreview();
 $('cameraFrameInfo').textContent='Applying orientation to preview and capture…';
 try{
  const orientation=$('cameraOrientation').value;
  const info=await api('/api/camera/orientation',{method:'POST',body:{orientation}});
  if(epoch!==cameraViewEpoch)return;
  sessionStorage.setItem('edgeai_camera_orientation',orientation);
  cameraOrientationReady=true;updateCameraFrameInfo(info);
 }catch(e){$('cameraFrameInfo').textContent='Orientation not applied: '+e.message;throw e;}
 finally{cameraOrientationPending=false;$('cameraOrientation').disabled=false;$('capture').disabled=!cameraOrientationReady;}
}
$('cameraOrientation').onchange=safe(applyCameraOrientation);
$('openCamera').onclick=safe(async()=>{await applyCameraOrientation();await api('/api/camera/open',{method:'POST',body:{source:$('cameraSource').value,orientation:$('cameraOrientation').value}});toast('Opening camera…');});
$('closeCamera').onclick=safe(async()=>{await api('/api/camera/close',{method:'POST'});cameraViewEpoch++;resetCameraPreview();$('cameraFrameInfo').textContent='Camera stopped.';});
$('capture').onclick=safe(async()=>{if(cameraOrientationPending||!cameraOrientationReady)throw Error('Apply a camera orientation before capturing');const epoch=cameraViewEpoch;const r=await api('/api/camera/capture',{method:'POST'});if(epoch!==cameraViewEpoch)throw Error('Orientation changed during capture. Capture again.');await setPerson(r.id);toast(`Frame captured${r.width?' · '+r.width+' × '+r.height:''}. This orientation is used by the mask editor and AI.`);});
async function preview(){
 if(cameraMode&&token&&!cameraOrientationPending&&cameraOrientationReady){
  const epoch=cameraViewEpoch;
  try{
   const b=await api('/api/camera/frame');
   if(epoch===cameraViewEpoch&&cameraMode&&!cameraOrientationPending){
    if(b){if(previewURL)URL.revokeObjectURL(previewURL);previewURL=URL.createObjectURL(b);$('cameraPreview').src=previewURL;$('cameraPreview').hidden=false;$('cameraEmpty').hidden=true;$('cameraPreview').closest('.camera-box').classList.add('has-frame');}
    else resetCameraPreview();
   }
  }catch(e){if(epoch===cameraViewEpoch)$('cameraFrameInfo').textContent='Camera preview unavailable: '+e.message;}
 }
 setTimeout(preview,160);
}
=======
$('openCamera').onclick=safe(async()=>{await api('/api/camera/open',{method:'POST',body:{source:$('cameraSource').value}});toast('Opening camera…');});
$('closeCamera').onclick=safe(async()=>{await api('/api/camera/close',{method:'POST'});$('cameraPreview').hidden=true;$('cameraEmpty').hidden=false;});
$('capture').onclick=safe(async()=>{const r=await api('/api/camera/capture',{method:'POST'});await setPerson(r.id);toast('Frame captured. The result will match this pose, not subsequent movement.');});
async function preview(){if(cameraMode&&token){try{const b=await api('/api/camera/frame');if(b){if(previewURL)URL.revokeObjectURL(previewURL);previewURL=URL.createObjectURL(b);$('cameraPreview').src=previewURL;$('cameraPreview').hidden=false;$('cameraEmpty').hidden=true;}else{$('cameraPreview').hidden=true;$('cameraEmpty').hidden=false;}}catch(e){/* status panel reports connectivity; no repeated toasts */}}setTimeout(preview,160);}
>>>>>>> origin/main
$('clearSession').onclick=safe(async()=>{if(!confirm('Delete all uploaded, captured and generated images in this local session?'))return;await api('/api/session',{method:'DELETE'});location.reload();});
status();statusTimer=setInterval(status,12000);preview();

// Catalog requests have their own bounded background worker, independent of CUDA.
let catalogJob=null, catalogURLs=[], catalogVersion=0;
$('catalogSource').onchange=()=>{const local=$('catalogSource').value==='local';$('catalogLive').disabled=local;if(local)$('catalogLive').checked=false;else $('catalogLive').checked=true;};
$('catalogForm').onsubmit=safe(async e=>{
 e.preventDefault();if(catalogJob)throw Error('A clothing search is already running');
 $('catalogSearch').disabled=true;$('catalogState').textContent='SEARCHING';
 try{const body={event:$('catalogQuery').value.trim(),budget:$('catalogBudget').value.trim(),source:$('catalogSource').value||null,category:$('catalogCategory').value||null,brand:$('catalogBrand').value.trim()||null,color:$('catalogColor').value.trim()||null,live:$('catalogLive').checked,limit:24};
 const j=await api('/api/catalog/search',{method:'POST',body});catalogJob=j.id;
 $('catalogMessage').textContent=body.live?'Fetching public stores now. No saved products will be substituted. A search can take up to two minutes.':'Searching local saved products…';
 pollCatalog(j.id);
 }catch(err){$('catalogSearch').disabled=false;$('catalogState').textContent='SEARCH NOT STARTED';throw err;}
});
async function pollCatalog(id,retries=0){
 if(catalogJob!==id)return;
 try{const job=await api('/api/catalog/search/'+id);$('catalogState').textContent=job.state.replaceAll('_',' ').toUpperCase();
 if(['done','failed','cancelled'].includes(job.state)){
 catalogJob=null;$('catalogSearch').disabled=false;
 if(job.state==='done')await renderCatalog(job.result);
 else{$('catalogMessage').textContent=job.error||'Search cancelled';toast(job.error||'Search cancelled');}
 return;}
 setTimeout(()=>pollCatalog(id),900);
 }catch(err){if(retries<3)setTimeout(()=>pollCatalog(id,retries+1),2500);else{catalogJob=null;$('catalogSearch').disabled=false;$('catalogMessage').textContent='Could not read search status. The server may still be searching. '+err.message;}}
}
async function renderCatalog(report){
 const version=++catalogVersion;
 catalogURLs.forEach(URL.revokeObjectURL);catalogURLs=[];
 $('catalogResults').replaceChildren();$('catalogSources').replaceChildren();
 $('catalogMessage').textContent=report.message;
 $('catalogState').textContent=report.used_live?'LIVE FETCH · '+(report.products||[]).length+' RESULTS':'SAVED CATALOG · NOT LIVE';
 $('catalogSources').hidden=!(report.sources||[]).length;
 for(const s of report.sources||[]){const line=document.createElement('div');line.textContent=`${s.source.toUpperCase()} · ${s.status} · ${s.message}${s.checked_at ? " · checked "+s.checked_at : ""}`;$('catalogSources').appendChild(line);}
 for(const product of report.products||[]){
 const card=document.createElement('article');card.className='catalog-card';
 const img=document.createElement('img');img.alt=product.title;img.loading='lazy';card.appendChild(img);
 const content=document.createElement('div');content.className='catalog-card-body';card.appendChild(content);
 const meta=document.createElement('span');meta.className='catalog-meta';meta.textContent=`${product.source.toUpperCase()} / ${product.category||'unknown category'}`;content.appendChild(meta);
 const title=document.createElement('h3');title.textContent=product.title;content.appendChild(title);
 const brand=document.createElement('p');brand.textContent=product.brand||'';content.appendChild(brand);
 const price=document.createElement('p');price.className='catalog-price';price.textContent=product.price==null?'Price unavailable':new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(product.price);content.appendChild(price);
 if(product.observed_at||product.updated_at){const stamp=document.createElement('p');stamp.className='catalog-meta';stamp.textContent=(product.freshness==='fetched_this_search'?'Fetched: ':'Saved observation: ')+(product.observed_at||product.updated_at);content.appendChild(stamp);}
 if(product.price_note){const note=document.createElement('p');note.className='catalog-meta';note.textContent=product.price_note;content.appendChild(note);}
 try{const linkURL=new URL(product.source_url);if(['https:','http:'].includes(linkURL.protocol)){const a=document.createElement('a');a.href=linkURL.href;a.target='_blank';a.rel='noopener noreferrer nofollow';a.textContent='Verify at retailer ↗';content.appendChild(a);}}catch(e){}
 const button=document.createElement('button');button.textContent=product.tryon_supported?'Select garment ↗':'Unmapped / multi-piece item';button.disabled=true;content.appendChild(button);
 button.onclick=safe(async()=>{button.disabled=true;try{const selection=await api(`/api/catalog/products/${product.id}/select`,{method:'POST'});await setGarmentSource(selection.garment,selection.category);toast('Reference selected. Clothing-only extraction is running; review the cutout before generating.');$('garmentPrepStatus').scrollIntoView({behavior:'smooth',block:'center'});}finally{button.disabled=!product.tryon_supported;}});
 $('catalogResults').appendChild(card);
 // Fetch authenticated thumbnails without putting tokens in src URLs.
 api(`/api/catalog/products/${product.id}/image`).then(blob=>{if(version!==catalogVersion)return;const u=URL.createObjectURL(blob);catalogURLs.push(u);img.src=u;button.disabled=!product.tryon_supported;}).catch(()=>{img.alt='Product photo unavailable';button.disabled=true;});
 }
}

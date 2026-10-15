"""Garment-only extraction contracts, with synthetic labels (not AI-quality claims)."""
from io import BytesIO
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from edgeai.garment import cloth_mask, prepare_from_mask
from edgeai.masking import mask_from_labels
from edgeai.engine import TryOnEngine, TryOnResult
from edgeai.config import Settings
from edgeai.storage import Storage
from edgeai.imaging import load_rgb
from edgeai.server import create_app


def labels():
    a=np.zeros((180,140),np.uint8)
    a[5:30,55:85]=11
    a[35:140,40:100]=7
    a[32:110,27:38]=14
    a[32:110,102:113]=15
    a[140:170,45:60]=12
    a[140:170,80:95]=13
    a[80:85,40:100]=8
    a[65:75,55:65]=14  # hand occludes garment: do NOT fill this hole
    return a


def test_clothing_mask_excludes_body_and_keeps_belt():
    a=labels();m,_=cloth_mask(a,'overall');b=np.asarray(m)>0
    assert b[50,70] and b[82,70]
    assert not b[np.isin(a,[11,14,15,12,13])].any()
    assert not b[0].any()
    assert not b[70,60]  # internal skin hole preserved


def test_garment_labels_are_category_specific():
    a=labels();a[a==7]=4;a[115:135,50:90]=6
    upper,_=cloth_mask(a,'upper')
    assert not np.asarray(upper)[120,60]
    lower,_=cloth_mask(a,'lower')
    assert np.asarray(lower)[120,60] and not np.asarray(lower)[50,60]
    overall,warnings=cloth_mask(a,'overall')
    assert warnings and not np.asarray(overall)[120,60]


def test_no_cloth_fails_not_raw_photo_fallback():
    a=np.full((120,100),11,np.uint8)
    for cat in ('upper','lower','overall'):
        with pytest.raises(ValueError): cloth_mask(a,cat)
    with pytest.raises(ValueError): cloth_mask(a,'saree')


def test_no_dilation_into_skin_or_filling_hidden_fabric():
    a=labels();m,_=cloth_mask(a,'overall')
    image=Image.new('RGB',m.size,(170,90,25))
    prep=prepare_from_mask(image,m,'overall','semantic_clothing')
    assert prep.metadata['review_required'] is True
    assert prep.metadata['hidden_fabric_reconstructed'] is False
    assert set(map(tuple,np.asarray(prep.image).reshape(-1,3))) <= {(170,90,25),(255,255,255)}
    x0,y0,x1,y1=prep.metadata['crop_box']
    assert x0==40 and x1==100 and y0==35 and y1==140
    assert prep.image.width<image.width and prep.image.height<image.height


def test_manual_crop_preserves_aspect_and_original_colors():
    im=Image.new('RGB',(200,240),(10,20,30));mask=Image.new('L',im.size)
    mask.paste(255,(60,40,140,200))
    r=prepare_from_mask(im,mask,'overall')
    arr=np.asarray(r.image)
    assert r.metadata['crop_box']==[60,40,140,200]
    assert (arr[20,20]==[10,20,30]).all()
    assert (arr[0,0]==255).all()
    assert r.mask.size==im.size


@pytest.mark.parametrize('case',['empty','size','tiny'])
def test_bad_reference_masks_rejected(case):
    im=Image.new('RGB',(100,150));mask=Image.new('L',im.size)
    if case=='size': mask=Image.new('L',(20,20),255)
    if case=='tiny': mask.paste(255,(10,10,12,12))
    with pytest.raises(ValueError): prepare_from_mask(im,mask,'overall')


def test_cropped_garment_warning():
    im=Image.new('RGB',(100,150));mask=Image.new('L',im.size);mask.paste(255,(20,0,80,100))
    p=prepare_from_mask(im,mask,'upper')
    assert any('photo edge' in w for w in p.metadata['warnings'])


def test_sleeves_are_opt_in_keep_distal_hands_and_face():
    a=labels()
    default=np.asarray(mask_from_labels(a,'overall'))
    sleeves=np.asarray(mask_from_labels(a,'overall',sleeves=True))
    assert not default[a==14].any()
    assert sleeves[42,32]==255
    assert sleeves[105,32]==0  # distal hand region still protected
    assert not sleeves[a==11].any()
    assert sleeves.sum()>default.sum()
    with pytest.raises(ValueError): mask_from_labels(a,'lower',sleeves=True)


def test_transparent_upload_is_white_not_black(tmp_path):
    image=Image.new('RGBA',(60,80),(0,0,0,0));image.paste((100,50,20,255),(20,20,40,60))
    data=BytesIO();image.save(data,format='PNG')
    store=Storage(tmp_path);key=store.upload(data.getvalue())
    out=load_rgb(store.path(key))
    assert out.getpixel((0,0))==(255,255,255)
    assert out.getpixel((25,25))==(100,50,20)


TOKEN='preparation-test-only-token-1234'
AUTH={'Authorization':'Bearer '+TOKEN}

def upload(client,im,mask=False):
    data=BytesIO();im.save(data,format='PNG')
    r=client.post('/api/assets?mask='+str(mask).lower(),headers=AUTH,files={'file':('fixture.png',data.getvalue(),'image/png')})
    assert r.status_code==200
    return r.json()['id']


class ContractOnlyEngine(TryOnEngine):
    """Test-only generation double. Real preparation, no trained synthesis claim."""
    def generate(self,person,garment,mask,progress,**kw):
        return TryOnResult(person,mask,person,{'contract_test':True},condition=garment)


def test_preparation_api_handoff_review_and_category_gate(tmp_path):
    settings=Settings(data_dir=tmp_path/'data',model_dir=tmp_path/'missing-models')
    app=create_app(settings,TOKEN,ContractOnlyEngine(settings))
    with TestClient(app) as c:
        source=upload(c,Image.new('RGB',(100,150),(170,90,25)))
        mask=Image.new('L',(100,150));mask.paste(255,(30,30,70,120));mask_key=upload(c,mask,True)
        assert c.post('/api/garments/prepare',json={'garment':source}).status_code==401
        j=c.post('/api/garments/prepare',headers=AUTH,json={'garment':source,'category':'overall','mask':mask_key}).json()['id']
        app.state.garment_worker.pending.join()
        job=c.get('/api/garments/prepare/'+j,headers=AUTH).json()
        assert job['state']=='done'
        result=job['result'];assert result['source']==source and result['garment']!=source
        assert result['metadata']['method']=='manual_mask'
        req={'person':source,'garment':result['garment'],'mask':mask_key,'category':'overall','preparation':j}
        assert c.post('/api/jobs',headers=AUTH,json=req).status_code==400
        req['garment_reviewed']=True
        wrong={**req,'garment':source}
        assert c.post('/api/jobs',headers=AUTH,json=wrong).status_code==409
        assert c.post('/api/jobs',headers=AUTH,json={**req,'category':'upper'}).status_code==409
        g=c.post('/api/jobs',headers=AUTH,json=req)
        assert g.status_code==202
        app.state.worker.pending.join()
        result=c.get('/api/jobs/'+g.json()['id'],headers=AUTH).json()['result']
        assert result['condition'] and result['preparation']==j and result['garment_reviewed']
        # Missing actual parser weights fail openly. Original model photo NOT returned.
        j=c.post('/api/garments/prepare',headers=AUTH,json={'garment':source,'category':'overall'}).json()['id']
        app.state.garment_worker.pending.join()
        failed=c.get('/api/garments/prepare/'+j,headers=AUTH).json()
        assert failed['state']=='failed' and failed['result'] is None
        assert c.get('/api/garments/prepare/not-real',headers=AUTH).status_code==404
        assert c.delete('/api/session',headers=AUTH).status_code==200
        assert c.get('/api/garments/prepare/'+j,headers=AUTH).status_code==404


def test_enclosed_clothing_panel_recovered_but_not_skin_or_background():
    a=labels();a[95:108,70:82]=4;a[110:118,70:80]=0
    mask,_=cloth_mask(a,'overall');b=np.asarray(mask)
    assert b[100,75]==255  # visible tie/panel misclassified as upper clothing
    assert b[70,60]==0    # real hand occlusion remains excluded
    assert b[114,75]==0   # background not invented as cloth

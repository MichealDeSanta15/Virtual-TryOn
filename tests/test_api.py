from io import BytesIO
import numpy as np
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from edgeai.server import create_app
from edgeai.config import Settings
from edgeai.engine import TryOnResult

TOKEN='unit-test-only-token-do-not-use'
AUTH={'Authorization':'Bearer '+TOKEN}

class TestOnlyEngine:
    """Contract double for API tests ONLY; never used by production or preview."""
    pipeline=None
    def make_mask(self,person,category,**kwargs):
        m=Image.new('L',person.size);m.paste(255,(10,10,30,30));return m,person
    def generate(self,person,garment,mask,progress,**kwargs):
        progress('generating');return TryOnResult(person,mask,person,{'unit_test':True})

@pytest.fixture
def client(tmp_path):
    app=create_app(Settings(model_dir=tmp_path/'models',data_dir=tmp_path/'data'),TOKEN,TestOnlyEngine())
    with TestClient(app) as c:yield c


def upload(client):
    b=BytesIO();Image.new('RGB',(60,80),'white').save(b,format='PNG')
    r=client.post('/api/assets',headers=AUTH,files={'file':('x.png',b.getvalue(),'image/png')})
    assert r.status_code==200
    return r.json()['id']


def test_auth_and_public_ui(client):
    assert client.get('/').status_code==200
    assert client.get('/health').status_code==200
    assert client.get('/api/status').status_code==401
    assert client.get('/api/status',headers=AUTH).status_code==200
    assert client.get('/static/secret.txt').status_code==404


def test_job_contract(client):
    person,garment=upload(client),upload(client)
    r=client.post('/api/mask',headers=AUTH,json={'person':person,'category':'upper'})
    mask=r.json()['mask']
    r=client.post('/api/jobs',headers=AUTH,json={'person':person,'garment':garment,'mask':mask})
    assert r.status_code==202
    client.app.state.worker.pending.join()
    j=client.get('/api/jobs/'+r.json()['id'],headers=AUTH).json()
    assert j['state']=='done'
    assert client.get('/api/assets/'+j['result']['image'],headers=AUTH).status_code==200
    assert client.get('/api/assets/'+j['result']['image']).status_code==401
    assert client.delete('/api/session',headers=AUTH).status_code==200
    assert client.get('/api/assets/'+person,headers=AUTH).status_code==404


def test_request_validation(client):
    person=upload(client)
    r=client.post('/api/jobs',headers=AUTH,json={'person':person,'garment':person,'category':'sari'})
    assert r.status_code==422
    r=client.post('/api/jobs',headers=AUTH,json={'person':'../not-a-path','garment':person})
    assert r.status_code==400
    assert client.post('/api/camera/capture',headers=AUTH).status_code==409
    assert client.post('/api/camera/open',headers=AUTH,json={'source':'C:/private.mp4'}).status_code==400


def test_camera_capture_contract(client):
    frame=np.zeros((240,320,3),np.uint8);frame[:,:,2]=255
    client.app.state.frames.put(frame,'unit-test')
    r=client.get('/api/camera/frame',headers=AUTH);assert r.status_code==200
    r=client.post('/api/camera/capture',headers=AUTH)
    im=Image.open(BytesIO(client.get('/api/assets/'+r.json()['id'],headers=AUTH).content))
    assert im.getpixel((0,0))==(255,0,0)

"""Pixel-level orientation and actual preview/capture HTTP contracts; no phone needed."""
from io import BytesIO
import numpy as np
from PIL import Image
import pytest
from fastapi.testclient import TestClient
from edgeai.camera import LatestFrame, orient_frame, rotation_for_shape
from edgeai.server import create_app
from edgeai.config import Settings
from edgeai.imaging import bgr_to_pil


@pytest.mark.parametrize('mode,k', [('source',0),('cw90',-1),('ccw90',1),('180',2),
                                    ('portrait_cw',-1),('portrait_ccw',1)])
def test_landscape_rotation_is_exact_copy(mode,k):
    frame=np.arange(4*7*3,dtype=np.uint8).reshape(4,7,3)
    before=frame.copy();result=orient_frame(frame,mode)
    assert np.array_equal(result,np.rot90(frame,k=k))
    assert result.size==frame.size and np.array_equal(frame,before)
    result[:]=0
    assert np.array_equal(frame,before)


@pytest.mark.parametrize('shape',[(7,4,3),(5,5,3)])
@pytest.mark.parametrize('mode',['portrait_cw','portrait_ccw'])
def test_portrait_and_square_not_double_rotated(shape,mode):
    frame=np.arange(np.prod(shape),dtype=np.uint8).reshape(shape)
    assert np.array_equal(orient_frame(frame,mode),frame)
    assert rotation_for_shape(shape,mode)==0


def test_source_kept_raw_and_orientation_change_does_not_fake_arrival():
    frames=LatestFrame();original=np.arange(6*10*3,dtype=np.uint8).reshape(6,10,3)
    frames.put(original)
    timestamp=frames.timestamp;received=frames.received;seq=frames.sequence
    frames.set_orientation('portrait_cw')
    ok,rotated,new_seq=frames.read_new(seq,timeout=.01)
    assert ok and new_seq>seq
    assert np.array_equal(rotated,np.rot90(original,k=-1))
    assert frames.timestamp==timestamp and frames.received==received
    assert frames.status()['input_size']==[10,6]
    assert frames.status()['output_size']==[6,10]
    assert frames.status()['rotation_degrees']==90
    frames.set_orientation('source')
    assert np.array_equal(frames.read()[1],original)  # not another rotation of transformed data
    frames.set_orientation('portrait_ccw')
    assert np.array_equal(frames.read()[1],np.rot90(original,k=1))
    assert not frames.read(max_age=-1)[0]
    frames.clear();assert frames.status()['output_size'] is None
    assert frames.orientation=='portrait_ccw'


def test_bad_orientation_rejected_without_changing_setting():
    frames=LatestFrame()
    with pytest.raises(ValueError):frames.set_orientation('guess-the-phone-sensor')
    assert frames.orientation=='source'
    with pytest.raises(ValueError):orient_frame(np.zeros((2,3,3),np.uint8),'45')


TOKEN='camera-orientation-test-token-1234'
AUTH={'Authorization':'Bearer '+TOKEN}


@pytest.fixture
def client(tmp_path):
    class NoInference:
        pipeline=None
    app=create_app(Settings(data_dir=tmp_path/'data',model_dir=tmp_path/'models'),TOKEN,NoInference())
    with TestClient(app) as c:yield c


def test_camera_orientation_api_auth_and_validation(client):
    assert client.post('/api/camera/orientation',json={'orientation':'portrait_cw'}).status_code==401
    assert client.post('/api/camera/orientation',headers=AUTH,json={'orientation':'45'}).status_code==422
    assert client.post('/api/camera/orientation',headers=AUTH,json={'orientation':'portrait_cw'}).status_code==200
    assert client.post('/api/camera/capture',headers=AUTH).status_code==409


def test_portrait_preview_and_saved_capture_agree(client):
    frame=np.zeros((64,96,3),np.uint8)
    frame[:32,:48]=(0,0,240);frame[:32,48:]=(0,240,0)
    frame[32:,:48]=(240,0,0);frame[32:,48:]=(0,240,240)
    client.app.state.frames.put(frame,'test-only')
    response=client.post('/api/camera/orientation',headers=AUTH,json={'orientation':'portrait_cw'})
    assert response.json()['output_size']==[64,96]
    r=client.get('/api/camera/frame',headers=AUTH)
    assert r.status_code==200
    preview=Image.open(BytesIO(r.content)).convert('RGB')
    capture=client.post('/api/camera/capture',headers=AUTH).json()
    assert (capture['width'],capture['height'])==(64,96)
    saved=Image.open(BytesIO(client.get('/api/assets/'+capture['id'],headers=AUTH).content)).convert('RGB')
    expected=np.asarray(bgr_to_pil(np.rot90(frame,k=-1)))
    assert preview.size==saved.size==(64,96)
    assert np.array_equal(np.asarray(saved),expected)
    # JPEG approximation away from quadrant boundaries, not a bit-exact JPEG claim.
    for y,x in [(12,12),(12,52),(82,12),(82,52)]:
        assert abs(np.asarray(preview,dtype=int)[y,x]-expected[y,x]).max()<12


def test_portrait_preview_bounded_without_downscaling_saved_photo(client):
    client.app.state.frames.put(np.zeros((900,1600,3),np.uint8))
    client.post('/api/camera/orientation',headers=AUTH,json={'orientation':'portrait_ccw'})
    preview=Image.open(BytesIO(client.get('/api/camera/frame',headers=AUTH).content))
    assert preview.size==(450,800)
    saved=client.post('/api/camera/capture',headers=AUTH).json()
    assert (saved['width'],saved['height'])==(900,1600)


def test_open_camera_applies_requested_orientation(client,monkeypatch):
    import edgeai.server as server
    class TestOnlyCamera:
        def __init__(self,source,frames):self.frames=frames
        def start(self):self.frames.put(np.zeros((60,100,3),np.uint8));return self
        def release(self):self.frames.clear()
    monkeypatch.setattr(server,'OpenCVCamera',TestOnlyCamera)
    response=client.post('/api/camera/open',headers=AUTH,json={'source':'0','orientation':'portrait_cw'})
    assert response.status_code==200
    assert client.app.state.frames.read()[1].shape==(100,60,3)
    assert client.post('/api/camera/close',headers=AUTH).status_code==200

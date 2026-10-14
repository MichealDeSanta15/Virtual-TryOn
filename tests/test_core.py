import time
import threading
from io import BytesIO
import numpy as np
import pytest
from PIL import Image
from edgeai.imaging import Letterbox, validate_mask, preserve_outside, bgr_to_pil, pil_to_bgr
from edgeai.masking import mask_from_labels
from edgeai.camera import LatestFrame
from edgeai.storage import Storage
from edgeai.worker import TryOnWorker, BusyError


def test_bgr_roundtrip():
    frame=np.zeros((25,31,3),np.uint8);frame[:,:,0]=221
    assert np.asarray(bgr_to_pil(frame))[0,0].tolist()==[0,0,221]
    assert np.array_equal(pil_to_bgr(bgr_to_pil(frame)),frame)

@pytest.mark.parametrize('shape',[(800,600),(600,800),(360,1200),(2000,550)])
def test_geometry(shape):
    image=Image.new('RGB',shape,'red');g=Letterbox.create(shape,(384,512))
    assert g.restore(g.apply(image)).size==shape
    mask=Image.new('L',shape,255)
    assert set(np.unique(g.apply(mask,True))) <= {0,255}
    assert g.restore(g.apply(mask,True),True).size==shape


def test_no_person_crop():
    image=Image.new('RGB',(1200,400),'white');g=Letterbox.create(image.size,(384,512))
    assert g.box[0]==0 and g.box[2]==384
    assert g.box[1]>0 and g.box[3]<512

@pytest.mark.parametrize('value',[0,255])
def test_invalid_mask(value):
    with pytest.raises(ValueError):validate_mask(Image.new('L',(100,100),value),(100,100))


def test_mask_wrong_size():
    with pytest.raises(ValueError):validate_mask(Image.new('L',(20,20)),(100,100))


def test_preserve_pixels():
    rng=np.random.default_rng(0);orig=rng.integers(0,256,(80,100,3),dtype=np.uint8)
    mask=np.zeros((80,100),np.uint8);mask[20:60,25:75]=255
    out=np.asarray(preserve_outside(Image.fromarray(orig),Image.new('RGB',(100,80),'white'),Image.fromarray(mask)))
    assert np.array_equal(orig[mask==0],out[mask==0])
    assert np.all(out[40,50]==255)


def test_parser_protects_face_and_hands():
    labels=np.zeros((100,80),np.uint8);labels[20:80,15:65]=4
    labels[15:30,30:50]=11;labels[40:65,35:45]=14
    mask=np.asarray(mask_from_labels(labels,'upper'))
    assert not mask[labels==11].any();assert not mask[labels==14].any()
    assert mask[35,25]==255


def test_parser_requires_category_region():
    with pytest.raises(ValueError):mask_from_labels(np.zeros((100,100)), 'lower')


def test_frame_copy_and_stale():
    f=LatestFrame();x=np.zeros((5,5,3),np.uint8);f.put(x);x[:]=200
    assert f.read()[1].max()==0
    a=f.read()[1];a[:]=180;assert f.read()[1].max()==0
    assert not f.read(max_age=-1)[0]
    f.release();assert not f.read()[0]


def test_frame_sequence():
    f=LatestFrame();f.put(np.zeros((4,4,3),np.uint8));f.put(np.ones((4,4,3),np.uint8))
    ok,frame,seq=f.read_new(0);assert ok and seq==2 and frame.min()==1
    assert not f.read_new(seq,timeout=.01)[0]


def test_storage(tmp_path):
    s=Storage(tmp_path);buf=BytesIO();Image.new('RGB',(50,50),'red').save(buf,format='PNG')
    key=s.upload(buf.getvalue());assert s.path(key).is_file()
    with pytest.raises(ValueError):s.path('../../etc/passwd')
    with pytest.raises(ValueError):s.upload(b'not an image')
    s.clear();assert not list(tmp_path.glob('*.png'))


def test_bounded_worker_and_cancellation():
    entered=threading.Event();release=threading.Event()
    def run(progress, value):
        entered.set();release.wait(3);progress('generating');return value
    w=TryOnWorker(run)
    try:
        a=w.submit(value=1);assert entered.wait(1)
        b=w.submit(value=2)
        with pytest.raises(BusyError):w.submit(value=3)
        w.cancel(a);w.cancel(b);release.set();w.pending.join()
        assert w.get(a)['state']=='cancelled' and w.get(a)['result'] is None
        assert w.get(b)['state']=='cancelled'
    finally:release.set();w.close()


def test_worker_error_recovery():
    def run(progress, value):
        if value==0:raise ValueError('bad input')
        return value
    w=TryOnWorker(run)
    try:
        a=w.submit(value=0);w.pending.join();assert w.get(a)['state']=='failed'
        b=w.submit(value=9);w.pending.join();assert w.get(b)['result']==9
    finally:w.close()

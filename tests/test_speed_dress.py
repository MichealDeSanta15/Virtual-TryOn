import numpy as np
import pytest
from edgeai.config import Settings
from edgeai.checkpoints import local_weight_options
from edgeai.masking import mask_from_labels, long_dress_envelope


@pytest.mark.parametrize('mode', ['staged', 'sequential', 'resident'])
def test_explicit_mode_overrides_legacy_env(monkeypatch, mode):
    monkeypatch.setenv('EDGEAI_OFFLOAD', '1')
    monkeypatch.setenv('EDGEAI_MEMORY', mode)
    assert Settings.from_env().effective_memory_mode == mode


def test_memory_defaults_and_legacy(monkeypatch):
    monkeypatch.delenv('EDGEAI_MEMORY', raising=False)
    monkeypatch.delenv('EDGEAI_OFFLOAD', raising=False)
    assert Settings.from_env().effective_memory_mode == 'staged'
    monkeypatch.setenv('EDGEAI_OFFLOAD', '1')
    assert Settings.from_env().effective_memory_mode == 'sequential'
    monkeypatch.setenv('EDGEAI_OFFLOAD', '0')
    assert Settings.from_env().effective_memory_mode == 'resident'
    assert Settings(offload=True).effective_memory_mode == 'sequential'


def test_reject_invalid_memory_mode(monkeypatch):
    monkeypatch.setenv('EDGEAI_MEMORY', 'unlimited')
    with pytest.raises(ValueError):
        Settings.from_env()


def test_explicit_local_checkpoint_format(tmp_path):
    p = tmp_path / 'unet'
    p.mkdir()
    with pytest.raises(FileNotFoundError): local_weight_options(tmp_path, 'unet')
    (p / 'diffusion_pytorch_model.bin').touch()
    assert local_weight_options(tmp_path, 'unet')['use_safetensors'] is False
    (p / 'diffusion_pytorch_model.safetensors').touch()
    assert local_weight_options(tmp_path, 'unet')['use_safetensors'] is True
    p = tmp_path / 'safety_checker'
    p.mkdir()
    (p / 'pytorch_model.bin').touch()
    assert local_weight_options(tmp_path, 'safety_checker', True)['use_safetensors'] is False
    (p / 'model.safetensors').touch()
    assert local_weight_options(tmp_path, 'safety_checker', True)['use_safetensors'] is True


def person_labels():
    labels = np.zeros((200, 140), np.uint8)
    labels[10:35, 55:85] = 11  # face
    labels[35:85, 40:100] = 4  # top
    labels[85:130, 40:65] = 6  # left shorts
    labels[85:130, 75:100] = 6  # right shorts
    labels[130:183, 44:62] = 12
    labels[130:183, 78:96] = 13
    labels[70:110, 62:76] = 14  # arm across torso/waist
    labels[183:195, 40:64] = 9
    labels[183:195, 76:100] = 10
    return labels


def test_dress_mask_extends_hem_and_fills_leg_gap():
    labels = person_labels()
    standard = np.asarray(mask_from_labels(labels, 'overall'))
    long_mask = np.asarray(mask_from_labels(labels, 'overall', profile='long_dress', hem_fraction=.92, flare=.2))
    assert standard[160, 70] == 0  # old clothes had no long skirt here
    assert long_mask[160, 70] == 255
    assert long_mask[160, 35] == 255  # room for a wider skirt
    assert not long_mask[np.isin(labels, [11, 14, 9, 10])].any()
    assert long_mask[190, 70] == 0
    assert long_mask[100, 0] == 0


def test_dress_controls_change_envelope():
    labels = person_labels()
    small = long_dress_envelope(labels, .75, 0)
    large = long_dress_envelope(labels, .92, .5)
    assert large.sum() > small.sum()
    assert not small[170].any()
    assert large[170].any()


def test_dress_request_validation():
    with pytest.raises(ValueError): mask_from_labels(person_labels(), 'upper', profile='long_dress')
    with pytest.raises(ValueError): long_dress_envelope(person_labels(), .99, .2)
    with pytest.raises(ValueError): long_dress_envelope(person_labels(), .8, 1)


def test_staged_placement_eviction_order():
    pytest.importorskip('torch')
    from types import SimpleNamespace
    from edgeai.memory import StagedPlacement
    calls = []
    class Model:
        def __init__(self, name): self.name = name
        def to(self, device): calls.append((self.name, str(device))); return self
    pipe = SimpleNamespace(vae=Model('vae'), unet=Model('unet'), safety_checker=Model('safety_checker'))
    placement = StagedPlacement(pipe, 'cpu')
    placement.activate('encode')
    placement.activate('denoise')
    assert calls == [('vae', 'cpu'), ('vae', 'cpu'), ('unet', 'cpu')]
    # No repeated relocation while the same network is active.
    n = len(calls)
    placement.activate('denoise')
    assert len(calls) == n
    placement.activate('decode')
    placement.activate('safety')
    placement.release()
    assert [name for name, _ in calls] == ['vae','vae','unet','unet','vae','vae','safety_checker','safety_checker']
    assert placement.active is None
    assert set(placement.timings) == {'encode', 'denoise', 'decode', 'safety'}

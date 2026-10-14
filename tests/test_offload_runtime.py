"""Real tiny random-weight models, no downloads. Checks execution, NOT try-on quality.

Install the AI dependencies to execute these tests; base-only environments skip them.
CPU is used as the execution device while Accelerate still offloads parameters to meta.
That reproduces the relevant lifecycle without needing a CUDA GPU.
"""
import pytest

torch = pytest.importorskip('torch')
pytest.importorskip('accelerate')
pytest.importorskip('diffusers')
pytest.importorskip('transformers')

from accelerate import cpu_offload
from diffusers import AutoencoderKL
from edgeai.vendor.catvton.utils import compute_vae_encodings


@pytest.fixture
def tiny_vae():
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(2)
    model = AutoencoderKL(
        in_channels=3, out_channels=3,
        down_block_types=('DownEncoderBlock2D',),
        up_block_types=('UpDecoderBlock2D',),
        block_out_channels=(16,), layers_per_block=1,
        latent_channels=4, norm_num_groups=8, sample_size=16,
    ).eval()
    yield model
    torch.set_num_threads(previous_threads)


def test_original_meta_device_transfer_reproduces_error(tiny_vae):
    """Keep the broken pattern here to demonstrate why it must not return."""
    cpu_offload(tiny_vae, execution_device=torch.device('cpu'), offload_buffers=True)
    assert tiny_vae.device.type == 'meta'
    image = torch.randn(1, 3, 16, 16)
    lost_data = image.to(tiny_vae.device, dtype=tiny_vae.dtype)
    with pytest.raises(NotImplementedError, match='Cannot copy out of meta tensor'):
        tiny_vae.encode(lost_data)


@pytest.mark.parametrize('explicit_device', [None, 'cpu'])
def test_encode_decode_repeated_with_real_offload_hooks(tiny_vae, explicit_device):
    tiny_vae.enable_slicing()
    tiny_vae.enable_tiling()
    cpu_offload(tiny_vae, execution_device=torch.device('cpu'), offload_buffers=True)
    image = torch.randn(1, 3, 16, 16)
    with torch.inference_mode():
        for _ in range(2):
            assert tiny_vae.device.type == 'meta'
            latent = compute_vae_encodings(image, tiny_vae, execution_device=explicit_device)
            assert latent.device.type == 'cpu'
            assert torch.isfinite(latent).all()
            decoded = tiny_vae.decode(latent / tiny_vae.config.scaling_factor).sample
            assert decoded.shape == image.shape
            assert decoded.device.type == 'cpu'
            assert torch.isfinite(decoded).all()
            # It must still offload afterwards, rather than silently disabling offload.
            assert tiny_vae.device.type == 'meta'


def test_offloaded_encoder_matches_resident_encoder(tiny_vae):
    image = torch.randn(1, 3, 16, 16)
    with torch.inference_mode():
        torch.manual_seed(123)
        reference = compute_vae_encodings(image, tiny_vae, execution_device='cpu')
        cpu_offload(tiny_vae, execution_device=torch.device('cpu'), offload_buffers=True)
        torch.manual_seed(123)
        actual = compute_vae_encodings(image, tiny_vae, execution_device='cpu')
    torch.testing.assert_close(actual, reference)


@pytest.mark.parametrize('meta_input', [True, False])
def test_meta_input_or_execution_device_is_rejected(tiny_vae, meta_input):
    image = torch.empty(1, 3, 16, 16, device='meta' if meta_input else 'cpu')
    with pytest.raises(ValueError, match='real input data'):
        compute_vae_encodings(image, tiny_vae, execution_device='cpu' if meta_input else 'meta')


@pytest.mark.parametrize("memory_mode", ["sequential", "staged", "resident"])
def test_tiny_catvton_denoising_path_repeated_with_offload(tiny_vae, memory_mode):
    """Exercise real encode -> UNet -> scheduler -> decode, using tiny random weights.

    Bypasses pretrained loading and safety checking ONLY in this test harness.
    It does not claim useful try-on output or CUDA/VRAM validation.
    """
    from PIL import Image
    from diffusers import UNet2DConditionModel, DDIMScheduler
    from edgeai.vendor.catvton.model.pipeline import CatVTONPipeline
    from edgeai.vendor.catvton.model.utils import init_adapter
    from edgeai.vendor.catvton.model.attn_processor import SkipAttnProcessor

    pipe = CatVTONPipeline.__new__(CatVTONPipeline)
    pipe.device = 'cpu'
    pipe.weight_dtype = torch.float32
    pipe.skip_safety_check = True
    pipe.vae = tiny_vae
    pipe.unet = UNet2DConditionModel(
        sample_size=16, in_channels=9, out_channels=4,
        down_block_types=('CrossAttnDownBlock2D',),
        up_block_types=('CrossAttnUpBlock2D',),
        block_out_channels=(16,), layers_per_block=1,
        cross_attention_dim=16, attention_head_dim=4, norm_num_groups=8,
    ).eval()
    init_adapter(pipe.unet, cross_attn_cls=SkipAttnProcessor)
    pipe.noise_scheduler = DDIMScheduler(num_train_timesteps=100)
    if memory_mode == 'sequential':
        for module in (pipe.vae, pipe.unet):
            cpu_offload(module, execution_device=torch.device('cpu'), offload_buffers=True)
    elif memory_mode == 'staged':
        from edgeai.memory import StagedPlacement
        pipe.placement = StagedPlacement(pipe, execution_device='cpu')
    image = Image.new('RGB', (16, 16), (100, 110, 120))
    garment = Image.new('RGB', (16, 16), (40, 70, 90))
    mask = Image.new('L', (16, 16), 0)
    mask.paste(255, (4, 4, 12, 12))
    with torch.inference_mode():
        for _ in range(2):
            output = pipe(image=image, condition_image=garment, mask=mask,
                          num_inference_steps=2, guidance_scale=2.5,
                          height=16, width=16,
                          generator=torch.Generator(device='cpu').manual_seed(42))
            assert len(output) == 1
            assert output[0].size == (16, 16)
            if memory_mode == 'sequential':
                assert pipe.vae.device.type == 'meta'
                assert pipe.unet.device.type == 'meta'
            elif memory_mode == 'staged':
                pipe.placement.release()
                assert pipe.placement.active is None
                assert set(pipe.placement.timings) == {'encode', 'denoise', 'decode'}
                pipe.placement.reset_metrics()

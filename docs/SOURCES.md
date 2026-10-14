# Technical sources used for the design

1. CatVTON source, paper links, VRAM claims and license:
   https://github.com/Zheng-Chong/CatVTON
   (Exact copied commit: `docs/upstream.json`.)
2. CatVTON official application and pipeline signatures:
   https://github.com/Zheng-Chong/CatVTON/blob/main/app.py
   https://github.com/Zheng-Chong/CatVTON/blob/main/model/pipeline.py
3. PyTorch maintainers on Blackwell/RTX 50-series CUDA 12.8 wheels:
   https://discuss.pytorch.org/t/cuda-support-for-rtx-50x-on-windows/221309
   https://discuss.pytorch.org/t/pytorch-support-for-sm-120-nvidia-geforce-rtx-5060/220941
4. Clothes parsing model, class labels and license reference:
   https://huggingface.co/mattmdjaga/segformer_b2_clothes
5. SD 1.5 inpainting model:
   https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting
6. Fine-tuned VAE model:
   https://huggingface.co/stabilityai/sd-vae-ft-mse
7. Trusted local HTTPS certificate setup:
   https://github.com/FiloSottile/mkcert

Upstream reported performance is not this implementation's RTX 5060 benchmark.
The Windows-friendly mask path, offload strategy, resolutions and system overhead
are different; this package must be measured independently.

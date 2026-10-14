# Target-machine acceptance checklist

Fill in during your demo preparation. Blank is intentionally not a success claim.

## Environment

- [ ] Windows version: __________
- [ ] GPU/VRAM from doctor: __________
- [ ] NVIDIA driver: __________
- [ ] Python/torch/torchvision/CUDA wheel versions: __________
- [ ] RAM / free disk: __________
- [ ] Pinned model download complete and licenses reviewed
- [ ] CUDA kernel test passes
- [ ] `python -m pytest -q` passes locally

## Camera

- [ ] Local webcam frame captured
- [ ] Phone source and transport: __________
- [ ] Portrait/landscape orientation checked
- [ ] Same-Wi-Fi connection stable for 5 minutes
- [ ] Disconnect/reconnect tested; stale frames rejected
- [ ] Preview remains responsive during generation
- [ ] No public relay or external image upload enabled

## Real model validation

| Case | Mask reviewed | Cold total (s) | Warm diffusion (s) | Peak allocated GB | Visual pass / failures |
|---|---|---|---|---|---|
| Plain top | | | | | |
| Patterned / long-sleeved top | | | | | |
| Trousers / skirt | | | | | |
| Short dress | | | | | |
| Long dress | | | | | |

For every case:
- [ ] Old garment fully replaced where intended; no pasted photo edges
- [ ] Body/pose appearance plausible; no new missing limbs
- [ ] Overlapping hands/face/hair preserved where required
- [ ] Patterns, neckline and hem compared against the reference garment
- [ ] Mask boundary seams checked at 100% zoom
- [ ] Input dimensions preserved and no unwanted crop
- [ ] Original pixels outside mask preserved
- [ ] Failures disclosed; appearance simulation not sold as accurate size/fit

## Integration / privacy

- [ ] Member 1 receives BGR frames on a worker and updates Qt through signals
- [ ] Member 2 supplies real local image paths + explicit try-on categories
- [ ] Stale generation is shown with its matching captured person frame
- [ ] No multiple service/GPU workers
- [ ] Queue overload and cancellation UX tested
- [ ] Final photos/benchmarks removed after demo if no longer needed

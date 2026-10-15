# Attribution, license and model-use notes

This is an academic/non-commercial research integration. A model being downloadable
or called "open source" does not automatically permit commercial use.

## Bundled inference code

**CatVTON: Concatenation Is All You Need for Virtual Try-On with Diffusion Models**,
by the CatVTON authors (Zheng-Chong/CatVTON upstream project), ICLR 2025.

- Repository: https://github.com/Zheng-Chong/CatVTON
- Paper: https://arxiv.org/abs/2407.15886
- License: **Creative Commons Attribution-NonCommercial-ShareAlike 4.0**.
- Full upstream license: `edgeai/vendor/catvton/LICENSE` (also project-root LICENSE).
- Copied files: model/pipeline.py, model/utils.py, model/attn_processor.py, utils.py,
  the upstream NSFW replacement image and license.
- Original hashes and commit: `docs/upstream.json`.
- Modifications: namespaced imports and configurable local VAE path; these modifications
  are marked in the manifest. Other wrapper/UI/test files are new integration work.

The new integration is provided under the same CC BY-NC-SA 4.0 terms. Retain attribution,
indicate modifications, and follow ShareAlike/NonCommercial terms when redistributing.
No claim of authorship over CatVTON or its training data is made.

## Downloaded weights (not included in the ZIP)

| Component | Repository / terms to review |
|---|---|
| CatVTON mixed attention | https://huggingface.co/zhengchong/CatVTON — CC BY-NC-SA 4.0 |
| SD 1.5 inpainting base | https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-inpainting — CreativeML Open RAIL-M |
| VAE ft-MSE | https://huggingface.co/stabilityai/sd-vae-ft-mse — model card labels MIT; review full upstream terms |
| Clothes SegFormer B2 | https://huggingface.co/mattmdjaga/segformer_b2_clothes — model card labels `other` and refers to NVIDIA SegFormer license |

SegFormer license reference: https://github.com/NVlabs/SegFormer/blob/master/LICENSE .
Review the actual NVIDIA source/model terms and dataset restrictions; do not relabel
this parser as MIT/Apache. The downloader explicitly asks you to review research terms.
Manual masks let you avoid using the parser if its terms do not meet your needs.

Optional MediaPipe pose model and Python dependencies have their own licenses:
https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker .
PyQt6 is optional; review its GPL/commercial terms for distribution of the teammate GUI.

Model commits are pinned in `models.lock.json`. Downloaded model cards are retained
alongside the weights. These notes are a practical attribution guide, not legal advice
or a substitute for checking the original licenses and data/image permissions.

## Image consent and representation

Use consenting subjects and images you have permission to process. No faces, product
photos or copyrighted retail datasets are bundled as demo assets. Generated images are
appearance simulations; don't present them as guaranteed fit or unaltered photographs.


## User-provided team catalog code

The integrated `clothing_pipeline` derives from the user-provided Virtual-TryOn
repository/branch recorded in `docs/catalog/upstream.json`. The reviewed branch has
no explicit LICENSE file; its README's "MIT (or choose your own)" is not treated as
a confirmed MIT license. Preserve team attribution and obtain explicit permission
before public redistribution/commercial use. No project-root license claim overrides
those original rights or retailer image rights.

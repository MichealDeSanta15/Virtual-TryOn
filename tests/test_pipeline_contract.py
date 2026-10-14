"""Check our vendored constructor contract without torch, CUDA or model downloads."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pipeline_constructor():
    tree = ast.parse((ROOT / 'edgeai/vendor/catvton/model/pipeline.py').read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'CatVTONPipeline')
    return next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')


def test_engine_keywords_match_vendored_constructor():
    constructor = pipeline_constructor()
    accepted = {arg.arg for arg in constructor.args.args + constructor.args.kwonlyargs}
    engine = ast.parse((ROOT / 'edgeai/engine.py').read_text())
    calls = [node for node in ast.walk(engine) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == 'CatVTONPipeline']
    assert calls, 'Expected engine to instantiate the vendored CatVTON pipeline'
    for call in calls:
        provided = {keyword.arg for keyword in call.keywords if keyword.arg is not None}
        assert provided <= accepted, f'Unsupported pipeline arguments: {provided - accepted}'


def test_local_vae_parameter_is_used_by_loader():
    constructor = pipeline_constructor()
    positional = [arg.arg for arg in constructor.args.args]
    defaults = dict(zip(positional[-len(constructor.args.defaults):], constructor.args.defaults))
    assert 'vae_ckpt' in defaults, 'Local VAE loading needs a declared constructor parameter'
    assert ast.literal_eval(defaults['vae_ckpt']) == 'stabilityai/sd-vae-ft-mse'
    loaders = [node for node in ast.walk(constructor) if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Attribute) and node.func.attr == 'from_pretrained'
               and isinstance(node.func.value, ast.Name) and node.func.value.id == 'AutoencoderKL']
    assert len(loaders) == 1
    assert isinstance(loaders[0].args[0], ast.Name)
    assert loaders[0].args[0].id == 'vae_ckpt'


def test_pipeline_passes_execution_device_to_every_vae_encoder_call():
    tree = ast.parse((ROOT / 'edgeai/vendor/catvton/model/pipeline.py').read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == 'compute_vae_encodings']
    assert len(calls) == 4, 'Both standard and Pix2Pix paths must use the explicit execution device'
    for call in calls:
        keyword = next((k for k in call.keywords if k.arg == 'execution_device'), None)
        assert keyword is not None
        assert ast.unparse(keyword.value) == 'self.device'

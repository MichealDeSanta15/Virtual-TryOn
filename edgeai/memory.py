"""Whole-model phase placement: no per-layer transfers during the denoising loop."""
import time


class StagedPlacement:
    STAGES = {'encode': 'vae', 'denoise': 'unet', 'decode': 'vae', 'safety': 'safety_checker'}

    def __init__(self, pipeline, execution_device='cuda'):
        import torch
        self.device = torch.device(execution_device)
        self.modules = {name: getattr(pipeline, name, None)
                        for name in ('vae', 'unet', 'safety_checker')}
        self.active = None
        self.stage = None
        self.started = None
        self.timings = {}
        self.transfer_seconds = 0.0

    def _sync(self):
        if self.device.type == 'cuda':
            import torch
            torch.cuda.synchronize(self.device)

    def _end_stage(self):
        if self.started is not None:
            self._sync()
            self.timings[self.stage] = self.timings.get(self.stage, 0.0) + time.perf_counter() - self.started
            self.started = None

    def reset_metrics(self):
        if self.active is not None:
            raise RuntimeError('Release the previous staged request before starting a new one')
        self.timings = {}
        self.transfer_seconds = 0.0

    def activate(self, stage):
        target = self.STAGES[stage]
        module = self.modules[target]
        if module is None:
            raise RuntimeError(f'Pipeline has no {target} for stage {stage}')
        self._end_stage()
        begin = time.perf_counter()
        if self.active != target:
            # Evict before loading: do not overlap VAE/UNet weights on the GPU.
            if self.active is not None:
                self.modules[self.active].to('cpu')
                self.active = None
            try:
                module.to(self.device)
            except Exception:
                # Recover partially moved modules after an allocation failure.
                module.to('cpu')
                raise
            self.active = target
        self._sync()
        self.transfer_seconds += time.perf_counter() - begin
        self.stage = stage
        self.started = time.perf_counter()

    def release(self):
        """Call in finally, including when inference/OOM/safety checking fails."""
        self._end_stage()
        begin = time.perf_counter()
        if self.active is not None:
            self.modules[self.active].to('cpu')
            self.active = None
        self._sync()
        self.transfer_seconds += time.perf_counter() - begin
        self.stage = None

    def metrics(self):
        return {'stage_seconds': {name: round(value, 3) for name, value in self.timings.items()},
                'weight_transfer_seconds': round(self.transfer_seconds, 3)}

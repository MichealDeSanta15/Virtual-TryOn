"""Member 1: pip install PyQt6, then import TryOnBridge in your existing GUI.

Start main.py separately. Keep a bridge reference on your window (self.tryon).
Signals are delivered to Qt slots on the GUI thread; no model is loaded in Qt.
"""
import os
from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot
from edgeai.client import EdgeAIClient


class TaskSignals(QObject):
    result=pyqtSignal(object,dict)
    error=pyqtSignal(str)
    stage=pyqtSignal(str)
    finished=pyqtSignal()


class TryOnTask(QRunnable):
    def __init__(self,url,token,frame,product,category,mask,preset):
        super().__init__()
        self.signals=TaskSignals()
        self.url,self.token=url,token
        self.frame=frame.copy()
        self.product=dict(product)
        self.category,self.mask,self.preset=category,mask.copy() if mask is not None else None,preset

    @pyqtSlot()
    def run(self):
        client=EdgeAIClient(self.url,self.token)
        try:
            job=client.submit(self.frame,self.product['image_path'],category=self.category,mask=self.mask,preset=self.preset)
            frame,metrics=client.wait(job,progress=self.signals.stage.emit)
            self.signals.result.emit(frame,metrics)
        except Exception as exc:self.signals.error.emit(str(exc))
        finally:
            client.close();self.signals.finished.emit()


class TryOnBridge(QObject):
    result_ready=pyqtSignal(object,dict)  # BGR uint8 same dimensions as captured input
    error=pyqtSignal(str)
    stage=pyqtSignal(str)
    busy_changed=pyqtSignal(bool)

    def __init__(self,url='http://127.0.0.1:8000',token=None,parent=None):
        super().__init__(parent)
        self.url=url;self.token=token or os.environ['EDGEAI_TOKEN']
        self.pool=QThreadPool(self);self.pool.setMaxThreadCount(1)
        self.busy=False;self.task=None

    def submit(self,frame,product,category='upper',mask=None,preset='draft'):
        if self.busy:
            self.error.emit('A try-on is already running. Keep the live preview separate.');return
        self.busy=True;self.busy_changed.emit(True)
        task=TryOnTask(self.url,self.token,frame,product,category,mask,preset)
        task.signals.result.connect(self.result_ready)
        task.signals.error.connect(self.error)
        task.signals.stage.connect(self.stage)
        task.signals.finished.connect(self._finished)
        self.task=task;self.pool.start(task)

    @pyqtSlot()
    def _finished(self):
        self.busy=False;self.busy_changed.emit(False);self.task=None

# Integration in your window (not executed here):
# self.tryon = TryOnBridge(token="paste terminal token", parent=self)
# self.tryon.result_ready.connect(self.show_generated_snapshot)
# self.tryon.error.connect(self.show_error)
# self.tryon.submit(captured_bgr_frame, product, category="upper")
# QImage(rgb.data,w,h,rgb.strides[0],QImage.Format.Format_RGB888).copy()
# Copy QImage data to avoid freed NumPy buffers after the slot returns.

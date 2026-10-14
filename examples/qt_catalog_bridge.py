"""Member 1: replace mock catalog results with the real service, on a Qt worker.

Requires the optional PyQt6 GUI dependency. Do not run this on the GUI thread.
The result includes products AND per-source failures; show both in the UI.
"""
from PyQt6.QtCore import QThread, pyqtSignal
from edgeai.client import EdgeAIClient

class CatalogWorker(QThread):
    results_ready=pyqtSignal(dict)
    error_occurred=pyqtSignal(str)
    stage=pyqtSignal(str)

    def __init__(self,url,token,event,budget,live=True,source=None,parent=None):
        super().__init__(parent)
        self.url,self.token=url,token
        self.event,self.budget,self.live,self.source=event,budget,live,source

    def run(self):
        client=EdgeAIClient(self.url,self.token)
        try:
            job=client.search_catalog(self.event,self.budget,live=self.live,source=self.source)
            self.results_ready.emit(client.wait_catalog(job,progress=self.stage.emit))
        except Exception as exc:self.error_occurred.emit(str(exc))
        finally:client.close()

# Do not fall back to colored cards or MockTryOnWorker on an error.
# To select a product: client.select_catalog_product(product['id']) returns a
# garment asset ID plus try-on category. Use that asset in POST /api/jobs with
# your captured-person and reviewed-mask asset IDs. See docs/CATALOG_INTEGRATION.md.

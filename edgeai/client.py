"""Synchronous HTTP client: use from a Qt worker, not the GUI event loop."""
from io import BytesIO
import time
import httpx
from PIL import Image
from .imaging import bgr_to_pil, pil_to_bgr, load_rgb


class EdgeAIClient:
    def __init__(self, url, token, verify=True):
        self.http=httpx.Client(base_url=url.rstrip('/'),headers={'Authorization':'Bearer '+token},
                               timeout=120,verify=verify)

    def _json(self,method,path,**kwargs):
        r=self.http.request(method,path,**kwargs)
        if r.is_error:
            try:detail=r.json().get('detail',r.text)
            except ValueError:detail=r.text
            raise RuntimeError(str(detail))
        return r.json()

    def upload(self,image,mask=False):
        data=BytesIO();image.save(data,format='PNG')
        return self._json('POST','/api/assets',params={'mask':str(mask).lower()},
                          files={'file':('image.png',data.getvalue(),'image/png')})['id']

    def submit(self,frame,garment_path,category='upper',mask=None,preset='draft',seed=42):
        person=self.upload(bgr_to_pil(frame));garment=self.upload(load_rgb(garment_path))
        mask_id=self.upload(mask,True) if mask is not None else None
        return self._json('POST','/api/jobs',json={'person':person,'garment':garment,'mask':mask_id,
                           'category':category,'preset':preset,'seed':seed})['id']

    def wait(self,job_id,progress=None,timeout=1800):
        start=time.monotonic()
        while time.monotonic()-start<timeout:
            job=self._json('GET','/api/jobs/'+job_id)
            if progress:progress(job['state'])
            if job['state']=='done':
                r=self.http.get('/api/assets/'+job['result']['image']);r.raise_for_status()
                image=Image.open(BytesIO(r.content)).convert('RGB')
                return pil_to_bgr(image),job['result']['metrics']
            if job['state'] in ('failed','cancelled'):
                raise RuntimeError(job['error'] or 'Job cancelled')
            time.sleep(.5)
        raise TimeoutError('Waiting timed out; the job may still be running. Cancel it explicitly if needed.')

    def prepare_garment(self, garment, category="upper", mask=None):
        """Prepare an uploaded SOURCE asset; optional mask is reference-photo geometry."""
        return self._json('POST','/api/garments/prepare',json={
            'garment':garment,'category':category,'mask':mask})['id']

    def wait_garment(self, job_id, progress=None, timeout=180):
        """Returns preview/mask asset IDs. The caller must show them for human review."""
        start=time.monotonic()
        while time.monotonic()-start < timeout:
            job=self._json('GET','/api/garments/prepare/'+job_id)
            if progress: progress(job['state'])
            if job['state']=='done': return job['result']
            if job['state'] in ('failed','cancelled'):
                raise RuntimeError(job['error'] or 'Garment preparation cancelled')
            time.sleep(.5)
        raise TimeoutError('Garment preparation may still be running; poll the same job ID again')

    def search_catalog(self, event, budget="5000", live=True, source=None, **filters):
        """Submit a catalog search. Poll from a worker; no image is sent to retailers."""
        return self._json('POST','/api/catalog/search',json={
            'event':event,'budget':str(budget),'live':live,'source':source,**filters})['id']

    def wait_catalog(self, job_id, progress=None, timeout=180):
        start=time.monotonic()
        while time.monotonic()-start < timeout:
            job=self._json('GET','/api/catalog/search/'+job_id)
            if progress:progress(job['state'])
            if job['state']=='done':return job['result']
            if job['state'] in ('failed','cancelled'):raise RuntimeError(job['error'] or 'Search cancelled')
            time.sleep(.5)
        raise TimeoutError('Catalog polling timed out; the service may still be finishing the search')

    def select_catalog_product(self, product_id):
        return self._json('POST',f'/api/catalog/products/{int(product_id)}/select')

    def cancel(self,job_id):return self._json('DELETE','/api/jobs/'+job_id)
    def capture(self):return self._json('POST','/api/camera/capture')['id']
    def close(self):self.http.close()

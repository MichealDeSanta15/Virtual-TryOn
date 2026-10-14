import argparse
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from edgeai.config import Settings
from clothing_pipeline.api import ClothingPipeline
from clothing_pipeline.importer import import_manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest');args=p.parse_args()
    s=Settings.from_env();root=s.data_dir/'catalog'
    pipe=ClothingPipeline(root/'products.db',root/'images')
    ids=import_manifest(args.manifest,pipe)
    print(f'Imported {len(ids)} real-image catalog entries into {root}. Select Local catalog in the studio.')

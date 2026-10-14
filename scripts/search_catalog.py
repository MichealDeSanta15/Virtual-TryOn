"""Live-first CLI search; --saved is explicit. Metadata output never asserts store availability."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from clothing_pipeline.api import ClothingPipeline
from edgeai.config import Settings
from clothing_pipeline.scraper.sources import ALL_SOURCES

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('query');p.add_argument('--budget',default='5000');p.add_argument('--source',choices=ALL_SOURCES)
 mode=p.add_mutually_exclusive_group()
 mode.add_argument('--live',dest='live',action='store_true',help='Fetch fresh products (default)')
 mode.add_argument('--saved',dest='live',action='store_false',help='Search saved observations; no network')
 p.set_defaults(live=True)
 p.add_argument('--refresh',action='store_true',help='Compatibility option; live always refreshes')
 p.add_argument('--limit',type=int,default=12)
 args=p.parse_args();s=Settings.from_env();root=s.data_dir/'catalog'
 report=ClothingPipeline(root/'products.db',root/'images').search_report(args.query,args.budget,source=args.source,
             scrape_if_empty=args.live,refresh=args.refresh,limit=args.limit)
 print(json.dumps(report,indent=2,ensure_ascii=False))

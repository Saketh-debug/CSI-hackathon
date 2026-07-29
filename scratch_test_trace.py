import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "streamlit-demo"))

import osmnx as ox
import config
import traceback

GRAPH_CACHE_DIR = Path(__file__).resolve().parent / "streamlit-demo" / "data"
cache_file = GRAPH_CACHE_DIR / "road_graph_test.graphml"

try:
    print("Downloading graph...")
    G = ox.graph_from_point(
        (config.CENTER_LAT, config.CENTER_LON),
        dist=8000,
        network_type='drive',
        simplify=True,
    )
    print("Saving graph via save_graphml...")
    ox.save_graphml(G, str(cache_file))
    print("Saved successfully!")
except Exception as e:
    traceback.print_exc()

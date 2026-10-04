import sys
import os

# Add root directory to sys.path so server, database, scraper can be imported
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Set VERCEL environment flag
os.environ["VERCEL"] = "1"

from server import app

# Vercel entry point
export_app = app

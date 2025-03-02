import os
import sys

# Get absolute path to project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Also add the generate_stories directory
GENERATE_STORIES_PATH = os.path.join(PROJECT_ROOT, "generate_stories")
if GENERATE_STORIES_PATH not in sys.path:
    sys.path.insert(0, GENERATE_STORIES_PATH)
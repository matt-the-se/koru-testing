"""
Input Processing Package

This package contains scripts for processing input data, including chunking response texts 
and preparing data for downstream analysis.
"""

# Import shared resources or modules
from config import DB_CONFIG, LOGGING_CONFIG

# Set up logging for the package
import logging
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Expose key functionalities
from .input_chunker import chunk_text, process_test_run
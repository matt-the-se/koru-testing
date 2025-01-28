"""
Classifier Package

This package contains scripts for classification and related tasks, 
including manual classification export/import and text chunk classification.
"""

# Import shared resources or modules to make them easily accessible
from config import DB_CONFIG, LOGGING_CONFIG

# Optionally, set up logging for the package
import logging
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Expose key functionalities directly
from .input_classifier import classify_chunk
from .manual_class_export import export_to_csv
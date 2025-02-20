"""
Input Processing Package

This package contains scripts for processing input data, including chunking response texts 
and preparing data for downstream analysis.
"""

# Expose key functionalities
from .test_run_processing import process_test_run
from .keyword_matcher import match_keywords
from .clarity_score_calc import calculate_clarity_score

__all__ = ['process_test_run', 'match_keywords', 'calculate_clarity_score']
import os
import sys
import importlib
from pathlib import Path
from config import INPUT_PROCESSING_DIR, INPUT_CLASSIFIER_DIR, GENERATE_STORIES_DIR

# Get base directory and construct paths
BASE_DIR = Path(__file__).parent.parent

def safe_import(module_path):
    """Safely import a module given its path"""
    try:
        # Get the directory and module name
        module_dir = os.path.dirname(module_path)
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        
        # Add module directory to path if not already there
        if module_dir not in sys.path:
            sys.path.append(module_dir)
        
        # Create spec and load module
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return module
    except Exception as e:
        print(f"Error importing {module_path}: {e}")
        return None
    finally:
        # Clean up sys.path
        if module_dir in sys.path:
            sys.path.remove(module_dir)

# Add core platform paths at runtime
def run_input_processor(logger, test_run_id):
    """Run the input processor module"""
    logger.info("Starting input processing...")
    sys.path.append(INPUT_PROCESSING_DIR)
    test_run_processing_path = os.path.join(INPUT_PROCESSING_DIR, 'test_run_processing.py')
    spec = importlib.util.spec_from_file_location(
        "test_run_processing", test_run_processing_path
    )
    test_run_processing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(test_run_processing)
    test_run_processing.process_test_run(logger, test_run_id)

def run_keyword_matcher(test_run_id):
    sys.path.append(INPUT_PROCESSING_DIR)
    keyword_matcher_path = os.path.join(INPUT_PROCESSING_DIR, 'keyword_matcher.py')
    spec = importlib.util.spec_from_file_location("keyword_matcher", keyword_matcher_path)
    keyword_matcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(keyword_matcher)
    return keyword_matcher.match_keywords(test_run_id)

def run_input_classifier(test_run_id):
    sys.path.append(INPUT_CLASSIFIER_DIR)
    classifier_path = os.path.join(INPUT_CLASSIFIER_DIR, 'input_classifier.py')
    spec = importlib.util.spec_from_file_location("input_classifier", classifier_path)
    input_classifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(input_classifier)
    return input_classifier.process_test_run(test_run_id)

def calculate_clarity(test_run_id):
    sys.path.append(INPUT_PROCESSING_DIR)
    clarity_path = os.path.join(INPUT_PROCESSING_DIR, 'clarity_score_calc.py')
    spec = importlib.util.spec_from_file_location("clarity_score_calc", clarity_path)
    clarity_score_calc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clarity_score_calc)
    return clarity_score_calc.calculate_clarity_score(test_run_id)

def run_story_generation(persona_id, test_run_id):
    """Run the story generation module"""
    sys.path.append(GENERATE_STORIES_DIR)
    stories_path = os.path.join(GENERATE_STORIES_DIR, 'generate_stories.py')
    spec = importlib.util.spec_from_file_location("generate_stories", stories_path)
    generate_stories = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generate_stories)
    return generate_stories.generate_story(test_run_id, persona_id) 
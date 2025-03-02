from typing import Dict, Any
import sys
import os

# Handle imports differently based on how the file is being used
if __name__ == "__main__" or __package__ is None:
    # When run directly or from webapp
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from generate_stories.gs_db_utils import (
        get_foundation_data,
        get_inputs_data,
        get_clarity_scores,
        get_passion_scores
    )
else:
    # When imported as part of the package
    from .gs_db_utils import (
        get_foundation_data,
        get_inputs_data,
        get_clarity_scores,
        get_passion_scores
    )

def build_persona_profile(test_run_id: int, persona_id: int) -> Dict[str, Any]:
    """Build persona profile using new streamlined approach"""
    
    # Get foundation data
    foundation = get_foundation_data(persona_id)
    
    # Get inputs with their themes
    inputs = get_inputs_data(test_run_id)
    print(f"DEBUG: Found {len(inputs)} inputs for test_run_id {test_run_id}")
    
    # Get scores
    clarity_scores = get_clarity_scores(test_run_id)
    passion_scores = get_passion_scores(test_run_id)
    
    # Calculate theme confidences from inputs
    theme_confidences = {}
    for i, input_data in enumerate(inputs):
        print(f"DEBUG: Processing input {i+1}/{len(inputs)}, input_id: {input_data.get('input_id')}")
        if "extracted_themes" in input_data:
            print(f"DEBUG: Input has extracted_themes")
            # Get confidence scores from response_text
            response_text = input_data['extracted_themes'].get('response_text', {})
            print(f"DEBUG: response_text: {response_text}")
            response_confidences = response_text.get('confidence', {})
            print(f"DEBUG: response_confidences: {response_confidences}")
            for theme, conf in response_confidences.items():
                if conf > 0.3:  # Use a reasonable threshold
                    if theme not in theme_confidences:
                        theme_confidences[theme] = []
                    theme_confidences[theme].append(conf)
            
            # Also check chunk-level themes
            chunks = input_data['extracted_themes'].get('chunks', [])
            print(f"DEBUG: Found {len(chunks)} chunks")
            for chunk in chunks:
                chunk_confidences = chunk.get('confidence', {})
                print(f"DEBUG: chunk_confidences: {chunk_confidences}")
                for theme, conf in chunk_confidences.items():
                    if conf > 0.3:  # Use the same threshold
                        if theme not in theme_confidences:
                            theme_confidences[theme] = []
                        theme_confidences[theme].append(conf)
    
    print(f"DEBUG: theme_confidences before averaging: {theme_confidences}")
    
    # Average confidences
    theme_confidences = {
        theme: sum(confs) / len(confs)
        for theme, confs in theme_confidences.items()
    }
    
    print(f"DEBUG: Final theme_confidences: {theme_confidences}")
    
    # Sort themes by confidence for primary/secondary selection
    sorted_themes = sorted(theme_confidences.items(), key=lambda x: x[1], reverse=True)
    print(f"DEBUG: sorted_themes: {sorted_themes}")
    primary_theme = sorted_themes[0][0] if sorted_themes else None
    secondary_themes = [t[0] for t in sorted_themes[1:3]] if len(sorted_themes) > 1 else []
    
    print(f"DEBUG: primary_theme: {primary_theme}, secondary_themes: {secondary_themes}")
    
    return {
        "foundation": foundation,
        "inputs": inputs,
        "theme_confidences": theme_confidences,
        "clarity_scores": clarity_scores,
        "passion_scores": passion_scores,
        "test_run_id": test_run_id,
        "persona_id": persona_id,
        "primary_theme": primary_theme,
        "secondary_themes": secondary_themes
    } 
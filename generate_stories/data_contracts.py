"""
Define expected data structures for all components
"""

FOUNDATION_SCHEMA = {
    "name": str,
    "age": int,
    "pronoun": str,
    "location": str,
    "relationship": str,
    "children": str,
    "pets": str
}

INPUT_SCHEMA = {
    "input_id": int,
    "response_text": str,
    "prompt_theme": str,
    "extracted_themes": {
        "chunks": list,
        "response_text": dict,
        "aggregated": dict
    },
    "response_stats": dict,
    "chunk_scores": list
}

PERSONA_DATA_SCHEMA = {
    "foundation": FOUNDATION_SCHEMA,
    "inputs": [INPUT_SCHEMA],
    "theme_confidences": dict,
    "passion_scores": dict,
    "clarity_scores": dict,
    "test_run_id": int,
    "persona_id": int
}

CONTENT_BUILDER_OUTPUT_SCHEMA = {
    "primary_theme": str,
    "secondary_themes": list,
    "theme_weights": dict,
    "passion_inputs": list,
    "story_elements": {
        "setting": dict,
        "characters": list,
        "activities": list,
        "emotional_moments": list
    }
} 
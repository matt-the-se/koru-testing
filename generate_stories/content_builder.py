import random
from typing import Dict, Any, List
import sys
import os

# Handle imports differently based on how the file is being used
if __name__ == "__main__" or __package__ is None:
    # When run directly or from webapp
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from generate_stories.gs_utils import validate_persona_data
    from generate_stories.data_contracts import CONTENT_BUILDER_OUTPUT_SCHEMA
else:
    # When imported as part of the package
    from .gs_utils import validate_persona_data
    from .data_contracts import CONTENT_BUILDER_OUTPUT_SCHEMA

class ContentBuilder:
    def __init__(self, persona_data: Dict[str, Any]):
        validate_persona_data(persona_data)
        self.persona_data = persona_data
        print(f"DEBUG ContentBuilder: persona_data keys: {list(persona_data.keys())}")
        print(f"DEBUG ContentBuilder: theme_confidences: {persona_data.get('theme_confidences', {})}")
        
    def build(self) -> Dict[str, Any]:
        """Build content guidance for story generation"""
        theme_emphasis = self._calculate_theme_emphasis()
        passionate_inputs = self._find_passionate_inputs()
        emotional_tone = self._extract_emotional_tone()
        
        print(f"DEBUG ContentBuilder.build: theme_emphasis: {theme_emphasis}")
        
        return {
            "foundation": self.persona_data["foundation"],
            "theme_emphasis": theme_emphasis,
            "passionate_inputs": passionate_inputs,
            "emotional_tone": emotional_tone,
            "style_guidance": {
                "pacing": "natural",
                "perspective": "intimate",
                "tone": "warm"
            }
        }

    def _calculate_theme_emphasis(self) -> Dict[str, float]:
        """Calculate relative emphasis for themes without strict weights"""
        emphasis = {}
        print(f"DEBUG _calculate_theme_emphasis: theme_confidences: {self.persona_data.get('theme_confidences', {})}")
        for theme in self.persona_data["theme_confidences"]:
            # Combine signals to determine emphasis
            confidence = self.persona_data["theme_confidences"][theme]
            passion = self._get_theme_passion(theme)
            clarity = self._get_theme_clarity(theme)
            
            # Higher emphasis means "lean into this theme more"
            emphasis[theme] = (confidence + passion + clarity) / 3
            
        print(f"DEBUG _calculate_theme_emphasis: final emphasis: {emphasis}")
        return emphasis

    def _find_passionate_inputs(self) -> List[Dict[str, Any]]:
        """Find inputs with high passion scores"""
        inputs = []
        for input_data in self.persona_data["inputs"]:
            passion_score = self.persona_data["passion_scores"].get(input_data["input_id"], 0)
            if passion_score > 0.7:
                inputs.append({
                    "content": input_data["response_text"],
                    "theme": input_data["prompt_theme"],
                    "intensity": passion_score
                })
        return inputs

    def _extract_emotional_tone(self) -> Dict[str, Any]:
        """Extract overall emotional guidance"""
        foundation = self.persona_data["foundation"]
        return {
            "setting": {
                "location": foundation["location"],
                "familiarity": "intimate"  # The story should feel personal
            },
            "relationships": {
                "family": bool(foundation["children"]),
                "partnership": foundation["relationship"] == "married",
                "pets": bool(foundation["pets"])
            }
        }

    def _get_theme_passion(self, theme: str) -> float:
        """Calculate passion score for a theme"""
        theme_inputs = [
            input_data for input_data in self.persona_data["inputs"]
            if input_data["prompt_theme"] == theme
        ]
        
        if not theme_inputs:
            return 0.0
            
        passion_scores = [
            self.persona_data["passion_scores"].get(input_data["input_id"], 0)
            for input_data in theme_inputs
        ]
        
        return sum(passion_scores) / len(passion_scores)

    def _get_theme_clarity(self, theme: str) -> float:
        """Calculate clarity score for a theme"""
        if theme in self.persona_data.get("clarity_scores", {}).get("theme_contributions", {}):
            clarity_components = self.persona_data["clarity_scores"]["theme_contributions"][theme]
            return (
                clarity_components["aggregate"] * 0.2 +
                clarity_components["complete_response"] * 0.1 +
                clarity_components["chunks"] * 0.1
            )
        return 0.0

    def build_story_prompt(self, content: Dict[str, Any]) -> str:
        foundation = content["foundation"]
        emphasis = content["theme_emphasis"]
        inputs = content["passionate_inputs"]
        tone = content["emotional_tone"]
        
        print(f"DEBUG build_story_prompt: emphasis: {emphasis}")
        
        # Get available themes and ensure we have at least one
        top_themes = sorted(emphasis.items(), key=lambda x: x[1], reverse=True)
        print(f"DEBUG build_story_prompt: top_themes: {top_themes}")
        if not top_themes:
            print("DEBUG build_story_prompt: No themes available to build story prompt")
            raise ValueError("No themes available to build story prompt")
        
        # Select up to 2 themes, but handle cases with fewer themes
        num_themes = min(2, len(top_themes))
        selected_themes = random.sample(top_themes, num_themes)
        
        # If we only have 1 theme, duplicate it as secondary theme
        if len(selected_themes) == 1:
            selected_themes = [selected_themes[0], selected_themes[0]]
        
        # Randomize sensory examples
        sensory_examples = [
            "You wake up to the gentle sound of waves",
            "The morning breeze carries the scent of coffee",
            "Your children's laughter fills the kitchen",
            "The warm sand shifts between your toes",
            "Sunlight dances across your bedroom walls"
        ]
        selected_examples = random.sample(sensory_examples, 2)
        
        prompt = f"""Tell an intimate day-in-the-life story about {foundation['name']}'s perfect day, using present tense and "you" perspective. For example:
- "{selected_examples[0]}"
- "{selected_examples[1]}"

The story should naturally emphasize {selected_themes[0][0]}, while weaving in elements of {selected_themes[1][0]}.

These moments matter deeply to them:"""

        # Add passionate inputs as inspiration
        for input_data in inputs:
            prompt += f"\n- {input_data['content']}"

        prompt += f"""

Make the reader feel present in each moment with {foundation['name']}, sharing their day with their {foundation['children']}, their partner, and {foundation['pets']}. Use sensory details and emotional moments to make their world come alive.

Remember to maintain present tense and "you" perspective throughout, creating an intimate experience as if we're right there with them in their {foundation['location']} home."""

        return prompt

    # Helper methods for story elements... 
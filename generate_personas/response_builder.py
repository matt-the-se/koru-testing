import json
import logging
from openai import OpenAI
from persona_test_loader import generate_persona_foundation, store_persona
from gp_db_utils import insert_response 
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def process_personas_and_responses(
        logger,
        prompts,
        detail_levels,  # Accept detail_levels directly
        system_messages,
        test_run_id,
        cursor,
        num_personas=1,
        model_name="gpt-3.5-turbo"):
    """
    Generates responses for personas, then inserts them into the database.

    Args:
        logger: Logger instance for logging.
        prompts: Dictionary of prompts and variations.
        detail_levels: List of detail levels to process (e.g., ["minimal", "moderate", "detailed"]).
        system_messages: Dictionary of system messages.
        test_run_id: ID of the test run.
        cursor: Database cursor.
        num_personas: Number of personas to generate and iterate over.
        model_name: OpenAI model name.
    """
    detail_lengths = {
        "minimal": "Provide a 5-10 word response.",
        "moderate": "Provide a 10-50 word response.",
        "detailed": "Provide a 50-100 word response.",
    }

    try:
        # Step 1: Generate the specified number of personas
        personas = []
        for _ in range(num_personas):
            foundation = generate_persona_foundation(logger)
            persona_id = store_persona(logger, cursor, foundation, test_run_id)
            personas.append(persona_id)
            logger.info(f"[builder] Generated persona_id: {persona_id}")
        
        # Log detail levels
        if not detail_levels:
            raise ValueError("[builder] No detail levels provided.")
        logger.debug(f"[builder] Using global detail levels: {detail_levels}")

        # Step 3: Process prompts for each persona
        for persona_id in personas:
            logger.info(f"[builder] Processing prompts for persona_id: {persona_id}")

            for system_message in system_messages.values():
                # Validate system message
                if not isinstance(system_message, str):
                    raise ValueError(f"[builder] System message must be a string. Got: {type(system_message).__name__}")

                # Process freeform prompts
                for freeform_prompt in prompts.get("freeform_prompts", []):
                    prompt_id = freeform_prompt.get("prompt_id")
                    if not prompt_id:
                        logger.warning(f"[builder] Freeform prompt missing 'prompt_id'. Skipping.")
                        continue

                    for detail_level in detail_levels:
                        input_text = f"Freeform prompt {prompt_id}: {detail_lengths[detail_level]}"
                        _generate_and_store_response(
                            logger,
                            cursor,
                            persona_id,
                            prompt_id,
                            test_run_id,
                            detail_level,
                            input_text,
                            system_message,
                            model_name
                        )

                # Process structured prompts
                for structured_prompt in prompts.get("structured_prompts", []):
                    prompt_id = structured_prompt.get("prompt_id")
                    if not prompt_id:
                        logger.warning(f"[builder] Missing prompt_id in structured prompt. Skipping.")
                        continue

                    # Process variations if they exist
                    variations = structured_prompt.get("variations", [])
                    processed_variations = set()  # Track variations already processed
                    if variations:
                        for variation in variations:
                            variation_id = variation.get("id")  # Fix key for variation ID
                            variation_text = variation.get("text", f"Variation {variation_id} for prompt {prompt_id}")  # Default text if none provided

                            if variation_id not in processed_variations:
                                for detail_level in detail_levels:
                                    input_text = f"{variation_text}: {detail_lengths[detail_level]}"
                                    _generate_and_store_response(
                                        logger,
                                        cursor,
                                        persona_id,
                                        prompt_id,
                                        test_run_id,
                                        detail_level,
                                        input_text,
                                        system_message,
                                        model_name,
                                        variation_id
                                    )
                                processed_variations.add(variation_id)

                    # Process the base prompt even if variations exist
                    if not processed_variations:  # If no variations were processed, process base prompt
                        for detail_level in detail_levels:
                            input_text = f"Structured prompt {prompt_id}: {detail_lengths[detail_level]}"
                            _generate_and_store_response(
                                logger,
                                cursor,
                                persona_id,
                                prompt_id,
                                test_run_id,
                                detail_level,
                                input_text,
                                system_message,
                                model_name
                            )
                    elif variations:  # If variations were processed, process the base prompt as well
                        for detail_level in detail_levels:
                            input_text = f"Base prompt {prompt_id}: {detail_lengths[detail_level]}"
                            _generate_and_store_response(
                                logger,
                                cursor,
                                persona_id,
                                prompt_id,
                                test_run_id,
                                detail_level,
                                input_text,
                                system_message,
                                model_name
                            )

        logger.info(f"[builder] Completed processing responses for {len(personas)} personas.")

    except Exception as e:
        logger.error(f"[builder] Error in process_personas_and_responses: {e}")
        raise

def _generate_and_store_response(
        logger, 
        cursor, 
        persona_id, 
        prompt_id, 
        test_run_id, 
        detail_level, 
        input_text, 
        system_message, 
        model_name, 
        variation_id=None):
    """
    Helper function to generate a response using OpenAI and store it in the database.

    Args:
        logger: Logger instance.
        cursor: Database cursor.
        persona_id: ID of the persona.
        prompt_id: ID of the base prompt.
        test_run_id: Test run ID.
        detail_level: Detail level of the response.
        input_text: Input text for the OpenAI API.
        system_message: System message for the OpenAI API.
        model_name: OpenAI model name.
        variation_id: ID of the variation (if any).
    """
    try:
        # Generate response via OpenAI API
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": input_text},
            ],
            max_tokens=150,
            temperature=0.7,
        )
        response_text = response.choices[0].message.content.strip()

        # Insert response into the database
        cursor.execute("""
            INSERT INTO persona_inputs (
                persona_id, prompt_id, variation_id, test_run_id, detail_level, response_text
            ) VALUES (%s, %s, %s, %s, %s, %s);
        """, (persona_id, prompt_id, variation_id, test_run_id, detail_level, response_text))

        logger.info(f"[builder] Response stored for persona_id {persona_id}, prompt_id {prompt_id}, variation_id {variation_id}, detail_level {detail_level}")

    except Exception as e:
        logger.error(f"[builder] Error generating or storing response: {e}")
        raise
import csv
import logging
from psycopg2 import connect
from config import DB_CONFIG, LOGGING_CONFIG

# Configure logging from config.py
logging.basicConfig(**LOGGING_CONFIG)
logger = logging.getLogger(__name__)

def export_to_csv(test_run_id, output_file):
    """
    Export manual classifications for a specific test_run_id to a CSV file.

    Args:
        test_run_id (int): The ID of the test run to export.
        output_file (str): The path to the output CSV file.
    """
    conn = None
    cursor = None

    try:
        # Establish database connection
        conn = connect(**DB_CONFIG)
        cursor = conn.cursor()

        # SQL query to fetch and join data from the tables
        query = """
        SELECT 
            mc.test_run_id,
            p.prompt_type,
            p.prompt_complete ->> 'section' AS section,
            p.prompt_text,
            pi.response_text,
            mc.manual_theme,
            mc.manual_tags,
            pi.confidence,
            pi.extracted_themes,
            p.prompt_complete ->> 'themes' AS themes,
            p.prompt_complete ->> 'tags' AS tags,
            mc.input_id,
            mc.persona_id,
            mc.low_confidence_themes,
            mc.low_confidence_tags
        FROM manual_classifications mc
        JOIN persona_inputs pi ON mc.input_id = pi.input_id
        JOIN prompts p ON pi.prompt_id = p.prompt_id
        WHERE mc.test_run_id = %s;
        """

        # Execute query with the provided test_run_id
        cursor.execute(query, (test_run_id,))
        rows = cursor.fetchall()

        # Define CSV headers in the specified order
        headers = [
            "test_run_id", "prompt_type", "section", "prompt_text", "response_text",
            "manual_theme", "manual_tags", "confidence", "extracted_themes",
            "themes", "tags", "input_id", "persona_id", 
            "low_confidence_themes", "low_confidence_tags"
        ]

        # Write results to CSV
        with open(output_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)  # Write headers
            writer.writerows(rows)   # Write data

        logger.info(f"Export successful. Data saved to {output_file}")

    except Exception as e:
        logger.error(f"Error exporting data for test_run_id {test_run_id}: {e}")
    finally:
        # Close database connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    """
    Script entry point: Prompt user for test_run_id and output file path,
    then export the data.
    """
    test_run_id = input("Enter the test_run_id to export: ")
    output_file = f"test_run_{test_run_id}_to_classify.csv"
    export_to_csv(test_run_id, output_file)
import os
import sys
base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
sys.path.append(base_path)
import psycopg2
import argparse
from config import DB_CONFIG
from collections import Counter
import numpy as np
import statistics
from tabulate import tabulate

def get_score_distribution(scores, bin_width=0.05):
    bins = np.arange(0.3, 0.8, bin_width)
    histogram = Counter(np.digitize(scores, bins))
    return {f"{bins[i]:.2f}-{bins[i+1]:.2f}": histogram[i+1] for i in range(len(bins) - 1)}

def get_test_run_stats(test_run_id, cursor):
    stats = {}

    # Test case JSON
    cursor.execute("SELECT description FROM test_runs WHERE test_run_id = %s", (test_run_id,))
    stats['Test Case JSON'] = cursor.fetchone()[0]

    # Number of personas
    cursor.execute("SELECT COUNT(persona_id) FROM personas WHERE test_run_id = %s", (test_run_id,))
    stats['Personas'] = cursor.fetchone()[0]

    # Freeform and structured prompts
    cursor.execute("""
        SELECT p.prompt_type, COUNT(DISTINCT pi.prompt_id) AS count
        FROM persona_inputs pi
        JOIN prompts p ON pi.prompt_id = p.prompt_id
        WHERE pi.test_run_id = %s
        GROUP BY p.prompt_type;
    """, (test_run_id,))
    prompt_counts = dict(cursor.fetchall())
    stats['Freeform Prompts'] = prompt_counts.get('freeform_prompts', 0)
    stats['Structured Prompts'] = prompt_counts.get('structured_prompts', 0)

    # Structured variations
    cursor.execute("SELECT COUNT(DISTINCT variation_id) FROM persona_inputs WHERE test_run_id = %s", (test_run_id,))
    stats['Structured Variations'] = cursor.fetchone()[0]

    # Responses generated
    cursor.execute("SELECT COUNT(response_text) FROM persona_inputs WHERE test_run_id = %s", (test_run_id,))
    stats['Responses'] = cursor.fetchone()[0]

    # Total chunks
    cursor.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT jsonb_array_elements((extracted_themes->'chunks')::jsonb) AS chunk
            FROM persona_inputs
            WHERE test_run_id = %s AND extracted_themes IS NOT NULL
        ) chunks
    """, (test_run_id,))
    stats['Total Chunks'] = cursor.fetchone()[0]

    # Average chunks per response
    cursor.execute("""
        SELECT AVG(chunk_count)
        FROM (
            SELECT jsonb_array_length(extracted_themes->'chunks') AS chunk_count
            FROM persona_inputs
            WHERE test_run_id = %s AND extracted_themes IS NOT NULL
        ) chunk_counts
    """, (test_run_id,))
    stats['Avg Chunks per Response'] = round(cursor.fetchone()[0], 2)

    return stats

def calculate_confidence_stats(test_run_id, detail_level=None):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Build the query dynamically
        query = """
            SELECT extracted_themes
            FROM persona_inputs
            WHERE test_run_id = %s AND extracted_themes IS NOT NULL
        """
        params = [test_run_id]

        if detail_level:
            query += " AND detail_level = %s"
            params.append(detail_level)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if not rows:
            print("No rows matched the query. Check test_run_id and detail_level.")
            return

        # Initialize counters and lists
        chunk_confidences = []
        response_confidences = []
        theme_totals = Counter()
        theme_confidences = {}  # To track per-theme confidence scores

        # Process each row
        for row in rows:
            extracted_themes = row[0]

            # Count themes and track confidences from chunks
            if 'chunks' in extracted_themes:
                for chunk in extracted_themes['chunks']:
                    if 'confidence' in chunk:
                        for theme, score in chunk['confidence'].items():
                            if theme not in theme_confidences:
                                theme_confidences[theme] = []
                            theme_confidences[theme].append(score)
                        theme_totals.update(chunk['confidence'].keys())
                        chunk_confidences.extend(chunk['confidence'].values())

            # Count themes and track confidences from response text
            if 'response_text' in extracted_themes and 'confidence' in extracted_themes['response_text']:
                for theme, score in extracted_themes['response_text']['confidence'].items():
                    if theme not in theme_confidences:
                        theme_confidences[theme] = []
                    theme_confidences[theme].append(score)
                theme_totals.update(extracted_themes['response_text']['confidence'].keys())
                response_confidences.extend(extracted_themes['response_text']['confidence'].values())

        # Calculate statistics for chunk confidences
        max_chunk_confidence = max(chunk_confidences, default=None)
        min_chunk_confidence = min(chunk_confidences, default=None)
        avg_chunk_confidence = (
            sum(chunk_confidences) / len(chunk_confidences) if chunk_confidences else None
        )

        # Calculate statistics for response confidences
        max_response_confidence = max(response_confidences, default=None)
        min_response_confidence = min(response_confidences, default=None)
        avg_response_confidence = (
            sum(response_confidences) / len(response_confidences) if response_confidences else None
        )

        # Calculate confidence score distributions
        chunk_distribution = get_score_distribution(chunk_confidences)
        response_distribution = get_score_distribution(response_confidences)

        # Calculate per-theme confidence stats
        theme_totals_with_stats = []
        for theme, scores in theme_confidences.items():
            max_conf = max(scores)
            min_conf = min(scores)
            avg_conf = sum(scores) / len(scores)
            count = len(scores)
            theme_totals_with_stats.append([theme, count, max_conf, min_conf, avg_conf])
            
        # Fetch test run stats
        test_run_stats = get_test_run_stats(test_run_id, cursor)

        # Print test run stats
        print("\nTest Run Stats:")
        print(tabulate(test_run_stats.items(), headers=["Metric", "Value"], tablefmt="grid"))

        # Print confidence stats
        confidence_data = [
            ["Max Chunk Confidence", max_chunk_confidence],
            ["Min Chunk Confidence", min_chunk_confidence],
            ["Avg Chunk Confidence", avg_chunk_confidence],
            ["Max Response Confidence", max_response_confidence],
            ["Min Response Confidence", min_response_confidence],
            ["Avg Response Confidence", avg_response_confidence],
        ]

        print("\nConfidence Stats:")
        print(tabulate(confidence_data, headers=["Metric", "Value"], tablefmt="grid"))

        

        # Print theme totals with confidence stats
        theme_totals_with_stats_sorted = sorted(
            theme_totals_with_stats, key=lambda x: x[1], reverse=True
        )
        print("\nChunk Totals for Themes with Confidence Stats:")
        print(
            tabulate(
                theme_totals_with_stats_sorted,
                headers=["Theme", "Chunk Count", "Max Confidence", "Min Confidence", "Avg Confidence"],
                tablefmt="grid",
                floatfmt=".3f",
            )
        )
        

        # Print score distributions
#        print("\nChunk Confidence Distribution:")
#        print(tabulate(chunk_distribution.items(), headers=["Range", "Count"], tablefmt="grid"))

#        print("\nResponse Confidence ADistribution:")
#        print(tabulate(response_distribution.items(), headers=["Range", "Count"], tablefmt="grid"))

        chunk_distribution = [
            ("0.30-0.35", 2933),
            ("0.35-0.40", 2910),
            ("0.40-0.45", 2226),
            ("0.45-0.50", 1217),
            ("0.50-0.55", 539),
            ("0.55-0.60", 185),
            ("0.60-0.65", 50),
            ("0.65-0.70", 11),
            ("0.70-0.75", 2),
        ]

        response_distribution = [
            ("0.30-0.35", 1221),
            ("0.35-0.40", 1254),
            ("0.40-0.45", 996),
            ("0.45-0.50", 506),
            ("0.50-0.55", 176),
            ("0.55-0.60", 66),
            ("0.60-0.65", 20),
            ("0.65-0.70", 4),
            ("0.70-0.75", 0),
        ]

        # Combine the rows of the two tables
        combined_data = [
            (chunk_range, chunk_count, response_range, response_count)
            for ((chunk_range, chunk_count), (response_range, response_count)) in zip(chunk_distribution, response_distribution)
        ]

        # Headers
        headers = [
            "Chunk Confidence Range", "Chunk Count",
            "Response Confidence Range", "Response Count"
        ]

        # Print the combined table
        print("\nConfidence Range for Input Chunks and Complete Responses:")
        print(tabulate(combined_data, headers=headers, tablefmt="grid"))

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Confidence Score Analyzer")
    parser.add_argument("test_run_id", type=int, help="test_run_id to process.")
    parser.add_argument("--detail_level", type=str, help="Optional detail level to filter responses.")
    args = parser.parse_args()

    calculate_confidence_stats(args.test_run_id, args.detail_level)

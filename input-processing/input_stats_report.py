from tabulate import tabulate


def generate_summary_report(input_data):
    """
    Generates a summary report based on input data.
    Args:
        input_data (dict): The input data collected for clarity score computation.
    """
    # Extract data
    test_run_stats = input_data["test_run_stats"]
    chunk_confidences = input_data["chunk_confidences"]
    response_confidences = input_data["response_confidences"]
    theme_totals = input_data["theme_totals"]
    theme_confidences = input_data["theme_confidences"]

    # Confidence Stats
    max_chunk_conf = max(chunk_confidences, default=None)
    min_chunk_conf = min(chunk_confidences, default=None)
    avg_chunk_conf = sum(chunk_confidences) / len(chunk_confidences) if chunk_confidences else None

    max_response_conf = max(response_confidences, default=None)
    min_response_conf = min(response_confidences, default=None)
    avg_response_conf = sum(response_confidences) / len(response_confidences) if response_confidences else None

    # Theme Totals with Confidence Stats
    theme_totals_with_stats = [
        [
            theme,
            len(scores),
            max(scores),
            min(scores),
            sum(scores) / len(scores),
        ]
        for theme, scores in theme_confidences.items()
    ]
    theme_totals_with_stats = sorted(theme_totals_with_stats, key=lambda x: x[1], reverse=True)

    # Print Test Run Stats
    print("\nTest Run Stats:")
    print(tabulate(test_run_stats.items(), headers=["Metric", "Value"], tablefmt="grid"))

    # Print Confidence Stats
    confidence_data = [
        ["Max Chunk Confidence", max_chunk_conf],
        ["Min Chunk Confidence", min_chunk_conf],
        ["Avg Chunk Confidence", avg_chunk_conf],
        ["Max Response Confidence", max_response_conf],
        ["Min Response Confidence", min_response_conf],
        ["Avg Response Confidence", avg_response_conf],
    ]
    print("\nConfidence Stats:")
    print(tabulate(confidence_data, headers=["Metric", "Value"], tablefmt="grid"))

    # Print Theme Totals
    print("\nTheme Totals with Confidence Stats:")
    print(
        tabulate(
            theme_totals_with_stats,
            headers=["Theme", "Count", "Max Confidence", "Min Confidence", "Avg Confidence"],
            tablefmt="grid",
            floatfmt=".3f",
        )
    )
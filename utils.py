import logging

def setup_logger(name, log_file, level=logging.DEBUG):
    """Set up a logger for a specific module."""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        logger.handlers.clear()

    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(file_handler)

    # Force flush for FileHandler
    file_handler.flush()

    return logger

def validate_json_keys(data, required_keys):
    """Ensure required keys are present in a JSON object."""
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"Missing required keys: {missing_keys}")

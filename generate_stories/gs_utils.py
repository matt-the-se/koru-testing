from typing import Dict, Any
from .data_contracts import PERSONA_DATA_SCHEMA, INPUT_SCHEMA, FOUNDATION_SCHEMA

def validate_schema(data: Dict[str, Any], schema: Dict[str, Any], path: str = "") -> None:
    """Recursively validate data against schema"""
    for field, field_type in schema.items():
        full_path = f"{path}.{field}" if path else field
        
        if field not in data:
            raise ValueError(f"Missing required field: {full_path}")
            
        if isinstance(field_type, dict):
            validate_schema(data[field], field_type, full_path)
        elif isinstance(field_type, list):
            if not isinstance(data[field], list):
                raise ValueError(f"Expected list for {full_path}")
            for item in data[field]:
                validate_schema(item, field_type[0], full_path)

def validate_persona_data(data: Dict[str, Any]) -> None:
    """Validate complete persona data structure"""
    validate_schema(data, PERSONA_DATA_SCHEMA) 
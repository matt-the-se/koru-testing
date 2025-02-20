import psycopg2
import json
from datetime import datetime
from config import DB_CONFIG

# Database connection details
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# Load the JSON file
with open("tags_import.json", "r") as f:
    data = json.load(f)

# Insert or update tags in the database
def upsert_tags(data):

    for theme, tags in data["themes"].items():
        # Check if the theme already exists
        cursor.execute("SELECT id FROM tags WHERE theme = %s", (theme,))
        existing = cursor.fetchone()

        if existing:
            # Update existing theme
            cursor.execute("""
                UPDATE tags
                SET tags = %s, updated_at = %s
                WHERE id = %s
            """, (json.dumps(tags), datetime.now(), existing[0]))
        else:
            # Insert new theme
            cursor.execute("""
                INSERT INTO tags (theme, tags)
                VALUES (%s, %s)
            """, (theme, json.dumps(tags)))

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()

# Run the function
upsert_tags(data)
print("Tags have been successfully updated!")
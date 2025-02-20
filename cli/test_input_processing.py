import click
from shared.database.manager import DatabaseManager, DBEnvironment
from config import input_processing_logger as logger

@click.group()
def cli():
    """Test input processing database operations"""
    pass

@cli.command()
def test_connection():
    """Test database connectivity"""
    try:
        db = DatabaseManager(DBEnvironment.TESTING)
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                logger.info("Database connection successful!")
                click.echo("Database connection successful!")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        click.echo(f"Error: {e}", err=True)

@cli.command()
@click.option('--test-run-id', type=int, required=True)
def show_input_data(test_run_id):
    """Show all input data for a test run"""
    db = DatabaseManager(DBEnvironment.TESTING)
    inputs = db.get_input_data(test_run_id)
    for input in inputs:
        click.echo(f"\nInput {input.input_id}:")
        click.echo(f"Prompt {input.prompt_id}")
        click.echo(f"Theme: {input.probable_theme}")
        click.echo(f"Text: {input.response_text[:50]}...")
        if input.clarity_score:
            click.echo(f"Clarity: {input.clarity_score}")

if __name__ == '__main__':
    cli() 
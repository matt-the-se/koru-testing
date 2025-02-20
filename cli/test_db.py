# cli/test_db.py
import click
from shared.database.manager import DatabaseManager, DBEnvironment

@click.group()
def cli():
    """Database testing tools"""
    pass

@cli.command()
def test_connection():
    """Test database connectivity"""
    db = DatabaseManager(DBEnvironment.TESTING)
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            click.echo("Database connection successful!")

@cli.command()
def create_run():
    """Create a new test run"""
    db = DatabaseManager(DBEnvironment.TESTING)
    test_run_id = db.create_test_run()
    click.echo(f"Created test run: {test_run_id}")

@cli.command()
@click.option('--test-run-id', type=int, required=True)
def show_inputs(test_run_id):
    """Show all inputs for a test run"""
    db = DatabaseManager(DBEnvironment.TESTING)
    inputs = db.get_test_run_inputs(test_run_id)
    for input in inputs:
        click.echo(f"Input {input.input_id} (Prompt {input.prompt_id}): {input.response_text[:50]}...")

@cli.command()
@click.option('--test-run-id', type=int, required=True)
def show_clarity_scores(test_run_id):
    """Show clarity scores by section"""
    db = DatabaseManager(DBEnvironment.TESTING)
    scores = db.get_clarity_scores(test_run_id)
    for section, score in scores.items():
        click.echo(f"{section}: {score:.2f}")

if __name__ == '__main__':
    cli()
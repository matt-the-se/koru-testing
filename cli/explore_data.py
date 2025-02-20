import click
from shared.database.manager import DatabaseManager, DBEnvironment
from shared.database.models import TestRun, PersonaInput, Prompt, Persona
from config import input_processing_logger as logger
from sqlalchemy.orm import joinedload
import json

@click.group()
def cli():
    """Explore database data"""
    pass

@cli.command()
@click.option('--db', type=click.Choice(['testing', 'webapp']), default='testing')
def list_test_runs(db):
    """List all test runs and their basic info"""
    env = DBEnvironment.TESTING if db == 'testing' else DBEnvironment.WEBAPP
    db_manager = DatabaseManager(env)
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT tr.test_run_id, COUNT(pi.input_id) as input_count
                FROM test_runs tr
                LEFT JOIN persona_inputs pi ON tr.test_run_id = pi.test_run_id
                GROUP BY tr.test_run_id
                ORDER BY tr.test_run_id DESC
                LIMIT 5
            """)
            runs = cur.fetchall()
            
            click.echo(f"\nMost recent test runs in {db}:")
            for run in runs:
                click.echo(f"Test Run {run[0]}:")
                click.echo(f"  Input Count: {run[1]}")

@cli.command()
@click.option('--test-run-id', type=int, required=True)
@click.option('--db', type=click.Choice(['testing', 'webapp']), default='testing')
def examine_test_run(test_run_id, db):
    """Examine details of a specific test run"""
    env = DBEnvironment.TESTING if db == 'testing' else DBEnvironment.WEBAPP
    db_manager = DatabaseManager(env)
    
    if db == 'testing':
        # First get personas and their clarity scores
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT persona_id, clarity_scores, top_themes
                    FROM personas
                    WHERE test_run_id = %s
                """, (test_run_id,))
                personas = cur.fetchall()
                
                click.echo(f"\nPersonas for Test Run {test_run_id}:")
                for persona in personas:
                    click.echo(f"\nPersona {persona[0]}:")
                    if persona[1]:  # clarity_scores
                        click.echo(f"Clarity Scores: {persona[1]}")
                    else:
                        click.echo("No clarity scores calculated yet")
                    if persona[2]:  # top_themes
                        click.echo(f"Top Themes: {persona[2]}")
                
                # Then get inputs
                cur.execute("""
                    SELECT pi.input_id, pi.prompt_id, p.prompt_text,
                           pi.response_text, pi.extracted_themes,
                           pi.confidence, pi.user_prompt_prefs,
                           pi.persona_id
                    FROM persona_inputs pi
                    JOIN prompts p ON pi.prompt_id = p.prompt_id
                    WHERE pi.test_run_id = %s
                    ORDER BY pi.persona_id, pi.input_id
                """, (test_run_id,))
                inputs = cur.fetchall()
    
    click.echo(f"\nInputs for Test Run {test_run_id} in {db}:")
    current_persona = None
    for input in inputs:
        if current_persona != input[7]:  # New persona
            current_persona = input[7]
            click.echo(f"\n--- Persona {current_persona} ---")
            
        click.echo(f"\nInput {input[0]} (Prompt {input[1]}):")
        click.echo(f"Prompt: {input[2][:100]}...")
        click.echo(f"Response: {input[3][:100]}...")
        if input[4]:  # extracted_themes
            click.echo(f"Themes: {input[4]}")
        if input[5]:  # confidence
            click.echo(f"Confidence: {input[5]}")
        if input[6]:  # user_prompt_prefs
            click.echo(f"User Preferences: {input[6]}")

@cli.command()
@click.option('--persona-id', type=int, required=True)
@click.option('--db', type=click.Choice(['testing', 'webapp']), default='testing')
def examine_persona(persona_id, db):
    """Show a persona's complete data including inputs and stories"""
    env = DBEnvironment.TESTING if db == 'testing' else DBEnvironment.WEBAPP
    db_manager = DatabaseManager(env)
    
    with db_manager.get_session() as session:
        persona = (
            session.query(Persona)
            .options(
                joinedload(Persona.inputs),
                joinedload(Persona.stories)
            )
            .filter_by(persona_id=persona_id)
            .first()
        )
        
        if not persona:
            click.echo(f"No persona found with ID {persona_id}")
            return
            
        click.echo(f"\nPersona {persona.persona_id}:")
        click.echo(f"Foundation: {persona.foundation}")
        click.echo(f"Detail Level: {persona.detail_level}")
        
        click.echo("\nInputs:")
        for input in persona.inputs:
            click.echo(f"  Prompt {input.prompt_id}: {input.response_text[:100]}...")
            
        click.echo("\nStories:")
        for story in persona.stories:
            click.echo(f"  Story {story.story_id}: {story.story_content[:100]}...")

@cli.command()
@click.option('--test-run-id', type=int, required=True)
@click.option('--db', type=click.Choice(['testing', 'webapp']), default='testing')
def debug_persona_data(test_run_id, db):
    """Debug: Show raw persona data for a test run"""
    env = DBEnvironment.TESTING if db == 'testing' else DBEnvironment.WEBAPP
    db_manager = DatabaseManager(env)
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            # Get all columns from personas
            cur.execute("""
                SELECT *
                FROM personas
                WHERE test_run_id = %s
            """, (test_run_id,))
            personas = cur.fetchall()
            
            # Get column names
            column_names = [desc[0] for desc in cur.description]
            
            click.echo(f"\nPersona Data for Test Run {test_run_id}:")
            for persona in personas:
                click.echo("\n" + "="*50)
                for i, value in enumerate(persona):
                    click.echo(f"{column_names[i]}: {value}")

@cli.command()
@click.option('--prompt-id', type=int, required=False, help="Show specific prompt, or all if not specified")
@click.option('--db', type=click.Choice(['testing', 'webapp']), default='testing')
def examine_prompts(prompt_id, db):
    """Show prompts and their variations"""
    env = DBEnvironment.TESTING if db == 'testing' else DBEnvironment.WEBAPP
    db_manager = DatabaseManager(env)
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            if prompt_id:
                cur.execute("""
                    SELECT prompt_id, prompt_text, prompt_theme, prompt_type, variations
                    FROM prompts
                    WHERE prompt_id = %s
                """, (prompt_id,))
            else:
                cur.execute("""
                    SELECT prompt_id, prompt_text, prompt_theme, prompt_type, variations
                    FROM prompts
                    ORDER BY prompt_id
                """)
            
            prompts = cur.fetchall()
            
            for prompt in prompts:
                click.echo("\n" + "="*50)
                click.echo(f"Prompt ID: {prompt[0]}")
                click.echo(f"Type: {prompt[3]}")
                click.echo(f"Theme: {prompt[2]}")
                click.echo(f"\nBase Prompt: {prompt[1]}")
                
                if prompt[4]:  # variations
                    click.echo("\nVariations:")
                    variations = prompt[4]
                    for i, variation in enumerate(variations, 1):
                        click.echo(f"\n{i}. {variation}")

@cli.command()
@click.option('--foundation', type=str, required=True, help="Foundation JSON string")
@click.option('--db', type=click.Choice(['testing', 'webapp']), default='testing')
def test_foundation(foundation, db):
    """Test foundation creation and prompt retrieval"""
    env = DBEnvironment.TESTING if db == 'testing' else DBEnvironment.WEBAPP
    db_manager = DatabaseManager(env)
    
    try:
        # Parse foundation JSON
        foundation_data = json.loads(foundation)
        
        # Create persona and test run
        persona_id, test_run_id = db_manager.create_persona_from_foundation(foundation_data)
        click.echo(f"Created persona {persona_id} with test run {test_run_id}")
        
        # Verify foundation data
        stored_foundation = db_manager.get_persona_foundation(persona_id)
        click.echo(f"\nStored foundation:")
        click.echo(json.dumps(stored_foundation, indent=2))
        
        # Show available prompts
        prompts = db_manager.get_available_prompts()
        click.echo("\nAvailable prompts:")
        for prompt in prompts:
            click.echo(f"\n{prompt['type']} - {prompt['theme']}")
            click.echo(f"ID {prompt['prompt_id']}: {prompt['prompt_text'][:100]}...")
            if prompt['variations']:
                click.echo(f"Has {len(prompt['variations'])} variations")
                
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

@cli.command()
@click.option('--test-run-id', type=int, required=True)
@click.option('--db', type=click.Choice(['testing', 'webapp']), default='testing')
def check_clarity(test_run_id, db):
    """Check clarity scores and status"""
    env = DBEnvironment.TESTING if db == 'testing' else DBEnvironment.WEBAPP
    db_manager = DatabaseManager(env)
    
    status = db_manager.get_clarity_status(test_run_id)
    if not status:
        click.echo(f"No data found for test run {test_run_id}")
        return
        
    click.echo("\nClarity Scores:")
    click.echo(json.dumps(status["clarity_scores"], indent=2))
    
    click.echo("\nSection Availability:")
    for section, available in status["sections_available"].items():
        click.echo(f"{section}: {'Available' if available else 'Locked'}")
    
    click.echo("\nPipeline Status:")
    for key, value in status["pipeline_status"].items():
        click.echo(f"{key}: {value}")

@cli.command()
@click.option('--persona-id', type=int, required=False, help="Filter by persona")
@click.option('--db', type=click.Choice(['testing', 'webapp']), default='testing')
def examine_prompt_preferences(persona_id, db):
    """Examine prompt preferences and selection patterns"""
    env = DBEnvironment.TESTING if db == 'testing' else DBEnvironment.WEBAPP
    db_manager = DatabaseManager(env)
    
    prefs = db_manager.get_prompt_preferences(persona_id)
    
    if not prefs:
        click.echo("No prompt preferences found")
        return
        
    click.echo("\nPrompt Preferences:")
    for pref in prefs:
        click.echo(f"\nInput {pref['input_id']} (Persona {pref['persona_id']}):")
        click.echo(f"Prompt {pref['prompt_id']}: {pref['prompt_text'][:100]}...")
        click.echo("Selection:")
        click.echo(json.dumps(pref['preferences'], indent=2))

@cli.command()
@click.option('--section', default='Core Vision', help='Filter prompts by section')
@click.option('--db', type=click.Choice(['testing', 'webapp']), default='testing')
def explore_prompts(section, db):
    """Explore prompts in the database"""
    env = DBEnvironment.TESTING if db == 'testing' else DBEnvironment.WEBAPP
    db_manager = DatabaseManager(env)
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            # First show raw prompts data
            cur.execute("""
                SELECT prompt_id, prompt_type, prompt_complete, variations
                FROM prompts 
                WHERE prompt_complete->>'section' = %s
            """, (section,))
            
            click.echo("\nRaw Prompts Data:")
            rows = cur.fetchall()
            for row in rows:
                click.echo(f"\nPrompt ID: {row[0]}")
                click.echo(f"Type: {row[1]}")
                click.echo(f"Complete Data: {json.dumps(row[2], indent=2)}")
                click.echo(f"Variations: {json.dumps(row[3], indent=2)}")

            # Then show what our get_available_prompts would return
            prompts = db_manager.get_available_prompts(section)
            click.echo("\nProcessed Prompts:")
            click.echo(json.dumps(prompts, indent=2))

if __name__ == '__main__':
    cli() 
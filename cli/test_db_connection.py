@cli.command()
def verify_setup():
    """Verify database connections and schema access"""
    for env in [DBEnvironment.TESTING, DBEnvironment.WEBAPP]:
        db_manager = DatabaseManager(env)
        click.echo(f"\nTesting {env.value} environment:")
        
        try:
            # Test basic connection
            with db_manager.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    click.echo("✓ Basic connection successful")
                    
                    # Test access to key tables
                    tables = ['personas', 'persona_inputs', 'prompts', 'test_runs', 'stories']
                    for table in tables:
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cur.fetchone()[0]
                        click.echo(f"✓ {table}: {count} rows")
                        
            # Test SQLAlchemy setup if webapp
            if env == DBEnvironment.WEBAPP:
                with db_manager.get_session() as session:
                    click.echo("✓ SQLAlchemy session creation successful")
                    
        except Exception as e:
            click.echo(f"✗ Error: {e}") 
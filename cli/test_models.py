import click
from shared.database.manager import DatabaseManager, DBEnvironment
from shared.database.models import Base, TestRun, PersonaInput, Prompt
from config import input_processing_logger as logger
import psycopg2
from psycopg2.extensions import AsIs

# Core tables that should match exactly
CORE_TABLES = {
    'persona_inputs',
    'personas',
    'prompts',
    'test_runs',
    'stories',
    'tags'
}

# Tables that can differ
OPTIONAL_TABLES = {
    'testing_db': {
        'evaluations',
        'manual_classifications'
    },
    'koru_data': {
        'input_history',
        'user_input_history'
    }
}

@click.group()
def cli():
    """Test SQLAlchemy model operations"""
    pass

@cli.command()
def compare_schemas():
    """Compare schemas between testing_db and koru_data"""
    db_test = DatabaseManager(DBEnvironment.TESTING)
    db_webapp = DatabaseManager(DBEnvironment.WEBAPP)
    
    def get_table_schema(conn, table_name):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name, data_type, is_nullable, 
                       column_default, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            return cur.fetchall()
    
    def get_constraints(conn, table_name):
        with conn.cursor() as cur:
            cur.execute("""
                SELECT conname, pg_get_constraintdef(c.oid)
                FROM pg_constraint c
                JOIN pg_namespace n ON n.oid = c.connamespace
                WHERE conrelid = %s::regclass
                AND n.nspname = 'public'
            """, (table_name,))
            return cur.fetchall()
    
    with db_test.get_connection() as test_conn, db_webapp.get_connection() as web_conn:
        # Compare core tables
        click.echo("\nComparing core tables:")
        for table in CORE_TABLES:
            click.echo(f"\n{table}:")
            test_schema = get_table_schema(test_conn, table)
            web_schema = get_table_schema(web_conn, table)
            
            if test_schema == web_schema:
                click.echo(f"✓ Schema matches")
                
                # Compare constraints
                test_constraints = get_constraints(test_conn, table)
                web_constraints = get_constraints(web_conn, table)
                if test_constraints == web_constraints:
                    click.echo(f"✓ Constraints match")
                else:
                    click.echo(f"✗ Constraint differences:")
                    click.echo("testing_db constraints:")
                    for con in test_constraints:
                        click.echo(f"  {con[0]}: {con[1]}")
                    click.echo("koru_data constraints:")
                    for con in web_constraints:
                        click.echo(f"  {con[0]}: {con[1]}")
            else:
                click.echo(f"✗ Schema differences:")
                click.echo("testing_db columns:")
                for col in test_schema:
                    click.echo(f"  {col[0]}: {col[1]} ({col[2]}) {col[3]}")
                click.echo("koru_data columns:")
                for col in web_schema:
                    click.echo(f"  {col[0]}: {col[1]} ({col[2]}) {col[3]}")
        
        # List additional tables
        click.echo("\nAdditional tables in testing_db:")
        for table in OPTIONAL_TABLES['testing_db']:
            click.echo(f"  {table}")
            
        click.echo("\nAdditional tables in koru_data:")
        for table in OPTIONAL_TABLES['koru_data']:
            click.echo(f"  {table}")

@cli.command()
def clone_schema():
    """Clone schema from testing_db to koru_data"""
    try:
        db_test = DatabaseManager(DBEnvironment.TESTING)
        db_webapp = DatabaseManager(DBEnvironment.WEBAPP)
        
        # Get schema from testing_db
        with db_test.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public';
                """)
                tables = cur.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    # Get create table statement
                    cur.execute("""
                        SELECT 
                            'CREATE TABLE ' || %s || ' (' ||
                            string_agg(
                                column_name || ' ' || data_type || 
                                CASE WHEN is_nullable = 'NO' THEN ' NOT NULL' ELSE '' END,
                                ', '
                            ) || ');'
                        FROM information_schema.columns
                        WHERE table_name = %s;
                    """, (AsIs(table_name), table_name))
                    create_stmt = cur.fetchone()[0]
                    
                    # Create table in koru_data
                    with db_webapp.get_connection() as web_conn:
                        with web_conn.cursor() as web_cur:
                            web_cur.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
                            web_cur.execute(create_stmt)
                            web_conn.commit()
                            
        logger.info("Schema cloned successfully")
        click.echo("Schema cloned successfully")
    except Exception as e:
        logger.error(f"Error cloning schema: {e}")
        click.echo(f"Error: {e}", err=True)

if __name__ == '__main__':
    cli() 
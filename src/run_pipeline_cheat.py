
import os
from sqlalchemy import create_engine, text

from cleaned.cleaned_institutions import clean_institutions
from cleaned.cleaned_financials import clean_financials
from cleaned.cleaned_failures import clean_failures
from cleaned.cleaned_complaints import clean_complaints
from company_crosswalk import build_company_crosswalk
from cleaned.clean_macro import clean_macro

#Purpose
# "My run_pipeline script acts as the orchestrator for the staging portion of my ETL pipeline.
# Instead of manually running each cleaning script and loading each dataset separately, it brings everything together.
#
# It establishes a database connection, executes the cleaning functions, and loads the resulting DataFrames into PostgreSQL
# staging tables. This makes the process more automated, consistent, and repeatable."



# 1. Create a connection engine for our PostgreSQL database.
def get_engine():

    # Read the password from an environment variable.
    # Use "database" as the default if the variable is not set.
    password = os.environ.get("DB_PASSWORD", "database")

    # SQLAlchemy uses psycopg2 to communicate with PostgreSQL.
    return create_engine(
        f"postgresql+psycopg2://database:{password}@localhost:5433/bank_health"
    )


# 2. Create the staging schema if it doesn't already exist.
def create_staging(engine):

    # engine.begin() opens a connection and manages the transaction.
    # Changes are committed automatically if no error occurs.
    with engine.begin() as conn:

        # text() allows SQLAlchemy to execute a raw SQL statement.
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))


# 3. Clean each dataset and load the results into staging.
def run_pipeline():

    engine = get_engine()

    # try contains the code we want Python to execute.
    # If an error occurs, Python still runs the finally block.
    try:
        # Ensure the staging schema exists before loading tables.
        create_staging(engine)

        # Run the Part 1 cleaning functions.
        institutions = clean_institutions()
        financials = clean_financials()
        failures = clean_failures()
        complaints = clean_complaints()

        # The crosswalk depends on both cleaned complaints and institutions.
        crosswalk = build_company_crosswalk(complaints, institutions)

        macro = clean_macro()

        # Map each staging table name to its cleaned DataFrame.
        # A dictionary lets us load all datasets using one loop.
        datasets = {
            "stg_institutions": institutions,
            "stg_financials": financials,
            "stg_failures": failures,
            "stg_complaints": complaints,
            "stg_crosswalk": crosswalk,
            "stg_macro": macro
        }

        # Loop through each table name and its corresponding DataFrame.
        for table_name, df in datasets.items():

            # pandas to_sql() writes the DataFrame into PostgreSQL.
            df.to_sql(
                table_name,
                engine,
                schema="staging",

                # Drop and recreate the table on each pipeline run.
                if_exists="replace",

                # Don't write the pandas index as an extra database column.
                index=False,

                # Insert rows in batches of 1,000.
                chunksize=1000
            )

            # Confirm how many records were loaded into each table.
            print(f"{table_name}: {len(df)} rows loaded")

        print("\nStaging pipeline completed successfully!")

    # finally ALWAYS runs, whether try succeeds or fails.
    # This ensures database connections are cleaned up even if an error occurs.
    # It does not hide errors; Python still reports them after cleanup.
    finally:
        engine.dispose()


# 4. Execute the pipeline only when this file is run directly.
if __name__ == "__main__":
    run_pipeline()


import os
from sqlalchemy import create_engine, text

from cleaned.cleaned_institutions import clean_institutions
from cleaned.cleaned_financials import clean_financials
from cleaned.cleaned_failures import clean_failures
from cleaned.cleaned_complaints import clean_complaints
from company_crosswalk import build_company_crosswalk
from cleaned.clean_macro import clean_macro


# 1. Connect to PostgreSQL
def get_engine():
    password = os.environ.get("DB_PASSWORD", "database")

    return create_engine(
        f"postgresql+psycopg2://database:{password}@localhost:5433/bank_health"
    )


# 2. Create the staging schema
def create_staging(engine):
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))


# 3. Run cleaning functions and load staging tables
def run_pipeline():
    engine = get_engine()

    try:
        create_staging(engine)

        # Run our existing Part 1 cleaning functions
        institutions = clean_institutions()
        financials = clean_financials()
        failures = clean_failures()
        complaints = clean_complaints()
        crosswalk = build_company_crosswalk(complaints, institutions)
        macro = clean_macro()

        # Load each cleaned DataFrame into staging
        datasets = {
            "stg_institutions": institutions,
            "stg_financials": financials,
            "stg_failures": failures,
            "stg_complaints": complaints,
            "stg_crosswalk": crosswalk,
            "stg_macro": macro
        }

        for table_name, df in datasets.items():
            df.to_sql(
                table_name,
                engine,
                schema="staging",
                if_exists="replace",
                index=False,
                chunksize=1000
            )

            print(f"{table_name}: {len(df)} rows loaded")

        print("\nStaging pipeline completed successfully!")

    finally:
        engine.dispose()


# 4. Run the pipeline
if __name__ == "__main__":
    run_pipeline()

# Bank Health and Customer Complaints Capstone

## Project Overview

This project analyzes the financial health of FDIC-insured banks alongside consumer complaints reported to the CFPB.

The goal is to build a data pipeline that cleans, organizes, and integrates multiple datasets into a PostgreSQL database for SQL analysis and Power BI reporting.

## Technologies Used

- **Python / Pandas:** Data profiling, cleaning, and transformation
- **PostgreSQL:** Data storage, warehouse, and analytics mart
- **Docker:** Database environment
- **SQL:** Data validation, joins, and analytical queries
- **Power BI:** Interactive dashboards and visualizations
- **Git / GitHub:** Version control

## Project Structure

- `raw/` - Original source datasets
- `src/` - Python scripts for profiling and cleaning
- `sql/` - SQL scripts for database creation, loading, and analytics
- `powerbi/` - Power BI dashboard (`.pbix`)
- `DATA_DICTIONARY.md` - Dataset definitions and field descriptions
- `DIRECTED_ANALYSIS.md` - Directed and open-ended analysis findings

## Data Pipeline

1. **Profile:** Examine raw datasets for missing values, duplicates, and inconsistencies.
2. **Clean:** Standardize data types, handle missing values, and prepare records.
3. **Load:** Import cleaned data into PostgreSQL.
4. **Model:** Build a normalized warehouse and analytics mart.
5. **Analyze:** Use SQL to investigate bank financials and consumer complaints.
6. **Visualize:** Create Power BI reports using the analytics mart.

## Running the Project

1. Clone the repository.
2. Start PostgreSQL using Docker Compose.
3. Run the Python profiling and cleaning scripts in `src/`.
4. Execute the SQL scripts in `sql/` in their numbered order.
5. Open the Power BI report in `powerbi/`.

The Power BI report uses imported data from the PostgreSQL analytics mart. Refreshing the report requires a connection to the local database.

## Analysis

The project explores:

- Changes in the number of reporting banks and industry asset concentration
- Consumer complaint trends and company matching
- Data quality and limitations across financial datasets
- Differences between complaints attributable to banks and those without direct FDIC matches

Detailed findings and limitations are documented in `DIRECTED_ANALYSIS.md`.

## Common Commands

The following commands were used in Windows PowerShell from the project directory.

Start the PostgreSQL Database

docker compose up -d

Check that the container is running:

docker ps

Run Python Profiling

python src/profile_data.py

Connect to PostgreSQL

docker exec -it bank-health-postgres psql -U database -d bank_health

Execute SQL Scripts

Load the warehouse:

Get-Content .\sql\02_load_warehouse.sql | docker exec -i bank-health-postgres psql -v ON_ERROR_STOP=1 -U database -d bank_health

Create the analytics mart:

Get-Content .\sql\04_create_mart.sql | docker exec -i bank-health-postgres psql -v ON_ERROR_STOP=1 -U database -d bank_health

Validate Data

Count financial records:

docker exec bank-health-postgres psql -U database -d bank_health -c "SELECT COUNT(*) FROM mart.fact_financial;"

Count complaints:

docker exec bank-health-postgres psql -U database -d bank_health -c "SELECT COUNT(*) FROM mart.fact_complaint;"

Check available mart tables:

docker exec bank-health-postgres psql -U database -d bank_health -c "\dt mart.*"
## Author

Brandon Magloire

York Solutions Emerging Talent Program
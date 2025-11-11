"""
MCP Server for SAE Dashboard Indicators Data

This MCP server exposes tools for querying family planning and reproductive health indicators
(e.g., modern contraceptive methods, traditional methods, unmet need) across regions in Senegal
and other African countries.

The server uses the existing data access layer from the main service to query CSV-based
indicator datasets organized by country, channel (indicator), subgroup, and version.
"""

import os
import duckdb
import pandas as pd

from pathlib import Path
from typing import List, Optional, Literal, Any, Dict
from mcp.server.fastmcp import FastMCP


from pydantic import BaseModel, Field
from service.helpers.controller_helpers import get_indicator_version, get_indicator_subgroups
from service.helpers.dot_name import DotName

# Initialize MCP server
mcp = FastMCP("SAEDashboard Indicators Data Server")


class TableSchema(BaseModel):
    """Schema information for an indicator table."""
    table_name: str = Field(description="Name of the table")
    file_path: str = Field(description="Relative path to the table data")
    columns: Dict[str, str] = Field(description="Column names and their data types")
    row_count: int = Field(description="Number of rows in the table")
    description: str = Field(description="Semantic description of the table")
    sample_values: Dict[str, List[Any]] = Field(description="Sample values for each column")


class SQLQueryResult(BaseModel):
    """Result of SQL query execution."""
    success: bool = Field(description="Whether the query executed successfully")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Query result rows as list of dictionaries")
    columns: Optional[List[str]] = Field(None, description="Column names in the result")
    row_count: Optional[int] = Field(None, description="Number of rows returned")
    error: Optional[str] = Field(None, description="Error message if query failed")


@mcp.tool()
def get_db_description() -> str:
    """
    Get information about the database including available tables with descriptions.
    Only includes tables with valid versions and subgroups.

    Returns:
        Formatted text with database table catalog

    Example:
        get_db_description()
        Returns complete list of available tables with descriptions
    """
    data_dir = Path(__file__).parent / "data" / "data"

    if not data_dir.exists():
        return "Data directory not found."

    # Get all available tables
    csv_files = sorted(data_dir.glob("Senegal__*.csv"))

    table_catalog = []
    for csv_path in csv_files:
        filename = Path(csv_path).stem
        parts = filename.split('__')

        if len(parts) >= 4:
            country = parts[0]
            indicator = parts[1]
            subgroup = parts[2]
            version = parts[3]

            # Get allowed version and subgroups for this indicator
            desc = ""
            try:
                dot_name = DotName(dot_name_str=f"Africa:{country}")
                allowed_version = get_indicator_version(dot_name.country, indicator)
                allowed_subgroups = get_indicator_subgroups(dot_name.country, indicator, allowed_version)

                # Skip if version or subgroup not in allow list
                if version != allowed_version:
                    print(f"Skipping {csv_path} because version {version} doesn't match expected version {allowed_version}")
                    continue
                if subgroup not in allowed_subgroups:
                    print(f"Skipping {csv_path} because subgroup {subgroup} doesn't match expected subgroups {','.join(subgroup)}")
                    continue

            except Exception as e:
                # Skip files that fail validation
                print(f"File {str(csv_path)} failed validation because {str(e)} ")
                continue

            # Create human-readable description
            indicator_readable = ' '.join(indicator.split('_')).title()
            subgroup_readable = ' '.join(subgroup.split('_')).title()

            table_catalog.append({
                'table_name': filename,
                'indicator': indicator_readable,
                'subgroup': subgroup_readable,
                'description': f"{indicator_readable} data for {subgroup_readable} population in {country}"
            })

    # Format table catalog
    catalog_text = "\n".join([
        f"- **{t['table_name']}**: {t['description']}"
        for t in table_catalog
    ])

    prompt = f"""# Database Description

## Available Tables

{catalog_text}

## Table Naming Convention

Tables follow this pattern: `{{country}}__{{indicator_name}}__{{subgroup}}__{{version}}`

Components:
- **country**: Geographic region (e.g., Senegal)
- **indicator_name**: Family planning metric (e.g., modern_method, traditional_method, unmet_need)
- **subgroup**: Population segment (e.g., all, 15-24, 25plus, Parity-0, rural, urban)
- **version**: Data version number

## Common Indicators

- **modern_method**: Modern contraceptive method usage rates
- **traditional_method**: Traditional contraceptive method usage rates
- **unmet_need**: Unmet need for family planning

## Usage

When analyzing a user's question, identify:
1. Which family planning indicators are relevant (modern methods, traditional methods, unmet need, etc.)
2. Which population subgroups are mentioned (all ages, 15-24, 25+, by parity, urban/rural)
3. Select the appropriate table(s) from the catalog above
"""

    return prompt


@mcp.tool()
def get_db_query_guidelines() -> str:
    """
    Get SQL query guidelines and best practices for querying the database.

    Returns:
        Formatted text with SQL query guidelines and examples

    Example:
        get_db_query_guidelines()
        Returns SQL query guidelines, example queries, and important notes
    """
    context_prompt = """# SQL Query Guidelines

## SQL Query Guidelines

1. **Table Names**: Use exact table names from the database catalog (no .csv extension)

2. **Region Filtering with Value Resolution** (CRITICAL):
   - The 'state' column contains hierarchical region identifiers in the format: `Continent:Country:Region:Department`
   - Example values: `Africa:Senegal:Dakar`, `Africa:Senegal:Dakar:Dakar`, `Africa:Senegal:Diourbel:Bambey`, `Africa:Senegal:Kaolack:Guinguinéo`
   - Data includes both region-level (e.g., `Africa:Senegal:Dakar`) and department-level (e.g., `Africa:Senegal:Dakar:Pikine`) entries

   **VALUE RESOLUTION REQUIRED**: When users specify region names, you MUST resolve them to the full hierarchical format:

   a. **Step 1 - Identify User Values**: Extract region names from the user's question
      - Examples: "Dakar", "Diourbel", "Pikine", "Bambey", "Kaffrine region"

   b. **Step 2 - Query Distinct Values**: Get all possible values from the database
      - Query: `SELECT DISTINCT state FROM table_name LIMIT 200`
      - This returns all available region identifiers in the hierarchical format

   c. **Step 3 - Fuzzy Match**: Match user values to database values using intelligent matching:
      - **Last component matching**: "Dakar" matches "Africa:Senegal:Dakar" and "Africa:Senegal:Dakar:Dakar"
      - **Case-insensitive**: "diourbel" matches "Diourbel"
      - **Typo tolerance**: "Pikene" matches "Pikine"
      - **Partial matching**: "Dakar" could match region "Dakar" and departments like "Dakar:Pikine", "Dakar:Rufisque"
      - **Regional levels**: "Kaffrine" matches both "Africa:Senegal:Kaffrine" and all "Kaffrine:*" departments

   d. **Step 4 - Replace Values**: Update your WHERE clause with resolved values
      - Before: `WHERE state IN ('Dakar', 'Diourbel')`
      - After: `WHERE state IN ('Africa:Senegal:Dakar', 'Africa:Senegal:Diourbel')`

   **Examples of Value Resolution**:
   ```sql
   -- User asks: "Show modern method usage in Dakar and Diourbel"
   -- Step 1: Extract values: ['Dakar', 'Diourbel']
   -- Step 2: Query: SELECT DISTINCT state FROM table LIMIT 200
   -- Step 3: Fuzzy match:
   --   'Dakar' → 'Africa:Senegal:Dakar' (region level)
   --   'Diourbel' → 'Africa:Senegal:Diourbel'
   -- Step 4: Generate query:
   SELECT state, year, pred
   FROM Senegal__modern_method__all__1
   WHERE state IN ('Africa:Senegal:Dakar', 'Africa:Senegal:Diourbel')
   AND year = 2022
   ```

   **Hierarchical Matching with LIKE**:
   - For broader matches (all departments in a region), use LIKE after value resolution:
   - Example: `WHERE state LIKE 'Africa:Senegal:Dakar%'` (matches region Dakar and all Dakar departments)
   - Example: `WHERE state = 'Africa:Senegal:Dakar:Pikine'` (exact department match)

3. **Year Filtering**: Use `WHERE year = 2022` or `WHERE year IN (2020, 2021, 2022)`

4. **Sorting**: Use `ORDER BY pred DESC` for highest values first

5. **Limiting Results**: Use `LIMIT n` to get top N results

6. **Aggregations**: Use `AVG(pred)`, `SUM(pred)`, `COUNT(*)`, etc.

7. **Joining Tables**: Join on state and year when comparing indicators

## Example Queries

```sql
-- Example 1: Top 5 regions by modern method usage in 2022
SELECT state, year, pred
FROM Senegal__modern_method__all__1
WHERE year = 2022
ORDER BY pred DESC
LIMIT 5

-- Example 2: Query distinct values for value resolution
-- (Use this before executing queries with user-provided region names)
SELECT DISTINCT state
FROM Senegal__modern_method__all__1
LIMIT 200

-- Example 3: Specific regions with resolved values
-- User asked: "Show modern method usage in Dakar and Diourbel in 2022"
-- After value resolution:
SELECT state, year, pred
FROM Senegal__modern_method__all__1
WHERE state IN ('Africa:Senegal:Dakar', 'Africa:Senegal:Diourbel')
  AND year = 2022

-- Example 4: All departments in Kaffrine region
SELECT state, year, pred
FROM Senegal__modern_method__all__1
WHERE state LIKE 'Africa:Senegal:Kaffrine%'
  AND year = 2022
ORDER BY pred DESC

-- Example 5: Average modern method usage across all regions over time
SELECT AVG(pred) as avg_modern_method, year
FROM Senegal__modern_method__all__1
GROUP BY year
ORDER BY year

-- Example 6: Regions with high unmet need AND low modern method usage
SELECT u.state, u.pred as unmet_need, m.pred as modern_method
FROM Senegal__unmet_need__all__1 u
JOIN Senegal__modern_method__all__1 m
  ON u.state = m.state AND u.year = m.year
WHERE u.year = 2022 AND u.pred > 0.2 AND m.pred < 0.15
ORDER BY u.pred DESC

-- Example 7: Compare traditional vs modern methods for young women
SELECT state, year, pred as traditional_method
FROM Senegal__traditional_method__15-24__1
WHERE year = 2022
ORDER BY pred DESC
LIMIT 10
```

## Important Notes

- **VALUE RESOLUTION IS MANDATORY** for any query with user-provided region names in WHERE clauses
- Always query distinct values first when users mention specific regions/locations
- Use fuzzy matching to handle typos, case differences, and partial region names
- The 'state' column uses hierarchical format: `Continent:Country:Region:Department`
- Data includes both region-level and department-level observations
- The 'pred' column contains the primary indicator values for analysis (typically as percentages/proportions)
- Always include relevant WHERE clauses to filter data appropriately
- Use meaningful column aliases in SELECT statements for clarity
- Query table schemas first to understand available columns and data types

## Value Resolution Columns

The following columns require value resolution when filtering with user-provided values:
- **state**: Geographic hierarchical identifiers (ALWAYS requires resolution)
- Any other column with a limited set of discrete categorical values

For numeric columns (year, pred, pred_lower, pred_upper), no value resolution is needed.
"""

    return context_prompt


@mcp.tool()
def get_db_schema(table_names: List[str]) -> List[TableSchema]:
    """
    Get full schema information for specified tables.

    Args:
        table_names: List of table names to get schema information for

    Returns:
        List of TableSchema objects containing column information, data types,
        sample values, and descriptions for the specified tables

    Example:
        get_db_schema(["Senegal__reported_incidence__all_ages__1", "Senegal__tpr__all_ages__1"])
        Returns schema information for the specified tables
    """
    data_dir = Path(__file__).parent / "data" / "data"

    if not data_dir.exists():
        return []

    schemas = []

    for table_name in table_names:
        csv_path = data_dir / f"{table_name}.csv"

        if not csv_path.exists():
            continue

        try:
            # Read CSV file
            df = pd.read_csv(csv_path)

            if df.empty:
                continue

            # Extract metadata from filename
            parts = table_name.split('__')

            country_name = parts[0] if len(parts) > 0 else "Unknown"
            indicator_name = parts[1] if len(parts) > 1 else "Unknown"
            subgroup_name = parts[2] if len(parts) > 2 else "all"
            version_name = parts[3] if len(parts) > 3 else "1"

            # Infer data types and create column descriptions
            columns_dict = {}
            sample_values_dict = {}

            # Define standard column descriptions
            column_descriptions = {
                'state': 'Hierarchical region identifier (e.g., Africa:Senegal:Dakar:Centre)',
                'year': 'Year of the data',
                'month': 'Month of data (1-12 or "all" for annual data)',
                'pred': 'Primary indicator value (main data column)',
                'pred_lower': 'Lower bound of prediction interval',
                'pred_upper': 'Upper bound of prediction interval',
            }

            for col in df.columns:
                # Get pandas dtype
                dtype = str(df[col].dtype)

                # Map to SQL-like types
                if 'int' in dtype:
                    sql_type = 'INTEGER'
                elif 'float' in dtype:
                    sql_type = 'FLOAT'
                elif 'object' in dtype:
                    sql_type = 'TEXT'
                elif 'datetime' in dtype:
                    sql_type = 'DATE'
                else:
                    sql_type = 'TEXT'

                # Add column description if available
                if col in column_descriptions:
                    columns_dict[col] = f"{sql_type} - {column_descriptions[col]}"
                elif col == indicator_name or col == f"se.{indicator_name}":
                    columns_dict[col] = f"{sql_type} - Reference data for {indicator_name}"
                elif col.startswith('pred_'):
                    subindicator = col.replace('pred_', '')
                    columns_dict[col] = f"{sql_type} - Disaggregated data for {subindicator}"
                else:
                    columns_dict[col] = sql_type

                # Get sample values (first 3 non-null unique values)
                sample_vals = df[col].dropna().unique()[:3].tolist()
                sample_values_dict[col] = [str(v) for v in sample_vals]

            # Create semantic description
            description = f"Health indicator data for {indicator_name} in {country_name}, subgroup: {subgroup_name}, version: {version_name}"

            # Relative path from service directory
            rel_path = str(Path(csv_path).relative_to(Path(__file__).parent))

            schemas.append(TableSchema(
                table_name=table_name,
                file_path=rel_path,
                columns=columns_dict,
                row_count=len(df),
                description=description,
                sample_values=sample_values_dict
            ))

        except Exception as e:
            print(f"Error processing {table_name}: {e}")
            continue

    return schemas


@mcp.tool()
def execute_db_query(sql_query: str) -> SQLQueryResult:
    """
    Execute a SQL query against health indicator tables using DuckDB.
    Tables are loaded as pandas DataFrames and queried directly.

    Args:
        sql_query: SQL query string to execute. Table names should match the exact
                  table names (e.g., 'Senegal__reported_incidence__all_ages__1')

    Returns:
        SQLQueryResult with data rows, columns, row count, or error message

    Example:
        execute_db_query(
            "SELECT state, year, pred FROM Senegal__reported_incidence__all_ages__1
             WHERE year = 2022 ORDER BY pred DESC LIMIT 5"
        )
        Returns top 5 regions by incidence in 2022
    """
    try:
        # Initialize DuckDB connection (in-memory)
        conn = duckdb.connect(database=':memory:')

        # Extract table names from the query
        # Simple extraction - looks for potential table names (alphanumeric + underscores)
        import re
        # Match patterns like "FROM table_name" or "JOIN table_name"
        table_patterns = re.findall(
            r'(?:FROM|JOIN|INTO|UPDATE)\s+([a-zA-Z0-9_]+)',
            sql_query,
            re.IGNORECASE
        )

        data_dir = Path(__file__).parent / "data" / "data"

        # TODO: Consider caching loaded DataFrames for performance
        #  e.g., LRU cache, global dict, pickles, loading csv files into a local db etc.
        # Load each referenced table as a pandas DataFrame and register with DuckDB
        loaded_dataframes = {}
        for table_name in table_patterns:
            csv_path = data_dir / f"{table_name}.csv"

            if csv_path.exists() and table_name not in loaded_dataframes:
                # Load table data as pandas DataFrame
                df = pd.read_csv(csv_path)
                loaded_dataframes[table_name] = df

                # Register DataFrame with DuckDB
                conn.register(table_name, df)
                print(f"Loaded table: {table_name}")

        if not loaded_dataframes:
            return SQLQueryResult(
                success=False,
                error="No valid tables found in query. Ensure table names match available table names."
            )

        # Execute the query
        result = conn.execute(sql_query).fetchall()
        columns = [desc[0] for desc in conn.description]

        # Convert to list of dictionaries
        data = [dict(zip(columns, row)) for row in result]

        # Close connection
        conn.close()

        # Log to MCP server console
        print(f"[execute_db_query] Executed query:")
        print(sql_query)
        print(f"[execute_db_query] returned {len(data)} rows")
        
        return SQLQueryResult(
            success=True,
            data=data,
            columns=columns,
            row_count=len(data)
        )

    except Exception as e:
        return SQLQueryResult(
            success=False,
            error=f"SQL execution error: {str(e)}"
        )


if __name__ == "__main__":
    # Run the MCP server with SSE transport for remote access
    # This starts an HTTP server with SSE endpoint at /sse

    # Get configuration from environment or use defaults
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "5010"))

    print(f"Starting MCP server on {host}:{port}")
    print(f"SSE endpoint will be available at: http://{host}:{port}/sse")
    print("""Available Tools:
        - get_db_description: Get database catalog for table selection
        - get_db_schema: Get detailed schema for specific tables
        - get_db_query_guidelines: Get SQL query best practices and guidelines
        - execute_db_query: Execute SQL queries against indicator tables
         """)

    # Run with SSE transport (uvicorn server)
    mcp.settings.host = host
    mcp.settings.port = port
    mcp.run(transport="sse")

    # For debugging
    # x = get_regions_with_highest_indicator_values(indicator="reported_incidence")
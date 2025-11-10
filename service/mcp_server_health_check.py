#!/usr/bin/env python3
"""
Health Check Script for MCP Server

This script connects to the MCP server, lists available tools,
and tests calling several tools to verify functionality.

Tests the following new SQL-based tools:
- get_db_description: Get database catalog for table selection
- get_db_query_guidelines: Get SQL query best practices and guidelines
- get_db_schema: Get detailed schema for specific tables
- execute_db_query: Execute SQL queries against indicator tables

Usage:
    python service/mcp_server_health_check.py [--url http://localhost:5010/sse]
"""

import asyncio
import sys
from typing import Any, Dict, List

# Try to import MCP client
try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client
except ImportError:
    print("ERROR: mcp package not found. Install it with: pip install mcp")
    sys.exit(1)


async def mcp_test_get_db_description(session: ClientSession) -> bool:
    """Test the get_db_description tool."""
    print("7. Testing tool: get_db_description")
    print("   Parameters: (no parameters)\n")

    try:
        result = await session.call_tool(
            "get_db_description",
            arguments={}
        )

        if result.structuredContent and 'result' in result.structuredContent:
            data = result.structuredContent['result']
            if data and isinstance(data, str):
                print(f"   ✓ Success! Received table selection prompt")
                print(f"   Content length: {len(data)} characters")
                lines = data.split('\\n')[:5]
                print(f"   First few lines:")
                for line in lines:
                    print(f"     {line}")
                print(f"     ... ({len(data.split(chr(10)))} total lines)")
                print()
                return True
            else:
                print(f"   ! Unexpected response type: {type(data)}")
                print(f"     {str(data)[:200]}")
                print()
        else:
            print("   ✗ No content returned")
            print()
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print()

    return False


async def mcp_test_get_db_query_guidelines(session: ClientSession) -> bool:
    """Test the get_db_query_guidelines tool."""
    print("8. Testing tool: get_db_query_guidelines")
    print("   Parameters: (no parameters)\n")

    try:
        result = await session.call_tool(
            "get_db_query_guidelines",
            arguments={}
        )

        if result.structuredContent and 'result' in result.structuredContent:
            data = result.structuredContent['result']
            if data and isinstance(data, str):
                print(f"   ✓ Success! Received SQL query guidelines")
                print(f"   Content length: {len(data)} characters")
                lines = data.split('\\n')[:5]
                print(f"   First few lines:")
                for line in lines:
                    print(f"     {line}")
                print()
                return True
            else:
                print(f"   ! Unexpected response type: {type(data)}")
                print(f"     {str(data)[:200]}")
                print()
        else:
            print("   ✗ No content returned")
            print()
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print()

    return False


async def mcp_test_get_db_schema(session: ClientSession) -> bool:
    """Test the get_db_schema tool."""
    print("9. Testing tool: get_db_schema")
    print("   Parameters: table_names=['Senegal__reported_incidence__all_ages__1', 'Senegal__test_positivity__all_ages__1']\n")

    try:
        result = await session.call_tool(
            "get_db_schema",
            arguments={
                "table_names": ["Senegal__reported_incidence__all_ages__1", "Senegal__test_positivity__all_ages__1"]
            }
        )

        if result.structuredContent and 'result' in result.structuredContent:
            data = result.structuredContent['result']
            if data and isinstance(data, list):
                print(f"   ✓ Success! Found {len(data)} table schemas")
                for i, table in enumerate(data, 1):
                    if isinstance(table, dict):
                        print(f"\n   Table {i}: {table.get('table_name', 'Unknown')}")
                        print(f"     File: {table.get('file_path', 'N/A')}")
                        print(f"     Rows: {table.get('row_count', 0)}")
                        print(f"     Description: {table.get('description', 'N/A')}")
                        columns = table.get('columns', {})
                        if columns:
                            print(f"     Columns ({len(columns)}): {', '.join(list(columns.keys())[:5])}" +
                                  (f", ... ({len(columns) - 5} more)" if len(columns) > 5 else ""))
                print()
                return True
            else:
                print(f"   ! Unexpected response type: {type(data)}")
                print(f"     {str(data)[:200]}")
                print()
        else:
            print("   ✗ No content returned")
            print()
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print()

    return False


async def mcp_test_execute_query(session: ClientSession) -> bool:
    """Test the execute_db_query tool."""
    print("10. Testing tool: execute_db_query")
    print("   Parameters: SQL query to get top 5 regions by incidence in 2022\n")

    sql_query = """
        SELECT state, year, pred
        FROM Senegal__reported_incidence__all_ages__1
        WHERE year = 2022
        ORDER BY pred DESC
        LIMIT 5
    """

    try:
        result = await session.call_tool(
            "execute_db_query",
            arguments={"sql_query": sql_query.strip()}
        )

        # For execute_db_query, FastMCP serializes the SQLQueryResult Pydantic model
        # directly to structuredContent without a 'result' wrapper
        if result.structuredContent and 'success' in result.structuredContent and result.structuredContent['success']:
            data = result.structuredContent
            if data and isinstance(data, dict):
                success = data.get('success', False)
                if success:
                    query_data = data.get('data', [])
                    columns = data.get('columns', [])
                    row_count = data.get('row_count', 0)

                    print(f"   ✓ Success! Query returned {row_count} rows")
                    print(f"   Columns: {', '.join(columns)}")
                    print(f"\n   Results:")
                    for i, row in enumerate(query_data, 1):
                        if isinstance(row, dict):
                            region = str(row.get('state', 'N/A')).split(':')[-1]
                            year = row.get('year', 'N/A')
                            value = row.get('pred', 0)
                            print(f"     {i}. {region} ({year}): {value:.2f}")
                    print()
                    return True
                else:
                    error = data.get('error', 'Unknown error')
                    print(f"   ✗ Query failed: {error}")
                    print()
            else:
                print(f"   ! Unexpected response type: {type(data)}")
                print(f"     {str(data)[:200]}")
                print()
        else:
            print("   ✗ No content returned")
            print()
    except Exception as e:
        print(f"   ✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print()

    return False


async def run_mcp_server(server_url: str = "http://localhost:5010/sse"):
    """Test the MCP server connection and tools."""

    print(f"\n{'='*60}")
    print(f"Testing MCP Server at: {server_url}")
    print(f"{'='*60}\n")

    try:
        # Connect to MCP server via SSE
        print("1. Connecting to MCP server...")

        async with sse_client(server_url) as (read, write):
            async with ClientSession(read, write) as session:
                print("✓ Connected successfully!\n")

                # Initialize the session
                await session.initialize()
                print("✓ Session initialized!\n")

                # List available tools
                print("2. Listing available tools...")
                tools_result = await session.list_tools()
                tools = tools_result.tools

                print(f"✓ Found {len(tools)} tools:\n")
                for i, tool in enumerate(tools, 1):
                    print(f"   {i}. {tool.name}")
                    print(f"      Description: {tool.description[:100]}..." if len(tool.description) > 100 else f"      Description: {tool.description}")
                    print()

                # Run all tests
                test_results = []
                # SQL-based tools
                test_results.append(await mcp_test_get_db_description(session))
                test_results.append(await mcp_test_get_db_query_guidelines(session))
                test_results.append(await mcp_test_get_db_schema(session))
                test_results.append(await mcp_test_execute_query(session))

                # Summary
                tests_passed = sum(test_results)
                total_tests = len(test_results)

                print(f"{'='*60}")
                print("TEST SUMMARY")
                print(f"{'='*60}")
                print(f"✓ Connection: SUCCESS")
                print(f"✓ Tools discovered: {len(tools)}")
                print(f"✓ Tools tested: {tests_passed}/{total_tests}")

                if tests_passed == total_tests:
                    print(f"\nAll tests completed successfully! ✓")
                else:
                    print(f"\n⚠ Some tests failed: {total_tests - tests_passed} failures")

                print(f"\nNew SQL-based tools tested:")
                print(f"  - get_db_description: Get database catalog for table selection")
                print(f"  - get_db_query_guidelines: Get SQL query best practices and guidelines")
                print(f"  - get_db_schema: Get detailed table schemas")
                print(f"  - execute_db_query: Execute SQL queries")
                print(f"{'='*60}\n")

                return tests_passed == total_tests

    except ConnectionRefusedError:
        print(f"\n✗ ERROR: Could not connect to MCP server at {server_url}")
        print("  Make sure the MCP server is running:")
        print("  docker-compose -f docker-compose.local.yml up mcp\n")
        return False

    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Health check for SenegalMEG MCP Server - Tests all available tools"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5010/sse",
        help="MCP server URL (default: http://localhost:5010/sse)"
    )

    args = parser.parse_args()

    success = await run_mcp_server(args.url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

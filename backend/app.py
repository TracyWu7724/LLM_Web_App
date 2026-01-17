import os
import sqlite3
import uvicorn
import re
import time
from fastapi import FastAPI, Request, HTTPException, Response, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd
import io
from datetime import datetime
from fuzzywuzzy import fuzz
from typing import List, Dict

from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI

import tempfile
import string

from sql_server_service import SQLServerService


# Global variables
last_query_results = []
sql_server_service = None

# Table list cache for performance
table_list_cache = {
    "tables": None,
    "last_updated": 0,
    "cache_duration": 300  # 5 minutes
}

# Pydantic models for request/response
class QueryRequest(BaseModel):
    question: str
    uploaded_table: str = None  # Optional: name of uploaded table to prioritize

class QueryResponse(BaseModel):
    sql_query: str



def validate_sql_server_query(sql: str) -> str:
    """
    Validate and fix SQL Server query for common issues
    """
    sql_upper = sql.upper()
    
    # Fix TOP and OFFSET conflict by converting to proper OFFSET...FETCH NEXT syntax
    if "TOP" in sql_upper and "OFFSET" in sql_upper:
        sql = fix_top_offset_conflict(sql)
        print(f"Fixed TOP/OFFSET conflict. New query: {sql}")
    
    # Check for LIMIT (SQLite syntax) in SQL Server query
    # Skip this check if it's likely an uploaded table query
    if "LIMIT" in sql_upper and not ("UPLOADED_" in sql_upper):
        raise ValueError(
            "SQL Server Error: LIMIT is not valid SQL Server syntax. "
            "Use TOP clause or ORDER BY ... OFFSET ... FETCH NEXT instead."
        )
    
    return sql

def fix_top_offset_conflict(sql: str) -> str:
    """
    Convert queries with both TOP and OFFSET to proper OFFSET...FETCH NEXT syntax
    """
    import re
    
    # Extract TOP value if present
    top_match = re.search(r'SELECT\s+TOP\s+(\d+)', sql, re.IGNORECASE)
    if not top_match:
        # If no TOP number found, return original with just TOP removed
        return re.sub(r'\bTOP\s+\w+\b', '', sql, flags=re.IGNORECASE).strip()
    
    top_value = int(top_match.group(1))
    
    # Remove the TOP clause
    sql_without_top = re.sub(r'SELECT\s+TOP\s+\d+\s*', 'SELECT ', sql, flags=re.IGNORECASE)
    
    # Check if there's already FETCH NEXT
    if 'FETCH NEXT' not in sql_without_top.upper():
        # Add FETCH NEXT clause
        if 'OFFSET' in sql_without_top.upper():
            # Insert FETCH NEXT after OFFSET clause
            sql_without_top = re.sub(
                r'(OFFSET\s+\d+\s+ROWS?)\s*',
                rf'\1 FETCH NEXT {top_value} ROWS ONLY ',
                sql_without_top,
                flags=re.IGNORECASE
            )
        else:
            # No OFFSET present, add both OFFSET 0 and FETCH NEXT
            # Find ORDER BY clause to insert OFFSET after it
            if 'ORDER BY' in sql_without_top.upper():
                sql_without_top = re.sub(
                    r'(ORDER\s+BY\s+[^;\s]+(?:\s+(?:ASC|DESC))?)',
                    rf'\1 OFFSET 0 ROWS FETCH NEXT {top_value} ROWS ONLY',
                    sql_without_top,
                    flags=re.IGNORECASE
                )
            else:
                # No ORDER BY, we need to add one for OFFSET to work
                # Add a generic ORDER BY (SELECT) clause
                sql_without_top += f' ORDER BY (SELECT NULL) OFFSET 0 ROWS FETCH NEXT {top_value} ROWS ONLY'
    
    return sql_without_top.strip()

def clean_sql_query(raw_sql: str) -> str:
    """
    Clean and validate SQL query
    """
    if not raw_sql:
        raise ValueError("Empty SQL response")
    
    # Basic cleanup only
    sql = raw_sql.strip()
    
    # Remove any markdown artifacts if present
    sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
    sql = re.sub(r'```\s*', '', sql)
    
    # Clean whitespace and remove trailing semicolon
    sql = re.sub(r'\s+', ' ', sql.strip().rstrip(';'))
    
    if not sql or len(sql) < 5:
        raise ValueError(f"Invalid SQL query: {sql}")
    
    # Validate SQL Server specific syntax
    sql = validate_sql_server_query(sql)
    
    print(f"Final SQL: '{sql}'")
    return sql



def save_query_to_history_background(query_text: str):
    """Save a query to the recent queries history in background"""
    global sql_server_service
    if sql_server_service:
        sql_server_service.save_query_to_history(query_text)

def clean_column_name(col_name: str) -> str:
    """Clean column name to be SQL-safe"""
    # Remove special characters and replace with underscores
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', str(col_name))
    # Remove leading/trailing underscores
    cleaned = cleaned.strip('_')
    # Ensure it doesn't start with a number
    if cleaned and cleaned[0].isdigit():
        cleaned = 'col_' + cleaned
    # If empty, use a default name
    if not cleaned:
        cleaned = 'unnamed_column'
    return cleaned

def process_uploaded_file(file_path: str, filename: str) -> dict:
    """Process uploaded CSV/Excel file and create database table"""
    global sql_server_service
    try:
        # Determine file type and read accordingly
        if filename.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        elif filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
        else:
            raise ValueError("Unsupported file format")
        
        # Clean column names
        df.columns = [clean_column_name(col) for col in df.columns]
        
        # Handle duplicate column names
        col_counts = {}
        new_columns = []
        for col in df.columns:
            if col in col_counts:
                col_counts[col] += 1
                new_columns.append(f"{col}_{col_counts[col]}")
            else:
                col_counts[col] = 0
                new_columns.append(col)
        df.columns = new_columns
        
        # Create table name from filename
        table_name = 'uploaded_' + clean_column_name(filename.split('.')[0])
        
        # Extract file extension for metadata
        file_extension = os.path.splitext(filename)[1].lower()
        
        # Use SQLServerService to handle uploaded file
        if sql_server_service:
            result = sql_server_service.handle_uploaded_file(df, table_name, filename, file_extension)
            if result["success"]:
                # Add original filename and extension to the result (already included from handle_uploaded_file)
                result["original_filename"] = filename
                result["file_extension"] = file_extension
            return result
        else:
            raise Exception("SQL Server service not initialized")
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_uploaded_table_columns(table_name: str, db_path: str) -> list:
    """Get actual column names from uploaded SQLite table"""
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return columns
    except Exception as e:
        print(f"Error getting columns for {table_name}: {e}")
        return []

def invalidate_table_cache():
    """Invalidate the table list cache to force refresh"""
    global table_list_cache
    table_list_cache["tables"] = None
    table_list_cache["last_updated"] = 0
    print("Table list cache invalidated")

def get_all_available_tables() -> List[Dict[str, str]]:
    """Get all schemas and tables dynamically from the database with caching"""
    global table_list_cache, sql_server_service
    
    current_time = time.time()
    
    # Check if cache is still valid
    if (table_list_cache["tables"] is not None and 
        current_time - table_list_cache["last_updated"] < table_list_cache["cache_duration"]):
        print(f"Using cached table list ({len(table_list_cache['tables'])} tables)")
        return table_list_cache["tables"]
    
    try:
        print("Refreshing table list from database...")
        
        # Get all schemas and tables from SQL Server
        all_tables = sql_server_service.get_all_schemas_and_tables()
        
        # Also get uploaded tables
        uploaded_tables = sql_server_service.get_uploaded_tables()
        
        # Format all tables consistently
        table_list = []
        
        # Add SQL Server tables
        for table_info in all_tables:
            table_list.append({
                "full_name": table_info.get("full_name", ""),
                "table_name": table_info.get("table_name", ""),
                "schema": table_info.get("schema", ""),
                "description": table_info.get("description", ""),
                "source": "sql_server"
            })
        
        # Add uploaded tables
        for table_info in uploaded_tables:
            table_list.append({
                "full_name": table_info["name"],
                "table_name": table_info["name"],
                "schema": "uploaded",
                "description": f"Uploaded file: {table_info.get('original_filename', '')}",
                "source": "uploaded"
            })
        
        # Update cache
        table_list_cache["tables"] = table_list
        table_list_cache["last_updated"] = current_time
        
        print(f"Table list refreshed: {len(table_list)} tables found")
        return table_list
        
    except Exception as e:
        print(f"Error getting tables: {e}")
        # Return cached data if available, otherwise empty list
        return table_list_cache["tables"] if table_list_cache["tables"] else []

def find_best_table_match(question: str) -> str:
    """Simple and fast string similarity matching for table selection"""
    # Get all available tables
    all_tables = get_all_available_tables()
    
    if not all_tables:
        return "das.Material_Tracker_Historical"  # Fallback
    
    question_lower = question.lower()
    
    # Create search strings for each table (combine name, schema, description)
    table_search_data = []
    for table in all_tables:
        search_string = f"{table['full_name']} {table['table_name']} {table['schema']} {table['description']}".lower()
        table_search_data.append({
            "table": table,
            "search_string": search_string,
            "full_name": table["full_name"]
        })
    
    # Simple string similarity matching
    best_score = 0
    best_table = all_tables[0]["full_name"]  # Default to first table
    
    for item in table_search_data:
        # Calculate simple similarity score
        score = 0
        
        # Direct substring matches get high scores
        words_in_question = question_lower.split()
        for word in words_in_question:
            if len(word) > 2:  # Skip very short words
                if word in item["search_string"]:
                    score += 3  # High score for exact word match
                
                # Partial matches
                for search_word in item["search_string"].split():
                    if len(search_word) > 2:
                        # Use fuzzywuzzy for individual word matching
                        word_similarity = fuzz.ratio(word, search_word)
                        if word_similarity > 80:
                            score += 2
                        elif word_similarity > 60:
                            score += 1
        
        # Boost score if question contains table name parts
        if any(part in question_lower for part in item["table"]["table_name"].lower().split('_')):
            score += 2
        
        # Boost score if question contains schema name
        if item["table"]["schema"].lower() in question_lower:
            score += 1
        
        if score > best_score:
            best_score = score
            best_table = item["full_name"]
    
    print(f"Best table match for '{question}': {best_table} (score: {best_score})")
    return best_table

def extract_table_name_from_question(question: str, available_tables = None) -> str:
    """Extract table name from natural language question - now uses fuzzy matching"""
    
    # Try the new fuzzy matching approach first
    try:
        best_match = find_best_table_match(question)
        if best_match:
            return best_match
    except Exception as e:
        print(f"Fuzzy matching failed, falling back to simple matching: {e}")
    
    # Fallback to original logic if fuzzy matching fails
    question_lower = question.lower()
    
    # If we have available tables, try to match against them intelligently
    if available_tables:
        # First try exact table name matches
        for table in available_tables:
            table_simple = table.split('.')[-1].lower()  # Get just the table name part
            if table_simple in question_lower:
                return table
        
        # Try keyword matching for common data types
        table_keywords = {
            'cost': ['cost', 'expense', 'budget', 'financial'],
            'revenue': ['revenue', 'income', 'sales', 'profit'],
            'customer': ['customer', 'client', 'user'],
            'product': ['product', 'item', 'inventory'],
            'employee': ['employee', 'staff', 'worker', 'hr'],
            'order': ['order', 'purchase', 'transaction'],
            'npi': ['npi', 'development', 'project', 'new product'],
            'manufacturing': ['manufacturing', 'production', 'factory'],
            'quality': ['quality', 'defect', 'test'],
            'supplier': ['supplier', 'vendor', 'procurement']
        }
        
        for keyword_type, keywords in table_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                # Find tables that might match this type
                matching_tables = [table for table in available_tables 
                                 if keyword_type in table.lower() or 
                                 any(kw in table.lower() for kw in keywords)]
                if matching_tables:
                    return matching_tables[0]  # Return first match
    
    # Pattern matching for explicit table references
    patterns = [
        r'(?:table|from)\s+(?:das\.)?([a-zA-Z_][a-zA-Z0-9_]*)',
        r'(?:das\.)([a-zA-Z_][a-zA-Z0-9_]*)',
        r'\b(das_[a-zA-Z_][a-zA-Z0-9_]*)\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, question_lower)
        if match:
            table_name = match.group(1)
            # Ensure fully qualified name
            if not table_name.startswith('das.'):
                table_name = f"das.{table_name}"
            return table_name
    
    # If we have available tables, return the first one as fallback
    if available_tables:
        print(f"No specific table detected, using first available: {available_tables[0]}")
        return available_tables[0]
    
    # Last resort fallback
    return "das.das_npi_development_cost_ebr"

def detect_large_dataset_request(question: str) -> tuple[bool, int, int]:
    """
    Detect if user wants a large dataset and extract custom limits/timeouts
    Returns: (is_large_request, custom_limit, suggested_timeout)
    """
    question_lower = question.lower()
    
    # Keywords that indicate user wants ALL data
    all_keywords = ['all rows', 'all data', 'all records', 'everything', 'complete dataset', 'entire table', 'full table']
    wants_all = any(keyword in question_lower for keyword in all_keywords)
    
    # Extract custom numbers from user request
    custom_limit = None
    
    # Look for explicit numbers like "first 5000", "limit 10000", "top 2000", etc.
    limit_patterns = [
        r'(?:first|top|limit|show)\s+(\d+)',
        r'(\d+)\s+(?:rows|records|entries)',
        r'limit\s+(\d+)',
    ]
    
    for pattern in limit_patterns:
        match = re.search(pattern, question_lower)
        if match:
            custom_limit = int(match.group(1))
            break
    
    # Determine if this is a large request
    is_large = wants_all or (custom_limit and custom_limit > 1000)
    
    # Set appropriate limits and timeouts
    if wants_all:
        # User wants everything - remove automatic LIMIT, use long timeout
        final_limit = None  # No limit
        timeout = 300  # 5 minutes
    elif custom_limit:
        # User specified a number
        final_limit = custom_limit
        if custom_limit > 10000:
            timeout = 180  # 3 minutes for very large
        elif custom_limit > 5000:
            timeout = 120  # 2 minutes for large
        elif custom_limit > 1000:
            timeout = 60   # 1 minute for medium
        else:
            timeout = 30   # 30 seconds for small
    else:
        # Default behavior
        final_limit = 1000
        timeout = 30
    
    return is_large, final_limit, timeout



# Load environment variables
load_dotenv()

# Google Gemini Configuration
gemini_api_key = os.getenv("GEMINI_API_KEY")

app = FastAPI(title="SQL Query API", description="API for natural language to SQL queries", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SQL Server service and models once at startup
sql_server_service = SQLServerService()
sql_server_service.init_local_db()

# Create LangChain LLM for SQL generation
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    google_api_key=gemini_api_key,
    temperature=0.0,
    max_output_tokens=4000,
)

def generate_sql_server_sql(question: str, table_name: str = "das.das_npi_development_cost_ebr", columns_list: list = None, custom_limit: int = None) -> str:
    """Generate SQL from natural language - adapts to SQL Server or SQLite"""
    
    # Detect if this is an uploaded table (SQLite) or SQL Server table
    is_uploaded_table = table_name.startswith("uploaded_")
    
    # Format column information if available
    columns_info = ""
    if columns_list:
        columns_info = f"\nAvailable columns: {', '.join(columns_list)}\nIMPORTANT: Only use these exact column names!"
    
    # Determine limit instruction based on custom_limit
    if custom_limit is None:
        limit_instruction = "DO NOT add any LIMIT clause - user wants all data"
    elif custom_limit > 1000:
        limit_instruction = f"Add LIMIT {custom_limit} to get the requested {custom_limit:,} rows"
    else:
        limit_instruction = f"Add LIMIT {custom_limit} for safety"
    
    if is_uploaded_table:
        # Generate SQLite-compatible SQL for uploaded tables
        prompt = f"""
Generate SQLite SQL for this question: {question}

Table: {table_name}{columns_info}
Rules:
- Use standard SQL syntax (SQLite)
- {limit_instruction}
- Column names may have underscores (Cost_Center, Item_Number)
- Be flexible: "cost center" = "Cost_Center"
- Only use columns that exist in the table
- Start with SELECT * LIMIT 10 if unsure about columns

Return only SQL:"""
    
    else:
        # Generate SQL Server SQL for main database
        prompt = f"""
Generate SQL Server SQL for this question: {question}

Table: {table_name}{columns_info}
Rules:
- Use SQL Server T-SQL syntax
- {limit_instruction}
- Use fully qualified table names (schema.table)
- Column names may have underscores (Cost_Center, Item_Number)  
- Be flexible: "cost center" = "Cost_Center"
- Only use columns that exist in the table
- Prefer summary queries (COUNT, SUM) over SELECT * when appropriate

PAGINATION RULES (CRITICAL):
- For simple row limiting: Use TOP clause (e.g., SELECT TOP 100 * FROM table)
- For pagination with offset: Use ORDER BY ... OFFSET ... FETCH NEXT syntax
  Example: SELECT * FROM table ORDER BY id OFFSET 10 ROWS FETCH NEXT 20 ROWS ONLY
- NEVER use TOP and OFFSET in the same query - this is invalid SQL Server syntax
- OFFSET requires an ORDER BY clause to work properly
- If you need both limiting and offset, use ONLY the OFFSET...FETCH NEXT pattern

Return only SQL:"""

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        # Fallback for simple queries
        print(f"LLM generation failed, using fallback: {e}")
        fallback_limit = f" LIMIT {custom_limit}" if custom_limit else ""
        
        if "first" in question.lower() or "limit" in question.lower():
            return f"SELECT * FROM {table_name}{fallback_limit or ' LIMIT 10'}"
        elif "column" in question.lower() or "schema" in question.lower():
            if is_uploaded_table:
                return f"PRAGMA table_info({table_name})"
            else:
                return f"DESCRIBE {table_name}"
        else:
            return f"SELECT * FROM {table_name}{fallback_limit or ' LIMIT 50'}"

print(" SQL Server service initialized")

# API Endpoints
@app.get("/")
async def root():
    """Root endpoint providing API information - NOT a health check"""
    return {
        "message": "SQL Query API", 
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "GET /": "This endpoint (API info)",
            "GET /health": "Health check (tests database connection)",
            "POST /generate_sql": "Generate SQL from natural language",
            "POST /query": "Generate and execute natural language query",
            "POST /upload": "Upload CSV/Excel file to create queryable table",
            "GET /tables": "Get all available database tables",
            "GET /recent_queries": "Get last 5 recent queries",
            "GET /download/csv": "Download last query results as CSV",
            "GET /download/excel": "Download last query results as Excel"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint - tests database connection"""
    global sql_server_service
    
    if not sql_server_service:
        raise HTTPException(status_code=500, detail="SQL Server service not initialized")
    
    # Test SQL Server connection
    connection_test = sql_server_service.test_connection()
    
    if connection_test["status"] == "success":
        return {
            "status": "healthy", 
            "database": "sql_server_connected", 
            "message": connection_test["message"],
            "tables_count": connection_test["tables_count"],
            "sample_tables": connection_test["sample_tables"]
        }
    else:
        raise HTTPException(status_code=500, detail=connection_test["message"])

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload CSV or Excel file and create a queryable database table"""
    
    # Validate file type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    allowed_extensions = ['.csv', '.xlsx', '.xls']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
        try:
            # Save uploaded file to temporary location
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            # Process the file
            result = process_uploaded_file(temp_file.name, file.filename)
            
            if result["success"]:
                # Invalidate cache since we added a new table
                invalidate_table_cache()
                print(f"New table '{result['table_name']}' uploaded and cache invalidated")
                
                # Get a preview of the uploaded data
                try:
                    preview_data = sql_server_service.query_uploaded_table(f"SELECT * FROM {result['table_name']} LIMIT 10")
                except Exception as preview_error:
                    print(f"Could not get preview data: {preview_error}")
                    preview_data = []
                
                return {
                    "message": "File uploaded successfully",
                    "table_name": result["table_name"],
                    "row_count": result["row_count"],
                    "column_count": result["column_count"],
                    "columns": result["columns"],
                    "preview_data": preview_data,
                    "preview_count": len(preview_data),
                    "original_filename": result.get("original_filename", "unknown"),
                    "file_extension": result.get("file_extension", ".csv")
                }
            else:
                raise HTTPException(status_code=400, detail=f"File processing failed: {result['error']}")
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file.name)
            except:
                pass

@app.get("/recent_queries")
async def get_recent_queries():
    """Get the last 5 recent queries"""
    global sql_server_service
    
    if not sql_server_service:
        return {"recent_queries": []}
    
    recent_queries = sql_server_service.get_recent_queries(5)
    return {"recent_queries": recent_queries}

@app.get("/table/{table_name}/preview")
async def get_table_preview(table_name: str, limit: int = 5):
    """Get a preview of table data (first few rows)"""
    global sql_server_service
    
    if not sql_server_service:
        raise HTTPException(status_code=500, detail="SQL Server service not initialized")
    
    try:
        # Check if it's an uploaded table (stored locally)
        if table_name.startswith("uploaded_"):
            # Handle uploaded tables with local SQLite
            conn = sqlite3.connect(sql_server_service.local_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Validate table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
            
            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            columns = [col['name'] for col in columns_info]
            
            # Get preview data
            cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
            rows = cursor.fetchall()
            result_dicts = [dict(row) for row in rows]
            
            # Get total row count
            cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
            total_rows = cursor.fetchone()['count']
            
            # Get file metadata
            metadata = sql_server_service.get_table_metadata(table_name)
            
            cursor.close()
            conn.close()
            
            return {
                "table_name": table_name,
                "columns": columns,
                "rows": result_dicts,
                "preview_count": len(result_dicts),
                "total_rows": total_rows,
                "original_filename": metadata.get("original_filename"),
                "file_extension": metadata.get("file_extension")
            }
        else:
            # Handle SQL Server tables
            return sql_server_service.get_table_preview(table_name, limit)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching table preview: {str(e)}")

@app.post("/generate_sql")
async def generate_sql(request: QueryRequest):
    """Generate SQL from natural language without executing"""
    try:
        # Analyze the user's question for large dataset requests
        is_large_request, custom_limit, suggested_timeout = detect_large_dataset_request(request.question)
        
        # Determine which table to use and modify question if needed
        if request.uploaded_table:
            table_name = request.uploaded_table
            question = request.question
            # Get actual column names from the uploaded table
            columns_list = get_uploaded_table_columns(table_name, sql_server_service.local_db_path)
            # For uploaded tables, modify the question to be more specific
            question = f"Using the uploaded table '{request.uploaded_table}', {request.question}. Use simple SQL syntax suitable for SQLite, not T-SQL. Do not use fully qualified table names."
        else:
            # Only get available tables if we need to query SQL Server
            # Skip this expensive operation for uploaded file queries
            available_tables = []
            
            # Extract table name from user question or use default
            table_name = extract_table_name_from_question(request.question)
            question = request.question
            print(f"Detected table name: {table_name}")
            
            # Only fetch SQL Server schema if we're actually querying a SQL Server table
            columns_list = None
            if not table_name.startswith("uploaded_"):
                try:
                    print("Fetching SQL Server table schema...")
                    schema = sql_server_service.get_table_schema(table_name)
                    if schema:
                        columns_list = [col['name'] for col in schema]
                        print(f"Got SQL Server columns: {columns_list}")
                    else:
                        print(f"No schema found for table: {table_name}")
                except Exception as e:
                    print(f"Could not get SQL Server schema for {table_name}: {e}")
            else:
                print("Skipping SQL Server schema fetch for uploaded table")
        
        # Generate SQL using our custom function with actual column names and limit info
        raw_sql = generate_sql_server_sql(question, table_name, columns_list, custom_limit)
        sql_query = clean_sql_query(raw_sql)
        
        # Prepare response with warning if needed
        response_data = {
            "question": request.question,
            "sql_query": sql_query,
            "table_name": table_name
        }
        
        # Add performance warning for large queries
        if is_large_request:
            if custom_limit is None:
                response_data["warning"] = "This query requests ALL data - execution may take several minutes."
            elif custom_limit > 10000:
                response_data["warning"] = f"This query requests {custom_limit:,} rows - execution may take several minutes."
            elif custom_limit > 5000:
                response_data["warning"] = f"This query requests {custom_limit:,} rows - execution may take 1-2 minutes."
                
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL Generation Error: {str(e)}")



@app.post("/query")
async def execute_natural_language_query(request: QueryRequest, background_tasks: BackgroundTasks):
    """Generate SQL from natural language and execute it"""
    global last_query_results, sql_server_service, sql_chain
    
    if not sql_server_service:
        raise HTTPException(status_code=500, detail="SQL Server service not initialized")
    
    try:
        # Analyze the user's question for large dataset requests
        is_large_request, custom_limit, suggested_timeout = detect_large_dataset_request(request.question)
        
        # Warn user about potential performance impact for large queries
        warning_message = ""
        if is_large_request:
            if custom_limit is None:
                warning_message = "Requesting ALL data - this may take several minutes and use significant memory."
            elif custom_limit > 10000:
                warning_message = f"Requesting {custom_limit:,} rows - this may take several minutes."
            elif custom_limit > 5000:
                warning_message = f"Requesting {custom_limit:,} rows - this may take 1-2 minutes."
        
        # Determine which table to use and modify question if needed
        if request.uploaded_table:
            table_name = request.uploaded_table
            question = request.question  # Start with original question
            # Get actual column names from the uploaded table
            columns_list = get_uploaded_table_columns(table_name, sql_server_service.local_db_path)
            # For uploaded tables, modify the question to be more specific
            question = f"Using the uploaded table '{request.uploaded_table}', {request.question}. Use simple SQL syntax suitable for SQLite, not T-SQL. Do not use fully qualified table names."
        else:
            # Only get available tables if we need to query SQL Server
            # Skip this expensive operation for uploaded file queries
            available_tables = []
            
            # Extract table name from user question or use default
            table_name = extract_table_name_from_question(request.question, available_tables)
            question = request.question
            print(f"Detected table name: {table_name}")
            
            # Only fetch SQL Server schema if we're actually querying a SQL Server table
            columns_list = None
            if not table_name.startswith("uploaded_"):
                try:
                    print("Fetching SQL Server table schema...")
                    schema = sql_server_service.get_table_schema(table_name)
                    if schema:
                        columns_list = [col['name'] for col in schema]
                        print(f"Got SQL Server columns: {columns_list}")
                    else:
                        print(f"No schema found for table: {table_name}")
                except Exception as e:
                    print(f"Could not get SQL Server schema for {table_name}: {e}")
            else:
                print("Skipping SQL Server schema fetch for uploaded table")
        
        # Generate SQL using our custom function with actual column names and limit info
        raw_sql = generate_sql_server_sql(question, table_name, columns_list, custom_limit)
        sql_query = clean_sql_query(raw_sql)
        
        # Determine where to execute the query
        result_dicts = []
        
        if request.uploaded_table and request.uploaded_table.startswith("uploaded_"):
            # Execute on local SQLite for uploaded tables (faster, no timeout needed)
            print("Executing query on uploaded table (local SQLite)")
            result_dicts = sql_server_service.query_uploaded_table(sql_query)
        else:
            # Execute on SQL Server with appropriate timeout and limit
            print("Executing query on SQL Server")
            try:
                print(f"Executing SQL Server query with timeout: {suggested_timeout}s, limit: {custom_limit}")
                
                # Ensure we don't have extremely long timeouts that could hang the frontend
                max_timeout = min(suggested_timeout, 300)  # Cap at 5 minutes
                if max_timeout != suggested_timeout:
                    print(f"Timeout capped at {max_timeout}s for safety")
                
                result_dicts = sql_server_service.execute_query(
                    sql_query, 
                    timeout_seconds=max_timeout,
                    custom_limit=custom_limit
                )
            except TimeoutError as timeout_err:
                raise HTTPException(status_code=408, detail=f"Query timeout: {str(timeout_err)}")
            except Exception as db_err:
                raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
        
        # Store results for download
        last_query_results = result_dicts
        
        # Save query to history in background (non-blocking)
        background_tasks.add_task(save_query_to_history_background, request.question)
        
        response_data = {
            "question": request.question,
            "sql_query": sql_query,
            "rows": result_dicts,
            "count": len(result_dicts),
            "raw_result": f"Retrieved {len(result_dicts)} rows"
        }
        
        # Add warning message if this was a large request
        if warning_message:
            response_data["warning"] = warning_message
            
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query Error: {str(e)}")

@app.get("/download/csv")
async def download_csv():
    """Download last query results as CSV"""
    global last_query_results
    
    if not last_query_results:
        raise HTTPException(status_code=404, detail="No query results available for download")
    
    try:
        # Convert to DataFrame
        df = pd.DataFrame(last_query_results)
        
        # Create CSV
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"query_results_{timestamp}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV generation failed: {str(e)}")

@app.get("/download/excel")
async def download_excel():
    """Download last query results as Excel"""
    global last_query_results
    
    if not last_query_results:
        raise HTTPException(status_code=404, detail="No query results available for download")
    
    try:
        # Convert to DataFrame
        df = pd.DataFrame(last_query_results)
        
        # Create Excel using xlsxwriter first, fallback to openpyxl
        excel_buffer = io.BytesIO()
        try:
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Query Results', index=False)
        except Exception as xlsx_error:
            print(f"xlsxwriter failed, trying openpyxl: {xlsx_error}")
            # Reset buffer and try with openpyxl
            excel_buffer = io.BytesIO()
            try:
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Query Results', index=False)
            except Exception as openpyxl_error:
                print(f"openpyxl also failed: {openpyxl_error}")
                # If both fail, just return CSV as Excel
                csv_content = df.to_csv(index=False)
                return Response(
                    content=csv_content,
                    media_type="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
                )
        
        excel_content = excel_buffer.getvalue()
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"query_results_{timestamp}.xlsx"
        
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        print(f"Excel download error: {e}")
        raise HTTPException(status_code=500, detail=f"Excel generation failed: {str(e)}")

@app.get("/tables")
async def get_tables(include_sql_server: bool = False):
    """Get available tables - only fetch SQL Server tables if requested"""
    global sql_server_service
    
    if not sql_server_service:
        return {"tables": [], "error": "SQL Server service not initialized"}
    
    try:
        table_info = []
        
        # Always get uploaded tables (fast, local SQLite)
        try:
            uploaded_tables = sql_server_service.get_uploaded_tables()
            table_info.extend(uploaded_tables)
            print(f"Found {len(uploaded_tables)} uploaded tables")
        except Exception as e:
            print(f"Error getting uploaded tables: {e}")
        
        # Only get SQL Server tables if explicitly requested
        if include_sql_server:
            try:
                print("Fetching SQL Server tables (this may take a moment)...")
                sql_server_tables = sql_server_service.get_table_names()
                for table_name in sql_server_tables:
                    try:
                        schema = sql_server_service.get_table_schema(table_name)
                        table_info.append({
                            "name": table_name,
                            "columns": schema,
                            "row_count": None,  # Skip row count for performance
                            "is_uploaded": False,
                            "source": "sql_server"
                        })
                    except Exception as e:
                        print(f"Error getting schema for {table_name}: {e}")
                        # Still add the table even if we can't get schema
                        table_info.append({
                            "name": table_name,
                            "columns": [],
                            "row_count": None,
                            "is_uploaded": False,
                            "source": "sql_server"
                        })
            except Exception as e:
                print(f"Error getting SQL Server tables: {e}")
        else:
            print("Skipping SQL Server tables (use ?include_sql_server=true to fetch them)")
        
        return {
            "tables": table_info,
            "total_count": len(table_info),
            "uploaded_count": len([t for t in table_info if t.get("is_uploaded", False)]),
            "sql_server_count": len([t for t in table_info if not t.get("is_uploaded", False)]),
            "sql_server_included": include_sql_server
        }
        
    except Exception as e:
        return {"tables": [], "error": str(e)}

@app.get("/tables/uploaded")
async def get_uploaded_tables_only():
    """Get only uploaded tables (fast, no SQL Server connection needed)"""
    global sql_server_service
    
    if not sql_server_service:
        return {"tables": [], "error": "SQL Server service not initialized"}
    
    try:
        uploaded_tables = sql_server_service.get_uploaded_tables()
        return {
            "tables": uploaded_tables,
            "count": len(uploaded_tables),
            "source": "local_sqlite_only"
        }
    except Exception as e:
        return {"tables": [], "error": str(e)}

@app.delete("/tables/uploaded/{table_name}")
async def delete_uploaded_table(table_name: str):
    """Delete an uploaded table and invalidate cache"""
    global sql_server_service
    
    if not sql_server_service:
        raise HTTPException(status_code=500, detail="SQL Server service not initialized")
    
    # Validate table name format
    if not table_name.startswith("uploaded_"):
        raise HTTPException(status_code=400, detail="Only uploaded tables can be deleted (must start with 'uploaded_')")
    
    try:
        # Delete the table
        result = sql_server_service.delete_uploaded_table(table_name)
        
        if result["success"]:
            # Invalidate the cache so the table list gets refreshed
            invalidate_table_cache()
            print(f"Table '{table_name}' deleted and cache invalidated")
            
            return {
                "success": True,
                "message": result["message"],
                "table_name": table_name
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting table: {str(e)}")

@app.options("/{path:path}")
async def options_handler(request: Request, path: str):
    """Handle OPTIONS requests for CORS"""
    return Response(status_code=204)

@app.get("/debug/uploaded_files")
async def debug_uploaded_files():
    """Debug endpoint to check uploaded file status"""
    global sql_server_service
    
    debug_info = {
        "sql_server_service_initialized": sql_server_service is not None,
        "local_db_path": sql_server_service.local_db_path if sql_server_service else None,
        "uploaded_tables": [],
        "errors": []
    }
    
    if not sql_server_service:
        debug_info["errors"].append("SQL Server service not initialized")
        return debug_info
    
    try:
        # Check if local database exists
        import os
        db_exists = os.path.exists(sql_server_service.local_db_path)
        debug_info["local_db_exists"] = db_exists
        
        # Get uploaded tables
        uploaded_tables = sql_server_service.get_uploaded_tables()
        debug_info["uploaded_tables"] = uploaded_tables
        debug_info["uploaded_count"] = len(uploaded_tables)
        
        # Try to query each uploaded table
        for table in uploaded_tables:
            table_name = table["name"]
            try:
                sample_data = sql_server_service.query_uploaded_table(f"SELECT * FROM {table_name} LIMIT 3")
                debug_info[f"sample_data_{table_name}"] = sample_data
            except Exception as e:
                debug_info["errors"].append(f"Error querying {table_name}: {str(e)}")
                
    except Exception as e:
        debug_info["errors"].append(f"Debug failed: {str(e)}")
    
    return debug_info

@app.get("/debug/table_matching")
async def debug_table_matching(question: str = "show me cost data"):
    """Debug endpoint to test the fuzzy table matching"""
    global sql_server_service
    
    debug_info = {
        "question": question,
        "table_matching_results": {},
        "errors": []
    }
    
    try:
        # Test the new fuzzy matching
        debug_info["table_matching_results"]["fuzzy_match"] = find_best_table_match(question)
        
        # Test the extract table function (which uses fuzzy matching)
        debug_info["table_matching_results"]["extract_table_result"] = extract_table_name_from_question(question)
        
        # Get all available tables for reference
        all_tables = get_all_available_tables()
        debug_info["table_matching_results"]["available_tables_count"] = len(all_tables)
        debug_info["table_matching_results"]["available_tables_sample"] = all_tables[:5] if all_tables else []
        
        # Show cache status
        debug_info["table_matching_results"]["cache_status"] = {
            "has_cached_tables": table_list_cache["tables"] is not None,
            "last_updated": table_list_cache["last_updated"],
            "cache_duration": table_list_cache["cache_duration"]
        }
        
    except Exception as e:
        debug_info["errors"].append(f"Table matching debug failed: {str(e)}")
    
    return debug_info

@app.get("/debug/sql_validation")
async def debug_sql_validation(sql: str = "SELECT TOP 10 * FROM table1 ORDER BY id OFFSET 5 ROWS"):
    """Debug endpoint to test SQL validation without executing"""
    debug_info = {
        "original_sql": sql,
        "validation_results": {},
        "errors": []
    }
    
    try:
        # Test SQL validation and fixing
        cleaned_sql = clean_sql_query(sql)
        debug_info["validation_results"]["cleaned_sql"] = cleaned_sql
        debug_info["validation_results"]["validation_passed"] = True
        debug_info["validation_results"]["was_fixed"] = cleaned_sql != sql
        
        # Analyze the SQL for potential issues
        sql_upper = sql.upper()
        cleaned_upper = cleaned_sql.upper()
        debug_info["validation_results"]["analysis"] = {
            "original": {
                "has_top": "TOP" in sql_upper,
                "has_offset": "OFFSET" in sql_upper,
                "has_fetch_next": "FETCH NEXT" in sql_upper,
                "has_limit": "LIMIT" in sql_upper,
                "has_select": "SELECT" in sql_upper,
                "has_uploaded_table": "UPLOADED_" in sql_upper,
                "top_offset_conflict": "TOP" in sql_upper and "OFFSET" in sql_upper
            },
            "fixed": {
                "has_top": "TOP" in cleaned_upper,
                "has_offset": "OFFSET" in cleaned_upper,
                "has_fetch_next": "FETCH NEXT" in cleaned_upper,
                "has_limit": "LIMIT" in cleaned_upper,
                "has_select": "SELECT" in cleaned_upper,
                "top_offset_conflict": "TOP" in cleaned_upper and "OFFSET" in cleaned_upper
            }
        }
        
        # Test some common problematic patterns
        test_cases = [
            "SELECT TOP 100 * FROM users ORDER BY id OFFSET 10 ROWS",
            "SELECT TOP 50 * FROM products ORDER BY name OFFSET 20 ROWS FETCH NEXT 30 ROWS ONLY",
            "SELECT * FROM orders ORDER BY date OFFSET 0 ROWS FETCH NEXT 25 ROWS ONLY",
            "SELECT TOP 200 id, name FROM customers"
        ]
        
        debug_info["validation_results"]["test_cases"] = []
        for test_sql in test_cases:
            try:
                fixed_test = clean_sql_query(test_sql)
                debug_info["validation_results"]["test_cases"].append({
                    "original": test_sql,
                    "fixed": fixed_test,
                    "was_changed": fixed_test != test_sql
                })
            except Exception as test_error:
                debug_info["validation_results"]["test_cases"].append({
                    "original": test_sql,
                    "error": str(test_error)
                })
        
    except Exception as e:
        debug_info["errors"].append(f"SQL validation failed: {str(e)}")
        debug_info["validation_results"]["validation_passed"] = False
    
    return debug_info

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

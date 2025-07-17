import os
import sqlite3
import uvicorn
import re
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import pandas as pd
import io
from datetime import datetime

from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from init_db import init_database

# Global variables
DB_PATH = "data.db"  # Database is now in the same directory as app.py
last_query_results = []

# Pydantic models for request/response
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    sql_query: str


def clean_sql_query(raw_sql: str) -> str:
    """
    Clean and extract SQL query from LangChain response
    Handles various formatting issues like code blocks, extra text, etc.
    """
    if not raw_sql:
        raise ValueError("Empty SQL response")
    
    # Store original for debugging
    original_sql = raw_sql
    print(f"🔧 Starting clean_sql_query with: '{raw_sql}'")
    
    try:
        # Remove common prefixes
        sql = re.sub(r'^(SQLQuery:\s*|SQL:\s*|Query:\s*)', '', raw_sql, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove markdown code blocks
        sql = re.sub(r'```sql\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'```\s*', '', sql)
        sql = re.sub(r'`([^`]+)`', r'\1', sql)  # Remove single backticks
        
        # Extract SQL from between markdown blocks if present
        code_block_match = re.search(r'```(?:sql)?\s*(.*?)\s*```', raw_sql, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            sql = code_block_match.group(1).strip()
        
        # Remove common explanatory text patterns
        sql = re.sub(r'(Here is the SQL query|The SQL query is|This query will).*?:', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'(Explanation|Note|Answer):\s*.*$', '', sql, flags=re.IGNORECASE | re.MULTILINE)
        
        # CRITICAL FIX: Remove any text before the first SQL keyword
        # This handles cases like "select all customers SELECT ..." 
        sql_keyword_pattern = r'.*?(?=\b(?:SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|WITH)\b)'
        sql = re.sub(sql_keyword_pattern, '', sql, flags=re.IGNORECASE | re.DOTALL)
        sql = sql.strip()
        
        # Remove SQL comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Clean up whitespace and newlines
        sql = re.sub(r'\s+', ' ', sql)  # Replace multiple whitespace with single space
        sql = sql.strip()
        
        # Extract first complete SQL statement if multiple are present
        # Look for SELECT, INSERT, UPDATE, DELETE, WITH statements
        sql_patterns = [
            r'(WITH\s+.*?(?:SELECT|INSERT|UPDATE|DELETE).*?)(?:;|\s*$)',
            r'(SELECT\s+.*?)(?:;|\s*$)',
            r'(INSERT\s+.*?)(?:;|\s*$)',
            r'(UPDATE\s+.*?)(?:;|\s*$)',
            r'(DELETE\s+.*?)(?:;|\s*$)',
            r'(CREATE\s+.*?)(?:;|\s*$)',
            r'(DROP\s+.*?)(?:;|\s*$)'
        ]
        
        for pattern in sql_patterns:
            match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)
            if match:
                sql = match.group(1).strip()
                break
        
        # Remove trailing semicolon if present (SQLite doesn't require it)
        sql = sql.rstrip(';').strip()
        
        # Final validation - must contain SQL keywords
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'WITH']
        if not any(keyword in sql.upper() for keyword in sql_keywords):
            raise ValueError(f"No valid SQL keywords found in cleaned query: {sql}")
        
        # Additional validation - must not be empty
        if not sql or len(sql.strip()) < 5:
            raise ValueError(f"Cleaned SQL query too short: {sql}")
        
        print(f"🎯 Final cleaned SQL: '{sql}'")
        return sql
        
    except Exception as e:
        raise ValueError(f"Failed to clean SQL query. Original: '{original_sql}', Error: {str(e)}")

# Load environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyB6qjvLibk0gj36C8rlQjKpQLTjZEucP0Y")

app = FastAPI(title="SQL Query API", description="API for natural language to SQL queries", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and models once at startup
init_database(DB_PATH=DB_PATH) 
db = SQLDatabase.from_uri(f"sqlite:///{DB_PATH}")

llm = ChatGoogleGenerativeAI(
    google_api_key=google_api_key,
    model="gemini-1.5-flash",
    temperature=0.0,
)

# Create the query chain and execution tool
sql_chain = create_sql_query_chain(llm, db, k=10000000) #remove the limit here

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
            "POST /execute_sql": "Execute SQL query directly",
            "POST /query": "Generate and execute natural language query",
            "GET /download/csv": "Download last query results as CSV",
            "GET /download/excel": "Download last query results as Excel"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint - tests database connection"""
    try:
        # Test database connection
        tables = db.get_usable_table_names()
        return {
            "status": "healthy", 
            "database": "connected", 
            "tables_count": len(tables),
            "tables": tables
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

@app.post("/generate_sql")
async def generate_sql(request: QueryRequest):
    """Generate SQL query from natural language"""
    try:
        # Generate SQL using LangChain
        raw_sql = sql_chain.invoke({"question": request.question})
        
        # Clean up the SQL query using our robust function
        sql_query = clean_sql_query(raw_sql)
        
        return {
            "sql_query": sql_query, 
            "question": request.question,
            "raw_response": raw_sql  # Include original for debugging
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL Generation Error: {e}")

@app.post("/execute_sql")
def execute_sql(request: QueryRequest):
    """Execute SQL query directly (expects SQL in the question field)"""
    global last_query_results
    try:
        # The question field should contain the SQL query
        sql_query = request.question.strip()
        
        # Basic validation
        if not sql_query:
            raise ValueError("Empty SQL query")
        
        # Execute the query using both methods for consistency
        result = db.run(sql_query)
        
        # Also get structured results
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        result_dicts = [dict(row) for row in rows]
        
        # Store results for download
        last_query_results = result_dicts
        
        cursor.close()
        conn.close()
        
        return {
            "sql_query": sql_query,
            "rows": result_dicts,
            "count": len(result_dicts),
            "raw_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL Execution Error: {e}")

@app.post("/query")
async def execute_natural_language_query(request: QueryRequest):
    """Generate SQL from natural language and execute it"""
    global last_query_results
    try:
        # Generate SQL using LangChain
        raw_sql = sql_chain.invoke({"question": request.question})
        
        # Clean up the SQL query using our robust function
        sql_query = clean_sql_query(raw_sql)
        
        # Execute the query
        result = db.run(sql_query)
        
        # Also get structured results
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        result_dicts = [dict(row) for row in rows]
        
        # Store results for download
        last_query_results = result_dicts
        
        cursor.close()
        conn.close()
        
        return {
            "question": request.question,
            "sql_query": sql_query,
            "rows": result_dicts,
            "count": len(result_dicts),
            "raw_result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query Error: {str(e)}")

@app.get("/download/csv")
def download_csv():
    """Download query results as CSV file"""
    global last_query_results
    if not last_query_results:
        raise HTTPException(status_code=400, detail="No query results to download")
    
    try:
        # Convert to DataFrame
        df = pd.DataFrame(last_query_results)
        
        # Create CSV in memory
        output = io.StringIO()
        df.to_csv(output, index=False)
        csv_content = output.getvalue()
        output.close()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"query_results_{timestamp}.csv"
        
        # Convert string to bytes
        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))
        
        # Return as streaming response
        return StreamingResponse(
            csv_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating CSV: {str(e)}")

@app.get("/download/excel")
def download_excel():
    """Download query results as Excel file"""
    global last_query_results
    if not last_query_results:
        raise HTTPException(status_code=400, detail="No query results to download")
    
    try:
        # Convert to DataFrame
        df = pd.DataFrame(last_query_results)
        
        # Create Excel in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Query Results', index=False)
        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"query_results_{timestamp}.xlsx"
        
        # Return as streaming response
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel: {str(e)}")

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

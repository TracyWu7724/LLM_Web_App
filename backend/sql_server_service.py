import os
import pandas as pd
from typing import List, Dict, Any, Optional
import pyodbc
from dotenv import load_dotenv
import sqlite3
import logging
import urllib.parse
import threading
from queue import Queue
import time
from cache_service import db_cache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionPool:
    """Simple connection pool for SQL Server connections"""
    
    def __init__(self, connection_string: str, max_connections: int = 5, timeout: int = 30):
        self.connection_string = connection_string
        self.max_connections = max_connections
        self.timeout = timeout
        self.pool = Queue(maxsize=max_connections)
        self.lock = threading.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        for _ in range(self.max_connections):
            try:
                conn = pyodbc.connect(self.connection_string)
                self.pool.put(conn)
            except Exception as e:
                logger.error(f"Failed to create connection for pool: {e}")
    
    def get_connection(self):
        """Get a connection from the pool"""
        try:
            # Try to get from pool with timeout
            conn = self.pool.get(timeout=10)
            # Test if connection is still valid
            try:
                conn.execute("SELECT 1")
                return conn
            except Exception as e:
                logger.warning(f"Connection test failed, creating new connection: {e}")
                # Connection is dead, create new one
                try:
                    conn.close()
                except:
                    pass
                conn = pyodbc.connect(self.connection_string)
                return conn
        except Exception as e:
            logger.warning(f"Pool empty or timeout, creating new connection: {e}")
            # Pool is empty or timeout, create new connection
            return pyodbc.connect(self.connection_string)
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        try:
            if not self.pool.full():
                self.pool.put(conn, block=False)
            else:
                conn.close()
        except:
            conn.close()

class SQLServerService:
    """Service class for SQL Server database operations"""
    
    def __init__(self):
        # SQL Server configuration
        self.server = os.getenv("SQL_SERVER_HOST")
        self.database = os.getenv("SQL_SERVER_DATABASE")
        self.username = os.getenv("SQL_SERVER_USERNAME")
        self.password = os.getenv("SQL_SERVER_PASSWORD")
        self.port = os.getenv("SQL_SERVER_PORT", "1433")
        self.driver = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 18 for SQL Server")
        
        # Fallback to local SQLite for query history
        self.local_db_path = "data.db"
        
        # Initialize connection pool
        self.connection_pool = None
        self._init_connection_pool()
        
        # Validate configuration
        if not all([self.server, self.database, self.username, self.password]):
            logger.warning("SQL Server configuration incomplete. Please set SQL_SERVER_HOST, SQL_SERVER_DATABASE, SQL_SERVER_USERNAME, and SQL_SERVER_PASSWORD")
    
    def _init_connection_pool(self):
        """Initialize the connection pool"""
        try:
            connection_string = self.get_connection_string()
            self.connection_pool = ConnectionPool(connection_string, max_connections=5, timeout=30)
            logger.info("Connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            self.connection_pool = None
    
    def get_connection_string(self):
        """Get SQL Server connection string"""
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server},{self.port};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            f"TrustServerCertificate=yes;"
            f"Encrypt=yes;"
            f"Connection Timeout=30;"
            f"Command Timeout=60;"
        )
    
    def get_sql_server_connection(self):
        """Get a connection from the pool"""
        if self.connection_pool:
            return self.connection_pool.get_connection()
        else:
            # Fallback to direct connection if pool failed
            connection_string = self.get_connection_string()
            logger.info(f"Connecting to SQL Server: {self.server}:{self.port}/{self.database}")
            return pyodbc.connect(connection_string)
    
    def return_connection(self, conn):
        """Return a connection to the pool"""
        if self.connection_pool:
            self.connection_pool.return_connection(conn)
        else:
            conn.close()
    
    def execute_query(self, query: str, timeout_seconds: int = 60, custom_limit: int = None) -> List[Dict[str, Any]]:
        """Execute a query on SQL Server and return results as list of dictionaries"""
        import threading
        import time
        
        # Check cache first for SELECT queries (not for INSERT/UPDATE/DELETE)
        query_upper = query.upper().strip()
        is_select_query = query_upper.startswith('SELECT')
        
        if is_select_query:
            cached_result = db_cache.get_query_result(query, custom_limit)
            if cached_result:
                logger.debug(f"Query cache hit: {len(cached_result)} rows")
                return cached_result
        
        # Add automatic TOP clause with intelligent defaults for better performance
        # BUT: Don't add TOP if query already contains OFFSET (SQL Server limitation)
        has_offset = "OFFSET" in query_upper
        has_top = "TOP" in query_upper
        has_fetch_next = "FETCH NEXT" in query_upper or "FETCH FIRST" in query_upper
        is_select = "SELECT" in query_upper
        is_special = "COUNT(" in query_upper or "DESCRIBE" in query_upper
        
        # Don't add TOP if query already uses OFFSET...FETCH NEXT pagination
        has_pagination = has_offset or has_fetch_next
        
        if custom_limit is not None and custom_limit > 0:
            # User specified a custom limit - use it
            if not has_top and not has_pagination and is_select and not is_special:
                query = query.replace("SELECT", f"SELECT TOP {custom_limit}", 1)
                logger.info(f"Added custom TOP {custom_limit} to query")
            elif has_pagination:
                logger.info(f"Skipping TOP addition because query uses pagination (OFFSET/FETCH NEXT)")
        elif custom_limit is None:
            # User wants ALL data - but add safety limit for performance
            if not has_top and not has_pagination and is_select and not is_special:
                # Add intelligent safety limit based on query type
                if "DISTINCT" in query_upper or "GROUP BY" in query_upper:
                    safety_limit = 5000  # Higher limit for aggregation queries
                else:
                    safety_limit = 10000  # Default safety limit
                query = query.replace("SELECT", f"SELECT TOP {safety_limit}", 1)
                logger.info(f"Added safety TOP {safety_limit} to unlimited query for performance")
            elif has_pagination:
                logger.info(f"Skipping safety TOP addition because query uses pagination")
        elif not has_top and not has_pagination and is_select and not is_special:
            # Default behavior - add safety TOP
            query = query.replace("SELECT", f"SELECT TOP {custom_limit}", 1)
            logger.info(f"Added TOP {custom_limit} to query for safety")
        elif has_pagination:
            logger.info(f"Skipping TOP addition because query uses pagination")
        
        logger.info(f"Executing query with {timeout_seconds}s timeout: {query[:100]}...")
        
        result_container = {"result": None, "error": None, "completed": False}
        
        def execute_with_timeout():
            connection = None
            try:
                connection = self.get_sql_server_connection()
                
                with connection.cursor() as cursor:
                    # Execute query (timeout handled by our threading mechanism)
                    cursor.execute(query)
                    
                    # Get column names
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        logger.info(f"Query returned {len(columns)} columns")
                    else:
                        logger.warning("No columns returned from query")
                        result_container["result"] = []
                        result_container["completed"] = True
                        return
                    
                    # Fetch results in chunks to avoid memory issues
                    result = []
                    chunk_size = 1000  # Process 1000 rows at a time
                    rows_fetched = 0
                    
                    while True:
                        rows = cursor.fetchmany(chunk_size)
                        if not rows:
                            break
                        
                        # Convert chunk to dictionaries
                        for row in rows:
                            result.append(dict(zip(columns, row)))
                        
                        rows_fetched += len(rows)
                        logger.info(f"Processed {rows_fetched} rows so far...")
                        
                        # Check if we're taking too long
                        if rows_fetched > 10000:  # If we have more than 10k rows
                            logger.warning(f"Large result set detected ({rows_fetched} rows). Consider adding filters.")
                    
                    result_container["result"] = result
                    result_container["completed"] = True
                    logger.info(f"Query completed successfully: {len(result)} rows returned")
                    
            except Exception as e:
                logger.error(f"Query execution error: {e}")
                result_container["error"] = str(e)
                result_container["completed"] = True
            finally:
                # Always return connection to pool
                if connection:
                    self.return_connection(connection)
        
        # Run query in a separate thread
        query_thread = threading.Thread(target=execute_with_timeout)
        query_thread.daemon = True
        query_thread.start()
        
        # Wait for completion or timeout
        start_time = time.time()
        while not result_container["completed"] and (time.time() - start_time) < timeout_seconds:
            time.sleep(0.1)  # Check every 100ms
        
        if not result_container["completed"]:
            logger.error(f"Query timed out after {timeout_seconds} seconds")
            raise TimeoutError(f"Query timed out after {timeout_seconds} seconds. Try:\n• Adding more specific filters (e.g., WHERE conditions)\n• Using smaller date ranges\n• Adding TOP clauses\n• Simplifying the query")
        
        if result_container["error"]:
            raise Exception(result_container["error"])
        
        # Cache the result if it's a SELECT query and reasonable size
        result = result_container["result"] or []
        if is_select_query and result and len(result) <= 5000:
            # Determine cache TTL based on query type
            cache_ttl = 300  # 5 minutes default
            if "COUNT(" in query_upper or "SUM(" in query_upper:
                cache_ttl = 600  # 10 minutes for aggregations
            elif "DISTINCT" in query_upper:
                cache_ttl = 900  # 15 minutes for distinct queries
            
            db_cache.set_query_result(query, result, custom_limit, ttl=cache_ttl)
            logger.debug(f"Cached query result: {len(result)} rows (TTL: {cache_ttl}s)")
        
        return result
    
    def get_table_names(self) -> List[str]:
        """Get all available table names from SQL Server"""
        # Try cache first
        cached_tables = db_cache.get_table_list(include_sql_server=True)
        if cached_tables:
            logger.debug(f"Table list cache hit: {len(cached_tables)} tables")
            return cached_tables
        
        try:
            query = """
            SELECT 
                SCHEMA_NAME(schema_id) + '.' + name as table_name
            FROM sys.tables 
            WHERE is_ms_shipped = 0
            ORDER BY SCHEMA_NAME(schema_id), name
            """
            
            # Use shorter timeout for metadata queries
            results = self.execute_query(query, timeout_seconds=15)
            
            # Extract table names
            table_names = []
            for row in results:
                table_name = row.get('table_name') or list(row.values())[0]
                table_names.append(table_name)
            
            # Cache the result
            if table_names:
                db_cache.set_table_list(table_names, include_sql_server=True)
                logger.debug(f"Cached table list: {len(table_names)} tables")
            
            logger.info(f"Successfully discovered {len(table_names)} tables")
            return table_names
            
        except Exception as e:
            logger.error(f"Error getting table names: {e}")
            return []
    
    def get_all_schemas_and_tables(self) -> List[Dict[str, str]]:
        """Get all schemas and their tables with metadata for similarity matching"""
        try:
            query = """
            SELECT 
                s.name as schema_name,
                t.name as table_name,
                SCHEMA_NAME(t.schema_id) + '.' + t.name as full_table_name,
                CAST(ep.value AS NVARCHAR(4000)) as table_description
            FROM sys.schemas s
            LEFT JOIN sys.tables t ON s.schema_id = t.schema_id AND t.is_ms_shipped = 0
            LEFT JOIN sys.extended_properties ep ON t.object_id = ep.major_id 
                AND ep.minor_id = 0 AND ep.name = 'MS_Description'
            WHERE s.name NOT IN ('sys', 'INFORMATION_SCHEMA', 'guest', 'db_owner', 'db_accessadmin', 
                                'db_securityadmin', 'db_ddladmin', 'db_datareader', 'db_datawriter', 
                                'db_denydatareader', 'db_denydatawriter', 'db_backupoperator')
            ORDER BY s.name, t.name
            """
            
            results = self.execute_query(query, timeout_seconds=15)
            
            all_tables = []
            for row in results:
                schema_name = row.get('schema_name')
                table_name = row.get('table_name')
                full_table_name = row.get('full_table_name')
                description = row.get('table_description') or ''
                
                if table_name:  # Only add if table exists (LEFT JOIN might return schema with no tables)
                    all_tables.append({
                        'table_name': table_name,
                        'full_name': full_table_name,
                        'description': description,
                        'schema': schema_name
                    })
            
            logger.info(f"Successfully discovered {len(all_tables)} tables from all schemas")
            return all_tables
            
        except Exception as e:
            logger.error(f"Error getting schemas and tables: {e}")
            return []
    
    def get_table_schema(self, table_name: str) -> List[Dict[str, str]]:
        """Get schema information for a specific table"""
        # Try cache first
        cached_schema = db_cache.get_table_schema(table_name)
        if cached_schema:
            logger.debug(f"Schema cache hit for table: {table_name}")
            return cached_schema
        
        connection = None
        try:
            # Parse table name to handle schema.table format
            if '.' in table_name:
                schema_name, table_name_only = table_name.split('.', 1)
            else:
                schema_name = 'das'
                table_name_only = table_name
            
            query = """
            SELECT 
                COLUMN_NAME as column_name,
                DATA_TYPE as data_type,
                IS_NULLABLE as is_nullable,
                CHARACTER_MAXIMUM_LENGTH as max_length
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
            """
            
            # Use shorter timeout for metadata queries
            connection = self.get_sql_server_connection()
            with connection.cursor() as cursor:
                cursor.execute(query, schema_name, table_name_only)
                rows = cursor.fetchall()
                
                schema = []
                for row in rows:
                    schema.append({
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == 'YES',
                        "max_length": row[3] if row[3] else None
                    })
                
                # Cache the result
                if schema:
                    db_cache.set_table_schema(table_name, schema)
                    logger.debug(f"Cached schema for table: {table_name}")
                
                return schema
        
        except Exception as e:
            logger.error(f"Error getting table schema for {table_name}: {e}")
            return []
        finally:
            if connection:
                self.return_connection(connection)
    
    def get_table_preview(self, table_name: str, limit: int = 5) -> Dict[str, Any]:
        """Get a preview of table data"""
        try:
            # Check if this is an uploaded table (SQLite) or SQL Server table
            is_uploaded_table = table_name.startswith("uploaded_")
            
            if is_uploaded_table:
                # Use SQLite syntax for uploaded tables
                query = f"SELECT * FROM {table_name} LIMIT {limit}"
                rows = self.query_uploaded_table(query)
                
                # Get schema info for uploaded table
                schema = self.get_table_schema(table_name)
                columns = [col["name"] for col in schema] if schema else []
                
                # Get total row count for uploaded table
                try:
                    count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                    count_result = self.query_uploaded_table(count_query)
                    total_rows = count_result[0]["count"] if count_result else len(rows)
                except:
                    total_rows = len(rows)  # Fallback if count fails
            else:
                # Use SQL Server syntax for regular tables
                query = f"SELECT TOP {limit} * FROM {table_name}"
                rows = self.execute_query(query)
                
                # Get schema info
                schema = self.get_table_schema(table_name)
                columns = [col["name"] for col in schema]
                
                # Get total row count (if possible)
                try:
                    count_query = f"SELECT COUNT(*) as count FROM {table_name}"
                    count_result = self.execute_query(count_query)
                    total_rows = count_result[0]["count"] if count_result else len(rows)
                except:
                    total_rows = len(rows)  # Fallback if count fails
            
            return {
                "table_name": table_name,
                "columns": columns,
                "rows": rows,
                "preview_count": len(rows),
                "total_rows": total_rows
            }
        except Exception as e:
            logger.error(f"Error getting table preview for {table_name}: {e}")
            raise
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the SQL Server connection"""
        try:
            # Try a simple query
            result = self.execute_query("SELECT 1 as test")
            tables = self.get_table_names()
            
            return {
                "status": "success",
                "message": "SQL Server connection successful",
                "tables_count": len(tables),
                "sample_tables": tables[:5]  # Show first 5 tables
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"SQL Server connection failed: {str(e)}"
            }
    
    def analyze_query_performance(self, query: str) -> Dict[str, Any]:
        """Analyze query performance and provide optimization suggestions"""
        try:
            # Add SET STATISTICS IO ON to get performance metrics
            performance_query = f"""
            SET STATISTICS IO ON;
            SET STATISTICS TIME ON;
            {query}
            SET STATISTICS IO OFF;
            SET STATISTICS TIME OFF;
            """
            
            connection = None
            try:
                connection = self.get_sql_server_connection()
                with connection.cursor() as cursor:
                    # Execute with performance monitoring
                    cursor.execute(performance_query)
                    
                    # Get the actual results
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        result = [dict(zip(columns, row)) for row in rows]
                    else:
                        result = []
                    
                    return {
                        "query": query,
                        "result_count": len(result),
                        "performance_analysis": {
                            "message": "Query executed successfully",
                            "suggestions": self._generate_optimization_suggestions(query, len(result))
                        }
                    }
                    
            finally:
                if connection:
                    self.return_connection(connection)
                    
        except Exception as e:
            return {
                "query": query,
                "error": str(e),
                "performance_analysis": {
                    "message": "Query analysis failed",
                    "suggestions": ["Check query syntax", "Verify table permissions", "Ensure proper WHERE clauses"]
                }
            }
    
    def _generate_optimization_suggestions(self, query: str, result_count: int) -> List[str]:
        """Generate optimization suggestions based on query analysis"""
        suggestions = []
        query_upper = query.upper()
        
        # Check for common performance issues
        if "SELECT *" in query_upper and result_count > 1000:
            suggestions.append("Consider selecting specific columns instead of SELECT * for large datasets")
        
        if "WHERE" not in query_upper and result_count > 100:
            suggestions.append("Add WHERE clauses to filter data and improve performance")
        
        if "ORDER BY" in query_upper and result_count > 1000:
            suggestions.append("Consider adding TOP clause before ORDER BY for large result sets")
        
        if "JOIN" in query_upper and "ON" not in query_upper:
            suggestions.append("Ensure all JOINs have proper ON clauses")
        
        if result_count > 10000:
            suggestions.append("Large result set detected. Consider pagination or more specific filters")
        
        if "LIKE '%" in query_upper:
            suggestions.append("Leading wildcards in LIKE clauses can't use indexes. Consider different patterns")
        
        return suggestions

    # Local SQLite methods for uploaded files and query history
    def init_local_db(self):
        """Initialize local SQLite database for uploaded files and query history"""
        conn = sqlite3.connect(self.local_db_path)
        cursor = conn.cursor()
        
        # Create recent queries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recent_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create table metadata table for uploaded files
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS table_metadata (
                table_name TEXT PRIMARY KEY,
                original_filename TEXT,
                file_extension TEXT,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_query_to_history(self, query_text: str):
        """Save a query to the recent queries history"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO recent_queries (query_text, created_at) 
                VALUES (?, CURRENT_TIMESTAMP)
            ''', (query_text.strip(),))
            
            conn.commit()
            conn.close()
            logger.info(f"Saved query to history: {query_text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to save query to history: {e}")
    
    def get_recent_queries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent queries from local database"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT query_text, created_at 
                FROM recent_queries 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            recent_queries = [dict(row) for row in rows]
            
            conn.close()
            return recent_queries
        except Exception as e:
            logger.error(f"Error getting recent queries: {e}")
            return []
    
    def handle_uploaded_file(self, df: pd.DataFrame, table_name: str, original_filename: str = None, file_extension: str = None) -> Dict[str, Any]:
        """Store uploaded file in local SQLite database with metadata"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Drop table if it exists
            conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Create table with pandas
            df.to_sql(table_name, conn, index=False, if_exists='replace')
            
            # Store metadata if provided
            if original_filename and file_extension:
                cursor.execute('''
                    INSERT OR REPLACE INTO table_metadata (table_name, original_filename, file_extension)
                    VALUES (?, ?, ?)
                ''', (table_name, original_filename, file_extension))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "table_name": table_name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "original_filename": original_filename,
                "file_extension": file_extension
            }
        except Exception as e:
            logger.error(f"Error handling uploaded file: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_table_metadata(self, table_name: str) -> Dict[str, Any]:
        """Get metadata for an uploaded table"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT original_filename, file_extension, upload_date
                FROM table_metadata 
                WHERE table_name = ?
            ''', (table_name,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return dict(row)
            else:
                return {}
        except Exception as e:
            logger.error(f"Error getting table metadata for {table_name}: {e}")
            return {}
    
    def get_uploaded_tables(self) -> List[Dict[str, Any]]:
        """Get information about uploaded tables in local SQLite"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Get uploaded tables (tables that start with "uploaded_")
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                AND name LIKE 'uploaded_%'
                AND name NOT LIKE 'sqlite_%'
            """)
            
            tables = cursor.fetchall()
            table_info = []
            
            for table_name_tuple in tables:
                table_name = table_name_tuple[0]
                
                # Get column info
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                # Get original filename metadata
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                original_filename_row = cursor.fetchone()
                original_filename = original_filename_row[0] if original_filename_row else None
                
                table_info.append({
                    "name": table_name,
                    "columns": [{"name": col[1], "type": col[2]} for col in columns],
                    "row_count": row_count,
                    "is_uploaded": True,
                    "source": "local",
                    "original_filename": original_filename
                })
            
            conn.close()
            return table_info
        except Exception as e:
            logger.error(f"Error getting uploaded tables: {e}")
            return []
    
    def query_uploaded_table(self, query: str) -> List[Dict[str, Any]]:
        """Execute query on local SQLite database (for uploaded tables)"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(query)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]
            
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Error querying uploaded table: {e}")
            raise
    
    def delete_uploaded_table(self, table_name: str) -> Dict[str, Any]:
        """Delete an uploaded table from local SQLite database"""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, (table_name,))
            
            if not cursor.fetchone():
                conn.close()
                return {
                    "success": False,
                    "error": f"Table '{table_name}' not found"
                }
            
            # Delete the table
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Delete metadata if it exists
            cursor.execute("DELETE FROM table_metadata WHERE table_name=?", (table_name,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully deleted uploaded table: {table_name}")
            return {
                "success": True,
                "message": f"Table '{table_name}' deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deleting uploaded table {table_name}: {e}")
            return {
                "success": False,
                "error": str(e)
            } 

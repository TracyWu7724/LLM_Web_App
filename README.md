# SQL Query Assistant

A full-stack application that enables users to query databases using natural language. The system leverages Large Language Models (LLMs) to translate user questions into SQL queries, executes them against connected databases, and presents results through an interactive web interface.

<img src="./Full Stack Text-to-SQL.png" alt="Website Overview" />

## Features

- **Natural Language to SQL**: Convert plain English questions into SQL queries using AI
- **Interactive Chat Interface**: Conversational UI for seamless database interactions
- **Real-time Query Execution**: Execute queries and display results instantly
- **Multiple Database Support**: Connect to SQL Server, SQLite, Databricks, and other databases
- **Data Export**: Download query results as CSV or Excel files
- **Query History**: Track and revisit previous queries
- **Network Access**: Access the application from multiple devices on the same network


## Installation

```bash
# Clone the repository
git clone https://github.com/TracyWu7724/LLM_Web_App.git
cd LLM_Web_App

# Install the backend dependencies
cd backend
pip3 install -r requirements.txt

# Install the frontend dependencies
npm install

```



## Configuration

### Database configurations

Create a `.env` file in the `backend` directory with the following variables:

```env
# Database Configuration
DB_SERVER=your_server_address
DB_NAME=your_database_name
DB_USERNAME=your_username
DB_PASSWORD=your_password

# LLM API Configuration
GEMINI_API_KEY=your_api_key

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

## Quick Start


```bash
# Start the backend server
cd backend
python3 app.py

# Start the frontend application
# From project root
cd frontend
npm start
```

## API Endpoints

### Core Endpoints

- `GET /` - API information and available endpoints
- `GET /health` - Health check and database connection status
- `POST /query` - Execute natural language query (generate SQL + execute)
- `POST /generate_sql` - Generate SQL from natural language (no execution)
- `POST /execute_sql` - Execute SQL query directly
- `GET /tables` - List all available database tables
- `GET /tables/{table_name}` - Get schema and preview for a specific table

### Data Export

- `GET /download/csv` - Download last query results as CSV
- `GET /download/excel` - Download last query results as Excel (.xlsx)

### Query Management

- `GET /query_history` - Retrieve query history
- `DELETE /query_history` - Clear query history

## Project Structure

```
LLM_Web_App/
├── backend/
│   ├── app.py                    # FastAPI application entry point
│   ├── sql_server_service.py     # SQL Server database connector
│   ├── databricks_service.py     # Databricks integration (if applicable)
│   ├── cache_service.py          # Query caching service
│   ├── requirements.txt          # Python dependencies
│   └── data.db                   # SQLite database (for query history)
├── public/                       # Static files
├── src/                          # React source code
│   ├── components/               # React components
│   ├── services/                 # API service clients
│   └── types/                    # TypeScript type definitions
├── package.json                  # Node.js dependencies

```

## Troubleshooting

### Backend Issues

- **Database Connection Failed**: Verify database credentials in `.env` file
- **LLM API Errors**: Check API key validity and quota limits
- **Port Already in Use**: Change the port in `app.py` or kill the process using the port

### Frontend Issues

- **Cannot Connect to Backend**: Ensure backend is running and CORS is configured
- **Build Errors**: Clear node_modules and reinstall: `rm -rf node_modules && npm install`




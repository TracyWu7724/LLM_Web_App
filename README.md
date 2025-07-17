# SQL Query Assistant

A full-stack application that allows users to query databases using natural language, powered by FastAPI and React.

## 🚀 Quick Start

#### 1. Backend Setup (FastAPI + Database)

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
python app.py
```

#### 2. Frontend Setup (React)

```bash
# Navigate to frontend directory  
cd frontend

# Install Node.js dependencies
npm install

# Start the React development server
npm start
```

## 🌐 Network Access

### Local Access
- **Backend API**: http://localhost:8000
- **Frontend App**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

> **Note**: Replace `10.16.56.77` with your actual local IP address. To find your IP:
> ```bash
> ipconfig | findstr /i "IPv4"
> ```

### Firewall Configuration (if needed)
If other devices can't connect, allow the ports through Windows Firewall:
```powershell
# Run PowerShell as Administrator
netsh advfirewall firewall add rule name="React Dev Server" dir=in action=allow protocol=TCP localport=3000
netsh advfirewall firewall add rule name="FastAPI Backend" dir=in action=allow protocol=TCP localport=8000
```

## 🔧 Features

- **Natural Language to SQL**: Convert questions into SQL queries using AI
- **Interactive Chat Interface**: Conversational UI for database queries
- **Real-time Results**: Display query results in interactive tables
- **Data Export**: Download results as CSV or Excel files
- **Network Access**: Access from multiple devices on the same network
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Debug Panel**: Development tools for SQL query inspection

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern Python web framework
- **LangChain**: AI/ML framework for natural language processing
- **Google Gemini**: Language model for SQL generation
- **SQLite**: Lightweight database
- **Pandas**: Data manipulation and analysis
- **Uvicorn**: ASGI server

### Frontend
- **React 19**: Latest JavaScript library for building user interfaces
- **TypeScript**: Type-safe JavaScript
- **Tailwind CSS**: Utility-first CSS framework
- **Framer Motion**: Animation library
- **Lucide React**: Icon library
- **React Router**: Client-side routing

## 🔍 API Endpoints

- `GET /` - API information and available endpoints
- `GET /health` - Health check and database connection status
- `POST /query` - Execute natural language queries (generate + execute)
- `POST /generate_sql` - Generate SQL from natural language only
- `POST /execute_sql` - Execute SQL query directly
- `GET /download/csv` - Download last query results as CSV
- `GET /download/excel` - Download last query results as Excel

## 🔧 Configuration

### Backend Configuration
The backend is configured in `backend/app.py`:
- **Host**: `0.0.0.0` (accepts connections from any IP)
- **Port**: `8000`
- **Database**: SQLite (`data.db`)

### Frontend Configuration
API configuration is in `frontend/src/config/api.ts`:
- **Base URL**: Configurable via environment variable or defaults to local IP
- **Timeout**: 15 seconds
- **Headers**: JSON content type

### Environment Variables
Create a `.env` file in the frontend directory to customize API URL:
```
REACT_APP_API_URL=http://your-custom-ip:8000
```

## 🐛 Troubleshooting

### Common Issues

**1. Port 8000 already in use**
```bash
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**2. Cannot connect to API server**
- Ensure backend is running: `python backend/app.py`
- Check health endpoint: http://localhost:8000/health
- Verify firewall settings if accessing from network

**3. Frontend won't start**
```bash
# Clear npm cache and reinstall
cd frontend
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

**4. Database errors**
```bash
# Reset database
cd backend
python init_db.py
```

## 🏃‍♂️ Development

### Backend Development
```bash
cd backend
python app.py
# API docs available at: http://localhost:8000/docs
```

### Frontend Development
```bash
cd frontend
npm start
# App available at: http://localhost:3000
```

### Database Management
The SQLite database (`backend/data.db`) contains sample data with:
- **customers** table: Customer information
- **orders** table: Order records

To reset or modify the database:
```bash
cd backend
python init_db.py
```

## 📚 Documentation

- [Integration Setup Guide](docs/INTEGRATION_SETUP.md) - Detailed setup instructions
- [API Documentation](http://localhost:8000/docs) - FastAPI auto-generated docs (when server is running)

## 🚀 Deployment Notes

### Local Network Access
- Backend binds to `0.0.0.0:8000` for network accessibility
- Frontend configured to connect via local IP address
- Use batch files for easy startup on Windows

### Production Considerations
- Set proper environment variables
- Configure HTTPS for secure communication
- Use proper database for production (PostgreSQL, MySQL)
- Set up proper CORS policies
- Consider using Docker for containerization


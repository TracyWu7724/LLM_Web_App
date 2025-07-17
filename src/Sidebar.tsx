import React from "react";
import { useNavigate } from "react-router-dom";

const Sidebar: React.FC = () => {
  const navigate = useNavigate();

  const handleQueryClick = (query: string) => {
    navigate(`/chat?query=${encodeURIComponent(query)}`);
  };

  const frequentQueries = [
    "Show me all employee records",
    "What is the total spending by department?",
    "How many requests were made by each originator?",
    "Show me all completed requests"
  ];

  const recentQueries = [
    "Show me Q3 2023 employee requests",
    "What is the average spending by category?",
    "Show me all high value requests above $50,000",
    "What is the status breakdown of all requests?"
  ];

  return (
    <aside className="w-64 bg-gray-100 p-8 flex flex-col space-y-6 text-gray-700 min-h-screen">
      {/* Logo */}
      <div className="flex items-center space-x-2">
        <img 
          src="/Skyworks_logo.PNG" 
          alt="Skyworks Logo" 
          className="h-13 w-auto"
        />
      </div>

      {/* Main Navigation */}
      <nav className="flex flex-col space-y-8">
        <div className="space-y-2">
          <button 
            onClick={() => navigate('/')}
            className="flex items-center space-x-3 hover:text-gray-900 transition-colors w-full text-left"
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
            </svg>
            <span> New Data Query</span>
          </button>
        </div>
        
        {/* Frequently Searched */}
        <div className="space-y-2">
          <div className="flex items-center space-x-3">
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
            </svg>
            <span>Frequently Searched</span>
          </div>
          {frequentQueries.map((query, index) => (
            <button
              key={index}
              onClick={() => handleQueryClick(query)}
              className="block hover:text-gray-900 hover:bg-gray-200 transition-colors text-sm pl-9 py-1 rounded w-full text-left"
            >
              {query.length > 35 ? `${query.substring(0, 35)}...` : query}
            </button>
          ))}
        </div>
        
        {/* Recent Queries */}
        <div className="space-y-2">
          <div className="flex items-center space-x-3">
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
              <path fillRule="evenodd" d="M4 5a2 2 0 012-2v1a1 1 0 001 1h6a1 1 0 001-1V3a2 2 0 012 2v10a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
            </svg>
            <span>Recent Queries</span>
          </div>
          {recentQueries.map((query, index) => (
            <button
              key={index}
              onClick={() => handleQueryClick(query)}
              className="block hover:text-gray-900 hover:bg-gray-200 transition-colors text-sm pl-9 py-1 rounded w-full text-left"
            >
              {query.length > 35 ? `${query.substring(0, 35)}...` : query}
            </button>
          ))}
        </div>
      </nav>
    </aside>
  );
};

export default Sidebar; 
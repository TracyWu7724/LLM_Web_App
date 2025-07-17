import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const SearchBar: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setIsLoading(true);
      console.log("Navigating to chat with query:", searchQuery);
      
      // Navigate to chat page with the query as a URL parameter
      navigate(`/chat?query=${encodeURIComponent(searchQuery)}`);
      
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSearch(e as any);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center mb-12 py-8 relative w-full max-w-6xl">
      <form onSubmit={handleSearch} className="w-full">
        {/* Advanced Search Bar with Gradient Glow Effect - EXTRA LONG */}
        <div 
          className="relative mx-auto max-w-5xl"
          style={{
            filter: 'drop-shadow(0 10px 20px rgba(17, 61, 115, 0.1))',
          }}
        >
          <div 
            className="relative bg-white rounded-2xl border-4 overflow-hidden transition-all duration-300 hover:scale-[1.02] transform"
            style={{ 
              borderColor: 'rgba(17, 61, 115, 0.2)',
              background: 'linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,250,255,0.95) 100%)',
              backdropFilter: 'blur(10px)',
              boxShadow: '0 20px 40px rgba(17, 61, 115, 0.1), 0 1px 3px rgba(17, 61, 115, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.6)'
            }}
          >
            
            <div className="flex items-center px-10 py-3 gap-4">
              {/* Command Icon */}
              <div className="flex-shrink-0">
                <svg className="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              
              {/* Search Input - LONG & NARROW */}
              <textarea
                className="flex-1 bg-transparent border-0 focus:ring-0 focus:outline-none text-lg placeholder:text-gray-400 resize-none min-h-[50px] py-3 leading-relaxed w-full"
                placeholder="Enter your text for data query..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                style={{ fontFamily: 'inherit', minWidth: '0' }}
              />
              
              {/* Execute Button - COMPACT */}
              <button 
                type="submit"
                disabled={isLoading || !searchQuery.trim()}
                className="inline-flex items-center gap-2 px-6 py-3 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium text-base shadow-xl hover:shadow-2xl flex-shrink-0"
                style={{ 
                  backgroundColor: '#113D73',
                }}
                onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#0e3560'}
                onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#113D73'}
              >
                {isLoading ? (
                  <svg className="w-6 h-6 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                )}
                Execute
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default SearchBar; 
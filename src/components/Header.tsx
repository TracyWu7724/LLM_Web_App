import React, { useState } from "react";

const Header: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <div className="flex items-center justify-center mb-8 relative">
      {/* Navigation Arrows - positioned absolutely on the left */}
      <div className="absolute left-0 flex items-center space-x-4">
        {/* ... arrows ... */}
      </div>

      {/* Search Bar - centered */}
      <div className="max-w-md w-full">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            placeholder="What do you want to listen to?"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="block w-full pl-10 pr-3 py-2 border border-transparent rounded-md leading-5 bg-white bg-opacity-10 text-white placeholder-gray-400 focus:outline-none focus:bg-opacity-20 focus:border-white transition-all"
          />
        </div>
      </div>

      {/* User Actions - positioned absolutely on the right */}
      <div className="absolute right-0 flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <img 
            src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=32&h=32&fit=crop&crop=face" 
            alt="User" 
            className="w-8 h-8 rounded-full object-cover" 
          />
          <span className="text-sm font-medium text-white">John Doe</span>
          <button className="text-gray-400 hover:text-white">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default Header; 
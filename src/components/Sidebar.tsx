import React from "react";

const Sidebar: React.FC = () => (
  <aside className="w-64 bg-gray-100 p-6 flex flex-col space-y-6 text-gray-700 min-h-screen">
    {/* Logo */}
    <div className="flex items-center space-x-2">
      <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
        <span className="text-black font-bold text-lg">S</span>
      </div>
      <span className="text-gray-900 font-bold text-xl">Spotify</span>
    </div>

    {/* Main Navigation */}
    <nav className="flex flex-col space-y-4">
      <div className="space-y-2">
        <a href="#" className="flex items-center space-x-3 hover:text-gray-900 transition-colors">
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
          </svg>
          <span>Data Qurey</span>
        </a>
      </div>

      {/* Playlists */}
      <div className="space-y-2">
        <div className="flex items-center space-x-3">
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
            <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
            <path fillRule="evenodd" d="M4 5a2 2 0 012-2v1a1 1 0 001 1h6a1 1 0 001-1V3a2 2 0 012 2v10a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
          </svg>
          <span>History</span>
        </div>
        <a href="#" className="block hover:text-gray-900 transition-colors text-sm">Discover Weekly</a>
        <a href="#" className="block hover:text-gray-900 transition-colors text-sm">Release Radar</a>
        <a href="#" className="block hover:text-gray-900 transition-colors text-sm">Liked Songs</a>
        <a href="#" className="block hover:text-gray-900 transition-colors text-sm">Decade</a>
        <a href="#" className="block hover:text-gray-900 transition-colors text-sm">Sylvan Esso</a>
        <a href="#" className="block hover:text-gray-900 transition-colors text-sm">Chill Vibes</a>
        <a href="#" className="block hover:text-gray-900 transition-colors text-sm">Workout Mix</a>
      </div>
    </nav>



  </aside>
);

export default Sidebar; 
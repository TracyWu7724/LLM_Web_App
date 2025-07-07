import React, { useState } from "react";

interface Props {
  title: string;
  artists: string;
  color: string;
}

const DailyMixCard: React.FC<Props> = ({ title, artists, color }) => {
  const [isHovered, setIsHovered] = useState(false);

  // Generate a gradient based on the color prop
  const getGradient = (color: string) => {
    const gradients = {
      "bg-pink-100": "from-pink-400 to-purple-500",
      "bg-blue-100": "from-blue-400 to-cyan-500",
      "bg-pink-300": "from-pink-500 to-red-500",
      "bg-green-200": "from-green-400 to-emerald-500",
      "bg-blue-200": "from-blue-500 to-indigo-500",
      "bg-lime-200": "from-lime-400 to-green-500"
    };
    return gradients[color as keyof typeof gradients] || "from-gray-400 to-gray-600";
  };

  return (
    <div 
      className={`group relative p-4 rounded-lg cursor-pointer transition-all duration-300 hover:scale-105 hover:shadow-2xl ${color} text-black`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Album Artwork */}
      <div className="relative mb-4">
        <div className={`w-full h-32 rounded-md bg-gradient-to-br ${getGradient(color)} flex items-center justify-center shadow-lg`}>
          <div className="text-white text-4xl font-bold opacity-80">
            {title.split(' ').map(word => word[0]).join('')}
          </div>
        </div>
        
        {/* Play Button Overlay */}
        <div className={`absolute inset-0 flex items-center justify-center transition-opacity duration-300 ${
          isHovered ? 'opacity-100' : 'opacity-0'
        }`}>
          <button className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition-transform">
            <svg className="w-6 h-6 text-white ml-1" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-2">
        <h3 className="font-bold text-lg truncate">{title}</h3>
        <p className="text-sm text-gray-700 line-clamp-2">{artists} and more</p>
      </div>

      {/* Hover Effects */}
      {isHovered && (
        <div className="absolute inset-0 bg-black bg-opacity-10 rounded-lg pointer-events-none" />
      )}
    </div>
  );
};

export default DailyMixCard; 
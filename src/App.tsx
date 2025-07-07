import React from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import DailyMixCard from "./components/DailyMixCard";
import Player from "./components/Player";

const mixes = [
  { id: 1, title: "Daily Mix 1", artists: "Massive Attack, Underworld, Jon Hopkins", color: "bg-pink-100" },
  { id: 2, title: "Daily Mix 2", artists: "Drive-By Truckers, Lambchop, Jason Isbell", color: "bg-blue-100" },
  { id: 3, title: "Daily Mix 3", artists: "Deerhunter, The Brian Jonestown Massacre", color: "bg-pink-300" },
  { id: 4, title: "Daily Mix 4", artists: "Grizzly Bear, The National, My Morning Jacket", color: "bg-green-200" },
  { id: 5, title: "Daily Mix 5", artists: "The Cult, Morphine, The Smashing Pumpkins", color: "bg-blue-200" },
  { id: 6, title: "Daily Mix 6", artists: "The Smiths, New Order, Joy Division", color: "bg-lime-200" }
];

const recentlyPlayed = [
  { id: 1, title: "Release Radar", artists: "New releases from artists you follow", image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&h=200&fit=crop" },
  { id: 2, title: "Discover Weekly", artists: "Your weekly mixtape of fresh music", image: "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=200&h=200&fit=crop" },
  { id: 3, title: "Chill Vibes", artists: "Relaxing tunes for your downtime", image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&h=200&fit=crop" },
  { id: 4, title: "Workout Mix", artists: "High energy tracks to keep you moving", image: "https://images.unsplash.com/photo-1511379938547-c1f69419868d?w=200&h=200&fit=crop" }
];

const topArtists = [
  { id: 1, name: "The Weeknd", image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&h=200&fit=crop&crop=face" },
  { id: 2, name: "Dua Lipa", image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&h=200&fit=crop&crop=face" },
  { id: 3, name: "Drake", image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&h=200&fit=crop&crop=face" },
  { id: 4, name: "Taylor Swift", image: "https://images.unsplash.com/photo-1493225457124-a3eb161ffa5f?w=200&h=200&fit=crop&crop=face" }
];

const PlaylistCard: React.FC<{ title: string; artists: string; image: string }> = ({ title, artists, image }) => (
  <div className="group relative p-4 rounded-lg cursor-pointer transition-all duration-300 hover:scale-105 hover:bg-white hover:bg-opacity-10">
    <div className="relative mb-4">
      <img src={image} alt={title} className="w-full h-32 object-cover rounded-md shadow-lg" />
      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <button className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition-transform">
          <svg className="w-6 h-6 text-white ml-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
    <div className="space-y-1">
      <h3 className="font-semibold text-white truncate">{title}</h3>
      <p className="text-sm text-gray-400 line-clamp-2">{artists}</p>
    </div>
  </div>
);

const ArtistCard: React.FC<{ name: string; image: string }> = ({ name, image }) => (
  <div className="group relative p-4 rounded-lg cursor-pointer transition-all duration-300 hover:scale-105 hover:bg-white hover:bg-opacity-10">
    <div className="relative mb-4">
      <img src={image} alt={name} className="w-full h-32 object-cover rounded-full shadow-lg" />
      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <button className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition-transform">
          <svg className="w-6 h-6 text-white ml-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
    <div className="text-center">
      <h3 className="font-semibold text-white truncate">{name}</h3>
      <p className="text-sm text-gray-400">Artist</p>
    </div>
  </div>
);

const App: React.FC = () => (
  <div className="flex h-screen bg-white text-gray-900 overflow-hidden">
    <Sidebar />
    <div className="flex-1 flex flex-col justify-between overflow-hidden">
      <div className="flex-1 overflow-y-auto">
        <div className="p-6">
          <Header />
          
          {/* Welcome Section */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold mb-2 text-gray-900">Good afternoon</h1>
            <p className="text-gray-600">Welcome back to your music</p>
          </div>

          {/* Recently Played */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold mb-4 text-gray-900">Recently played</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {recentlyPlayed.map((playlist) => (
                <PlaylistCard key={playlist.id} {...playlist} />
              ))}
            </div>
          </section>

          {/* Daily Mixes */}
          <section className="mb-8">
            <h2 className="text-2xl font-bold mb-4 text-gray-900">Your Daily Mixes</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {mixes.map((mix) => (
                <DailyMixCard key={mix.id} {...mix} />
              ))}
            </div>
          </section>

        </div>
      </div>
    </div>
  </div>
);

export default App; 
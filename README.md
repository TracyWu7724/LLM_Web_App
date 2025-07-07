# Web-App-React

# Spotify Frontend Clone

A modern, responsive Spotify-like music player interface built with React, TypeScript, and Tailwind CSS.

## Features

### 🎵 Music Player Interface
- **Interactive Player Controls**: Play/pause, skip, shuffle, repeat functionality
- **Volume Control**: Adjustable volume slider with visual feedback
- **Progress Bar**: Clickable progress bar with time display
- **Now Playing**: Current track information with album artwork

### 🎨 Modern UI/UX
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices
- **Smooth Animations**: Hover effects, transitions, and micro-interactions
- **Spotify-like Styling**: Authentic color scheme and design patterns
- **Custom Scrollbars**: Styled scrollbars for better visual consistency

### 📱 Navigation & Content
- **Sidebar Navigation**: Home, Search, Library, and playlist navigation
- **Search Functionality**: Interactive search bar with placeholder text
- **Content Sections**: 
  - Recently played playlists
  - Daily mixes with custom gradients
  - Top artists showcase
  - Featured playlists
- **User Profile**: User avatar and account information

### 🎯 Interactive Elements
- **Hover Effects**: Cards scale and show play buttons on hover
- **Click Handlers**: Interactive buttons and controls
- **State Management**: Local state for player controls and UI interactions
- **Responsive Grid**: Adaptive grid layouts for different screen sizes

## Tech Stack

- **React 19.1.0** - Modern React with latest features
- **TypeScript 4.9.5** - Type-safe development
- **Tailwind CSS 4.1.11** - Utility-first CSS framework
- **React Scripts 5.0.1** - Create React App build tools

## Getting Started

### Prerequisites
- Node.js (version 14 or higher)
- npm or yarn package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd spotify-frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

4. Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

### Available Scripts

- `npm start` - Runs the app in development mode
- `npm run build` - Builds the app for production
- `npm test` - Launches the test runner
- `npm run eject` - Ejects from Create React App (not recommended)

## Project Structure

```
spotify-frontend/
├── public/
│   └── index.html          # Main HTML template
├── src/
│   ├── components/
│   │   ├── DailyMixCard.tsx    # Daily mix playlist cards
│   │   ├── Header.tsx          # Top navigation and search
│   │   ├── Player.tsx          # Music player controls
│   │   └── Sidebar.tsx         # Left navigation sidebar
│   ├── App.tsx                 # Main application component
│   ├── index.tsx               # Application entry point
│   └── index.css               # Global styles and Tailwind imports
├── package.json                # Dependencies and scripts
├── tailwind.config.js          # Tailwind CSS configuration
└── README.md                   # Project documentation
```

## Component Details

### Sidebar (`Sidebar.tsx`)
- Spotify logo and branding
- Main navigation (Home, Search, Library)
- Playlist section with user playlists
- User profile section with avatar and account info
- Install app button

### Header (`Header.tsx`)
- Navigation arrows (back/forward)
- Search bar with icon and placeholder
- User actions (notifications, help)
- User profile display

### Player (`Player.tsx`)
- Current track information with album artwork
- Playback controls (play/pause, skip, shuffle, repeat)
- Progress bar with time display
- Volume control slider
- Interactive buttons with hover states

### DailyMixCard (`DailyMixCard.tsx`)
- Gradient album artwork based on color prop
- Hover effects with play button overlay
- Track and artist information
- Smooth transitions and animations

### App (`App.tsx`)
- Main layout with sidebar and content area
- Multiple content sections (recently played, daily mixes, top artists)
- Responsive grid layouts
- Custom card components for playlists and artists

## Styling

The project uses Tailwind CSS for styling with:
- Custom color palette matching Spotify's brand
- Responsive design utilities
- Custom animations and transitions
- Utility classes for layout and spacing

### Custom CSS Features
- Line clamping for text truncation
- Custom scrollbar styling
- Smooth transitions for all interactive elements
- Hover effects and micro-interactions

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is for educational purposes and is not affiliated with Spotify.

## Acknowledgments

- Design inspired by Spotify's web interface
- Icons from Heroicons
- Images from Unsplash
- Built with Create React App and Tailwind CSS 

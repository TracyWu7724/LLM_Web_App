import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import Sidebar from "./Sidebar";
import SearchBar from "./SearchBar";

const Home: React.FC = () => {
  const [hasOutput, setHasOutput] = useState(false);

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div className="flex h-screen bg-white text-gray-900 overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex items-start justify-center pt-48">
        <div className="flex flex-col items-center space-y-8 max-w-7xl w-full px-4">
          {/* Title Section */}
          <div className="text-center space-y-4">
            <AnimatePresence>
              {!hasOutput && (
                <>
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="shimmer inline-block px-4 py-1.5 mb-6 text-sm md:text-base font-medium tracking-wider border-[3px] rounded-full shadow-glow"
                    style={{ 
                      borderColor: 'rgba(17, 61, 115, 0.2)', 
                      backgroundColor: 'rgba(17, 61, 115, 0.05)' 
                    }}
                  >
                    <svg className="w-4 h-4 inline mr-2" fill="#3070A6" viewBox="0 0 24 24">
                      <path d="M12 2L15.09 8.26L22 9L17 14L18.18 21L12 17.77L5.82 21L7 14L2 9L8.91 8.26L12 2Z"/>
                    </svg>
                    AI Powered
                  </motion.span>
                  <motion.h1
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-2xl md:text-4xl lg:text-5xl font-bold mb-4 md:mb-6 tracking-tight text-gray-900" style={{ color: '#113D73' }}
                  >
                    DAS TAM Eng Ops Data Analytics and Insights
                    
                  </motion.h1>
                  <motion.p 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    variants={itemVariants}
                    className="text-base md:text-lg text-gray-600 mb-8 md:mb-10 max-w-2xl mx-auto"
                  >
                    
                  </motion.p>
                </>
              )}
            </AnimatePresence>
          </div>
          
          {/* Search Bar */}
          <SearchBar />
        </div>
      </div>
    </div>
  );
};

export default Home; 
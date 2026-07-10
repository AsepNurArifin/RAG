"use client";

import { motion } from "framer-motion";

export function LoadingIndicator() {
  return (
    <div className="flex items-start space-x-4 max-w-[80%] my-4">
      {/* Avatar Placeholder */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[#0077ff] flex items-center justify-center shadow-sm">
        <div className="w-4 h-4 bg-[#e6f0fa]/20 rounded-full animate-pulse" />
      </div>
      
      {/* Loading Bubble */}
      <div className="flex flex-col">
        <div className="flex items-center space-x-2 mb-1">
          <span className="text-xs font-semibold text-slate-600">EnterpriseMind AI</span>
          <span className="text-[10px] text-slate-400">Sedang memproses...</span>
        </div>
        
        <div className="relative p-4 rounded-2xl rounded-tl-sm bg-[#e6f0fa] border border-slate-200 text-slate-800 shadow-sm overflow-hidden min-w-[120px]">
          {/* Animated gradient background for sleek effect */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-[#0077ff]/5 to-transparent -translate-x-full animate-[shimmer_2s_infinite]" />
          
          <div className="flex space-x-1.5 items-center justify-center h-4">
            <motion.div 
              animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
              transition={{ repeat: Infinity, duration: 1.2, delay: 0 }}
              className="w-1.5 h-1.5 bg-[#0077ff] rounded-full"
            />
            <motion.div 
              animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
              transition={{ repeat: Infinity, duration: 1.2, delay: 0.2 }}
              className="w-1.5 h-1.5 bg-[#0077ff] rounded-full"
            />
            <motion.div 
              animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
              transition={{ repeat: Infinity, duration: 1.2, delay: 0.4 }}
              className="w-1.5 h-1.5 bg-[#0077ff] rounded-full"
            />
          </div>
        </div>
      </div>
    </div>
  );
}

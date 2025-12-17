"use client";

import React from "react";
import { Calculator } from "lucide-react";

export default function Header() {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          {/* Logo and Title */}
          <div className="flex items-center gap-2">
            <div className="bg-[#FF5F1F] text-white p-2 rounded">
              <Calculator className="h-5 w-5" />
            </div>
            <div className="flex flex-col">
              <h1 className="text-xl font-bold text-gray-900">Lakemeter</h1>
              <span className="text-xs text-gray-500 uppercase tracking-wide">Pricing Calculator</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

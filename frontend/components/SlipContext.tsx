"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export interface SlipLeg {
  match_id: number;
  fixture: string;
  market: string;
  selection: string;
  odds: number;
  probability: number;
}

interface SlipContextType {
  legs: SlipLeg[];
  addLeg: (leg: SlipLeg) => void;
  removeLeg: (match_id: number, market: string, selection: string) => void;
  clearSlip: () => void;
  combinedOdds: number;
  jointProbability: number;
  bookingCode: string | null;
  generateBookingCode: () => Promise<string>;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

const SlipContext = createContext<SlipContextType | undefined>(undefined);

export function SlipProvider({ children }: { children: React.ReactNode }) {
  const [legs, setLegs] = useState<SlipLeg[]>([]);
  const [bookingCode, setBookingCode] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("bet_slip_legs");
      if (saved) setLegs(JSON.parse(saved));
    } catch (e) {}
  }, []);

  // Save to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("bet_slip_legs", JSON.stringify(legs));
    } catch (e) {}
  }, [legs]);

  const addLeg = (leg: SlipLeg) => {
    setLegs((prev) => {
      // Disallow exact duplicate selection
      const exists = prev.some(
        (l) => l.match_id === leg.match_id && l.market === leg.market && l.selection === leg.selection
      );
      if (exists) return prev;
      // Replace only if same match AND same market type (allow mixing different markets like Goals + Corners from same game!)
      const filtered = prev.filter(
        (l) => !(l.match_id === leg.match_id && l.market === leg.market)
      );
      return [...filtered, leg];
    });
    setBookingCode(null);
    setIsOpen(true);
  };

  const removeLeg = (match_id: number, market: string, selection: string) => {
    setLegs((prev) =>
      prev.filter((l) => !(l.match_id === match_id && l.market === market && l.selection === selection))
    );
    setBookingCode(null);
  };

  const clearSlip = () => {
    setLegs([]);
    setBookingCode(null);
  };

  const combinedOdds = Number(
    legs.reduce((acc, leg) => acc * Math.max(leg.odds, 1.01), 1.0).toFixed(2)
  );

  const jointProbability = Number(
    legs.reduce((acc, leg) => acc * Math.max(leg.probability, 0.05), 1.0).toFixed(4)
  );

  const generateBookingCode = async (): Promise<string> => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/v1/accumulators/custom", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slip_name: "Custom Slip",
          legs,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setBookingCode(data.booking_code);
        return data.booking_code;
      }
    } catch (e) {}
    // Client-side fallback code
    const rand = Math.random().toString(36).substring(2, 8).toUpperCase();
    const code = `SB-${rand}`;
    setBookingCode(code);
    return code;
  };

  return (
    <SlipContext.Provider
      value={{
        legs,
        addLeg,
        removeLeg,
        clearSlip,
        combinedOdds,
        jointProbability,
        bookingCode,
        generateBookingCode,
        isOpen,
        setIsOpen,
      }}
    >
      {children}
    </SlipContext.Provider>
  );
}

export function useSlip() {
  const context = useContext(SlipContext);
  if (!context) {
    throw new Error("useSlip must be used within a SlipProvider");
  }
  return context;
}

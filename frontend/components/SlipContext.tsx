"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export interface SlipLeg {
  match_id: number;
  fixture: string;
  market: string;
  selection: string;
  odds: number;
  probability: number;
  event_id?: string;
  market_id?: string;
  outcome_id?: string;
  specifier?: string;
  kickoff?: string;
}

interface SlipContextType {
  legs: SlipLeg[];
  addLeg: (leg: SlipLeg) => void;
  removeLeg: (match_id: number, market: string, selection: string) => void;
  clearSlip: () => void;
  combinedOdds: number;
  jointProbability: number;
  bookingCode: string | null;
  shareUrl: string | null;
  isOfficialSporty: boolean;
  bookingError: string | null;
  generateBookingCode: () => Promise<string | null>;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

const SlipContext = createContext<SlipContextType | undefined>(undefined);

export function SlipProvider({ children }: { children: React.ReactNode }) {
  const [legs, setLegs] = useState<SlipLeg[]>([]);
  const [bookingCode, setBookingCode] = useState<string | null>(null);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [isOfficialSporty, setIsOfficialSporty] = useState(false);
  const [bookingError, setBookingError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("bet_slip_legs");
      if (saved) {
        const parsed = JSON.parse(saved) as SlipLeg[];
        // Previous live picks used invented prices, so never restore them into a bet slip.
        const current = parsed.filter((leg) => !/^(live\s|next goal)/i.test(leg.market));
        setLegs(current);
        if (current.length !== parsed.length) {
          localStorage.setItem("bet_slip_legs", JSON.stringify(current));
        }
      }
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
      if (exists) {
        return prev.map((current) =>
          current.match_id === leg.match_id &&
          current.market === leg.market &&
          current.selection === leg.selection
            ? { ...current, ...leg }
            : current
        );
      }
      // Replace only if same match AND same market type
      const filtered = prev.filter(
        (l) => !(l.match_id === leg.match_id && l.market === leg.market)
      );
      return [...filtered, leg];
    });
    setBookingCode(null);
    setShareUrl(null);
    setBookingError(null);
    setIsOpen(true);
  };

  const removeLeg = (match_id: number, market: string, selection: string) => {
    setLegs((prev) =>
      prev.filter((l) => !(l.match_id === match_id && l.market === market && l.selection === selection))
    );
    setBookingCode(null);
    setShareUrl(null);
    setBookingError(null);
  };

  const clearSlip = () => {
    setLegs([]);
    setBookingCode(null);
    setShareUrl(null);
    setBookingError(null);
  };

  const combinedOdds = Number(
    legs.reduce((acc, leg) => acc * Math.max(leg.odds, 1.01), 1.0).toFixed(2)
  );

  const jointProbability = Number(
    legs.reduce((acc, leg) => acc * Math.max(leg.probability, 0.05), 1.0).toFixed(4)
  );

  const generateBookingCode = async (): Promise<string | null> => {
    setBookingError(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/v1/accumulators/custom`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slip_name: "SportyBet Custom Slip",
          legs,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (!data.booking_code || !data.is_official_sporty) {
          throw new Error("SportyBet did not return an official booking code.");
        }
        setBookingCode(data.booking_code);
        setShareUrl(data.share_url || `https://www.sportybet.com/ng/?shareCode=${data.booking_code}`);
        setIsOfficialSporty(data.is_official_sporty ?? true);
        if (Array.isArray(data.legs)) setLegs(data.legs);
        return data.booking_code;
      }
      const errorData = await res.json().catch(() => null);
      throw new Error(errorData?.detail || `Booking request failed (${res.status}).`);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Could not reach the booking service.";
      setBookingError(message);
      return null;
    }
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
        shareUrl,
        isOfficialSporty,
        bookingError,
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

"use client";

import { motion } from "framer-motion";
import type { FocusCategory } from "@/lib/api";

interface FocusSelectorProps {
  selected: FocusCategory | null;
  onSelect: (focus: FocusCategory | null) => void;
  disabled?: boolean;
}

const FOCUS_OPTIONS: { key: FocusCategory | null; label: string }[] = [
  { key: null, label: "Ausgewogen" },
  { key: "timbre", label: "Klangfarbe" },
  { key: "harmony", label: "Harmonie" },
  { key: "rhythm", label: "Rhythmus" },
  { key: "brightness", label: "Helligkeit" },
  { key: "intensity", label: "Intensität" },
];

export default function FocusSelector({ selected, onSelect, disabled }: FocusSelectorProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <span className="self-center text-[10px] text-text-tertiary mr-1">Fokus:</span>
      {FOCUS_OPTIONS.map(({ key, label }) => {
        const isActive = selected === key;
        return (
          <button
            key={label}
            onClick={() => onSelect(key)}
            disabled={disabled}
            className={`relative rounded-full px-3 py-1 text-[11px] font-medium transition-colors disabled:opacity-50 ${
              isActive
                ? "text-amber-light"
                : "text-text-secondary hover:text-text-primary hover:bg-surface-elevated"
            }`}
          >
            {isActive && (
              <motion.span
                layoutId="focus-pill"
                className="absolute inset-0 rounded-full bg-amber/15 border border-amber/30"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative">{label}</span>
          </button>
        );
      })}
    </div>
  );
}

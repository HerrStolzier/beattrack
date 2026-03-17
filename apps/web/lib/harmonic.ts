/**
 * Camelot Wheel mapping and harmonic compatibility logic for DJ mixing.
 */

// Standard musical key → Camelot code mapping
const KEY_TO_CAMELOT: Record<string, string> = {
  "A-flat major": "4B", "G# major": "4B",
  "E-flat major": "5B", "D# major": "5B",
  "B-flat major": "6B", "A# major": "6B",
  "F major": "7B",
  "C major": "8B",
  "G major": "9B",
  "D major": "10B",
  "A major": "11B",
  "E major": "12B",
  "B major": "1B",
  "F# major": "2B", "G-flat major": "2B",
  "D-flat major": "3B", "C# major": "3B",
  // Minor keys
  "F minor": "4A",
  "C minor": "5A",
  "G minor": "6A",
  "D minor": "7A",
  "A minor": "8A",
  "E minor": "9A",
  "B minor": "10A",
  "F# minor": "11A", "G-flat minor": "11A",
  "C# minor": "12A", "D-flat minor": "12A",
  "G# minor": "1A", "A-flat minor": "1A",
  "D# minor": "2A", "E-flat minor": "2A",
  "A# minor": "3A", "B-flat minor": "3A",
};

export function toCamelot(musicalKey: string | null | undefined): string | null {
  if (!musicalKey) return null;
  return KEY_TO_CAMELOT[musicalKey] ?? null;
}

function parseCamelot(code: string): { num: number; letter: "A" | "B" } | null {
  const match = code.match(/^(\d{1,2})([AB])$/);
  if (!match) return null;
  const num = parseInt(match[1], 10);
  if (num < 1 || num > 12) return null;
  return { num, letter: match[2] as "A" | "B" };
}

export type HarmonicCompat = "perfect" | "compatible" | "incompatible";

/**
 * Determine harmonic compatibility between two Camelot codes.
 * - perfect: same code, or ±1 on the wheel (same letter)
 * - compatible: same number (A↔B switch), or ±2 on the wheel
 * - incompatible: everything else
 */
export function getHarmonicCompatibility(
  keyA: string | null | undefined,
  keyB: string | null | undefined,
): HarmonicCompat | null {
  const camelotA = toCamelot(keyA);
  const camelotB = toCamelot(keyB);
  if (!camelotA || !camelotB) return null;

  const a = parseCamelot(camelotA);
  const b = parseCamelot(camelotB);
  if (!a || !b) return null;

  // Same code
  if (a.num === b.num && a.letter === b.letter) return "perfect";

  // Circular distance on the wheel (1-12)
  const dist = Math.min(
    Math.abs(a.num - b.num),
    12 - Math.abs(a.num - b.num),
  );

  // Same letter, ±1 step
  if (a.letter === b.letter && dist === 1) return "perfect";

  // Same number, different letter (major↔minor)
  if (a.num === b.num && a.letter !== b.letter) return "compatible";

  // Same letter, ±2 steps
  if (a.letter === b.letter && dist === 2) return "compatible";

  return "incompatible";
}

export type BpmMatch = "exact" | "close" | "far";

export function getBpmMatch(bpmA: number | null | undefined, bpmB: number | null | undefined): BpmMatch | null {
  if (bpmA == null || bpmB == null || bpmA === 0 || bpmB === 0) return null;
  const ratio = Math.abs(bpmA - bpmB) / Math.max(bpmA, bpmB);
  if (ratio <= 0.02) return "exact";
  if (ratio <= 0.05) return "close";
  return "far";
}

export function getBpmDiff(bpmA: number | null | undefined, bpmB: number | null | undefined): number | null {
  if (bpmA == null || bpmB == null) return null;
  return Math.round(bpmB - bpmA);
}

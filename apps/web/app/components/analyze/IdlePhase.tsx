"use client";

import { motion } from "framer-motion";
import UrlInput from "../UrlInput";
import UploadZone from "../UploadZone";
import SessionHistory from "./SessionHistory";
import type { IdentifyResponse } from "@/lib/api";
import type { AnalyzePhase } from "@/app/hooks/useAnalyzeState";
import type { HistoryEntry } from "@/app/hooks/useSessionHistory";

interface IdlePhaseProps {
  onMatch: (result: IdentifyResponse) => void;
  onFileSelected: (file: File) => Promise<void>;
  setPhase: (phase: AnalyzePhase) => void;
  history: HistoryEntry[];
  onClearHistory: () => void;
}

export default function IdlePhase({ onMatch, onFileSelected, setPhase, history, onClearHistory }: IdlePhaseProps) {
  return (
    <>
      <UrlInput onMatch={onMatch} />
      <div className="flex items-center gap-3 my-6">
        <div className="h-px flex-1 bg-gradient-to-r from-transparent to-border-subtle" />
        <span className="text-xs text-text-tertiary font-medium">oder</span>
        <div className="h-px flex-1 bg-gradient-to-l from-transparent to-border-subtle" />
      </div>
      <UploadZone onFileSelected={onFileSelected} />

      {/* Blend + Vibe buttons */}
      <div className="flex items-center gap-3 mt-6">
        <div className="h-px flex-1 bg-gradient-to-r from-transparent to-border-subtle" />
        <span className="text-xs text-text-tertiary font-medium">oder</span>
        <div className="h-px flex-1 bg-gradient-to-l from-transparent to-border-subtle" />
      </div>
      <div className="flex gap-2 mt-4">
        <motion.button
          onClick={() => setPhase("blend")}
          className="relative flex-1 overflow-hidden glass rounded-xl px-4 py-3 text-sm font-medium text-text-secondary"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          transition={{ type: "spring", stiffness: 400, damping: 25 }}
          style={{ originX: 0.5, originY: 0.5 }}
        >
          {/* Hover glow overlay */}
          <motion.div
            className="pointer-events-none absolute inset-0 rounded-xl"
            initial={{ opacity: 0 }}
            whileHover={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            style={{
              background: "radial-gradient(ellipse at 50% 100%, rgba(245,158,11,0.12), transparent 70%)",
              boxShadow: "inset 0 0 0 1px rgba(245,158,11,0.25)",
            }}
          />
          {/* Animated indicator dot */}
          <motion.span
            className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-amber/60"
            animate={{ opacity: [0.4, 1, 0.4], scale: [0.8, 1.1, 0.8] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
          />
          <span className="relative block text-text-primary">Sonic Blend</span>
          <span className="relative block text-[10px] text-text-tertiary font-normal mt-0.5">Zwischen zwei Songs</span>
        </motion.button>
        <motion.button
          onClick={() => setPhase("vibe")}
          className="relative flex-1 overflow-hidden glass rounded-xl px-4 py-3 text-sm font-medium text-text-secondary"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          transition={{ type: "spring", stiffness: 400, damping: 25 }}
          style={{ originX: 0.5, originY: 0.5 }}
        >
          {/* Hover glow overlay */}
          <motion.div
            className="pointer-events-none absolute inset-0 rounded-xl"
            initial={{ opacity: 0 }}
            whileHover={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
            style={{
              background: "radial-gradient(ellipse at 50% 100%, rgba(167,139,250,0.12), transparent 70%)",
              boxShadow: "inset 0 0 0 1px rgba(167,139,250,0.2)",
            }}
          />
          {/* Animated indicator dot */}
          <motion.span
            className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-violet/60"
            animate={{ opacity: [0.4, 1, 0.4], scale: [0.8, 1.1, 0.8] }}
            transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
          />
          <span className="relative block text-text-primary">Vibe definieren</span>
          <span className="relative block text-[10px] text-text-tertiary font-normal mt-0.5">2-5 Songs kombinieren</span>
        </motion.button>
      </div>

      {/* Session history — only shown when entries exist */}
      <SessionHistory history={history} onClear={onClearHistory} />
    </>
  );
}

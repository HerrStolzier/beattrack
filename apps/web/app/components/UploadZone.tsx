"use client";

import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const MAX_SIZE_MB = 50;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const ACCEPTED_TYPES = [
  "audio/mpeg",
  "audio/mp3",
  "audio/wav",
  "audio/x-wav",
  "audio/flac",
  "audio/x-flac",
  "audio/ogg",
  "audio/aac",
  "audio/mp4",
  "audio/x-m4a",
];

type UploadZoneProps = {
  onFileSelected: (file: File) => void;
  disabled?: boolean;
};

export default function UploadZone({ onFileSelected, disabled }: UploadZoneProps) {
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRipple, setShowRipple] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSelect = useCallback(
    (file: File) => {
      setError(null);

      if (file.size > MAX_SIZE_BYTES) {
        setError(`Datei zu groß (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum: ${MAX_SIZE_MB} MB.`);
        return;
      }

      if (!ACCEPTED_TYPES.includes(file.type) && !file.name.match(/\.(mp3|wav|flac|ogg|aac|m4a)$/i)) {
        setError("Ungültiges Format. Unterstützt: MP3, WAV, FLAC, OGG, AAC, M4A.");
        return;
      }

      onFileSelected(file);
    },
    [onFileSelected]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (file) {
        // Trigger drop ripple
        setShowRipple(true);
        setTimeout(() => setShowRipple(false), 700);
        validateAndSelect(file);
      }
    },
    [disabled, validateAndSelect]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (!disabled) setDragOver(true);
    },
    [disabled]
  );

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) validateAndSelect(file);
      // Reset input so the same file can be selected again
      e.target.value = "";
    },
    [validateAndSelect]
  );

  return (
    <div>
      <motion.div
        role="button"
        tabIndex={0}
        data-testid="upload-zone"
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !disabled) inputRef.current?.click();
        }}
        className={`
          gradient-border glass-premium relative flex cursor-pointer flex-col items-center justify-center
          overflow-hidden rounded-2xl p-8 sm:p-12 transition-all duration-300
          ${disabled ? "cursor-not-allowed opacity-50" : ""}
        `}
        animate={
          dragOver
            ? {
                boxShadow:
                  "inset 0 0 60px rgba(245, 158, 11, 0.15), 0 0 30px rgba(245, 158, 11, 0.1)",
                scale: 1.02,
              }
            : {
                boxShadow: "none",
                scale: 1,
              }
        }
        transition={{ duration: 0.25 }}
        whileHover={disabled ? {} : { scale: dragOver ? 1.02 : 1.01 }}
        whileTap={disabled ? {} : { scale: 0.99 }}
      >
        {/* Marching-ants SVG border */}
        <svg
          className="pointer-events-none absolute inset-0 h-full w-full"
          xmlns="http://www.w3.org/2000/svg"
          style={{ borderRadius: "1rem" }}
        >
          <rect
            x="2"
            y="2"
            width="calc(100% - 4px)"
            height="calc(100% - 4px)"
            rx="14"
            ry="14"
            fill="none"
            stroke={dragOver ? "rgba(245, 158, 11, 0.7)" : "rgba(255, 255, 255, 0.18)"}
            strokeWidth="1.5"
            strokeDasharray="8 6"
            strokeLinecap="round"
            style={{
              animation: "marching-ants 0.6s linear infinite",
              transition: "stroke 0.3s",
            }}
          />
        </svg>

        {/* Drop ripple overlay */}
        <AnimatePresence>
          {showRipple && (
            <motion.div
              className="pointer-events-none absolute inset-0 flex items-center justify-center"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <motion.div
                className="rounded-full"
                style={{
                  background:
                    "radial-gradient(circle, rgba(245, 158, 11, 0.25) 0%, transparent 70%)",
                  width: 80,
                  height: 80,
                }}
                initial={{ scale: 0, opacity: 1 }}
                animate={{ scale: 6, opacity: 0 }}
                transition={{ duration: 0.65, ease: "easeOut" }}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Floating upload icon */}
        <motion.div
          className="relative z-10 mb-4 rounded-full bg-gradient-to-br from-amber-dim to-violet-dim p-4"
          animate={
            dragOver
              ? { scale: 1.15, rotate: 5 }
              : { scale: 1, rotate: 0, y: [0, -6, 0] }
          }
          transition={
            dragOver
              ? { type: "spring", stiffness: 300, damping: 15 }
              : { duration: 3, repeat: Infinity, ease: "easeInOut" }
          }
        >
          <svg
            className="h-8 w-8 text-amber-light"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
        </motion.div>

        <p className="relative z-10 text-sm font-medium text-text-primary">
          Audio-Datei hierher ziehen oder{" "}
          <span className="text-amber-light underline decoration-amber/50 underline-offset-2">
            durchsuchen
          </span>
        </p>
        <p className="relative z-10 mt-2 text-xs text-text-tertiary">
          MP3, WAV, FLAC, OGG, AAC — max. {MAX_SIZE_MB} MB
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="audio/*"
          className="hidden"
          onChange={handleInputChange}
          disabled={disabled}
          data-testid="upload-input"
        />
      </motion.div>
      {error && (
        <motion.p
          className="mt-2 text-sm text-error"
          role="alert"
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {error}
        </motion.p>
      )}
    </div>
  );
}

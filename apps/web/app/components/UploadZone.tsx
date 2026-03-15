"use client";

import { useCallback, useRef, useState } from "react";
import { motion } from "framer-motion";

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
      if (file) validateAndSelect(file);
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
          gradient-border glass-premium flex cursor-pointer flex-col items-center justify-center
          rounded-2xl border-2 border-dashed p-12 transition-all duration-300
          ${disabled ? "cursor-not-allowed border-border-subtle opacity-50" : ""}
          ${dragOver ? "border-amber/50 glow-multi scale-[1.02]" : "border-border-glass hover:border-amber/30"}
        `}
        whileHover={disabled ? {} : { scale: 1.01 }}
        whileTap={disabled ? {} : { scale: 0.99 }}
      >
        <motion.div
          className="mb-4 rounded-full bg-gradient-to-br from-amber-dim to-violet-dim p-4"
          animate={dragOver ? { scale: 1.15, rotate: 5 } : { scale: 1, rotate: 0 }}
          transition={{ type: "spring", stiffness: 300, damping: 15 }}
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
        <p className="text-sm font-medium text-text-primary">
          Audio-Datei hierher ziehen oder <span className="text-amber-light underline decoration-amber/50 underline-offset-2">durchsuchen</span>
        </p>
        <p className="mt-2 text-xs text-text-tertiary">MP3, WAV, FLAC, OGG, AAC — max. {MAX_SIZE_MB} MB</p>
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
          className="mt-2 text-sm text-red-400"
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

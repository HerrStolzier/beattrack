"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ToastVariant = "info" | "error" | "success";

interface ToastItem {
  id: string;
  message: string;
  variant: ToastVariant;
  visible: boolean;
}

interface ToastContextValue {
  info: (message: string) => void;
  error: (message: string) => void;
  success: (message: string) => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const ToastContext = createContext<ToastContextValue | null>(null);

// ---------------------------------------------------------------------------
// Variant styles
// ---------------------------------------------------------------------------

const variantBorder: Record<ToastVariant, string> = {
  info: "border-l-blue-500",
  error: "border-l-red-500",
  success: "border-l-emerald-500",
};

const variantIcon: Record<ToastVariant, string> = {
  info: "ℹ",
  error: "✕",
  success: "✓",
};

const variantIconColor: Record<ToastVariant, string> = {
  info: "text-blue-400",
  error: "text-red-400",
  success: "text-emerald-400",
};

// ---------------------------------------------------------------------------
// Single Toast component
// ---------------------------------------------------------------------------

interface ToastProps {
  item: ToastItem;
  onClose: (id: string) => void;
}

function Toast({ item, onClose }: ToastProps) {
  return (
    <div
      role="alert"
      className={[
        "flex items-start gap-3 rounded-xl border border-zinc-700 bg-zinc-900 px-4 py-3 shadow-lg",
        "border-l-4",
        variantBorder[item.variant],
        "transition-all duration-300 ease-out",
        item.visible
          ? "translate-y-0 opacity-100"
          : "translate-y-4 opacity-0",
      ].join(" ")}
    >
      <span
        className={`mt-0.5 text-sm font-bold ${variantIconColor[item.variant]}`}
        aria-hidden="true"
      >
        {variantIcon[item.variant]}
      </span>
      <p className="flex-1 text-sm text-zinc-100">{item.message}</p>
      <button
        onClick={() => onClose(item.id)}
        aria-label="Close notification"
        className="ml-1 mt-0.5 text-zinc-500 transition hover:text-zinc-300"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

const MAX_TOASTS = 3;
const AUTO_DISMISS_MS = 5000;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [mounted, setMounted] = useState(false);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    setMounted(true);
    return () => {
      // Clear all timers on unmount
      timers.current.forEach((t) => clearTimeout(t));
    };
  }, []);

  const dismiss = useCallback((id: string) => {
    // Start fade-out transition
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, visible: false } : t))
    );
    // Remove from DOM after transition completes
    const removeTimer = setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
      timers.current.delete(id);
    }, 320);
    timers.current.set(`remove-${id}`, removeTimer);
  }, []);

  const add = useCallback(
    (message: string, variant: ToastVariant) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

      setToasts((prev) => {
        // If at max, mark the oldest for removal
        let next = prev;
        if (prev.length >= MAX_TOASTS) {
          const oldest = prev[0];
          // Trigger removal of oldest (fire-and-forget via dismiss)
          setTimeout(() => dismiss(oldest.id), 0);
          next = prev.slice(1);
        }
        return [...next, { id, message, variant, visible: false }];
      });

      // Trigger slide-in on next frame
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setToasts((prev) =>
            prev.map((t) => (t.id === id ? { ...t, visible: true } : t))
          );
        });
      });

      // Auto-dismiss
      const timer = setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
      timers.current.set(id, timer);
    },
    [dismiss]
  );

  const info = useCallback((msg: string) => add(msg, "info"), [add]);
  const error = useCallback((msg: string) => add(msg, "error"), [add]);
  const success = useCallback((msg: string) => add(msg, "success"), [add]);

  return (
    <ToastContext.Provider value={{ info, error, success }}>
      {children}
      {mounted &&
        createPortal(
          <div
            aria-live="polite"
            aria-atomic="false"
            className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 flex-col gap-2"
          >
            {toasts.map((item) => (
              <div key={item.id} className="pointer-events-auto">
                <Toast item={item} onClose={dismiss} />
              </div>
            ))}
          </div>,
          document.body
        )}
    </ToastContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used inside <ToastProvider>");
  }
  return ctx;
}

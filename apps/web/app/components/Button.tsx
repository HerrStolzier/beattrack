"use client";

import { type ButtonHTMLAttributes, type ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
  children: ReactNode;
}

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-amber text-surface font-semibold hover:bg-amber-light active:bg-gold shadow-[0_0_16px_var(--color-amber-dim)]",
  secondary:
    "glass border border-border-glass text-text-primary hover:bg-surface-elevated hover:border-amber/30",
  ghost:
    "bg-transparent text-text-secondary hover:text-text-primary hover:bg-surface-raised",
};

const sizeStyles: Record<Size, string> = {
  sm: "px-3 py-1.5 text-xs rounded-lg gap-1.5",
  md: "px-4 py-2.5 text-sm rounded-xl gap-2",
  lg: "px-6 py-3 text-sm rounded-xl gap-2.5",
};

function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        className="opacity-25"
      />
      <path
        d="M4 12a8 8 0 018-8"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        className="opacity-75"
      />
    </svg>
  );
}

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      className={`inline-flex items-center justify-center font-medium transition-all duration-200 ${variantStyles[variant]} ${sizeStyles[size]} ${isDisabled ? "opacity-50 pointer-events-none" : "cursor-pointer hover:scale-[1.02] active:scale-[0.97]"} ${className}`}
      disabled={isDisabled}
      {...props}
    >
      {loading ? <Spinner /> : icon}
      <span>{children}</span>
    </button>
  );
}

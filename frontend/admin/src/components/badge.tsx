import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";
import { cn } from "../lib/utils";

export const badgeVariants = cva(
  "inline-flex items-center rounded-full border font-bold uppercase tracking-wider transition-colors",
  {
    variants: {
      tone: {
        neutral: "border-border bg-secondary text-muted-foreground",
        info: "border-accent/20 bg-accent/10 text-accent",
        success: "border-primary/20 bg-primary/10 text-primary",
        warning: "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
        danger: "border-destructive/20 bg-destructive/10 text-destructive",
      },
      size: {
        sm: "px-2 py-0.5 text-[10px]",
        md: "px-2.5 py-1 text-[11px]",
        lg: "px-3 py-1.5 text-xs",
      },
    },
    defaultVariants: {
      tone: "neutral",
      size: "md",
    },
  }
);

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline'
}

function mapVariantToTone(variant?: BadgeProps['variant']): BadgeProps['tone'] {
  if (variant === 'default') return 'success'
  if (variant === 'secondary') return 'neutral'
  if (variant === 'destructive') return 'danger'
  if (variant === 'outline') return 'info'
  return undefined
}

export function Badge({ className, tone, size, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone: tone ?? mapVariantToTone(variant), size, className }))} {...props} />;
}

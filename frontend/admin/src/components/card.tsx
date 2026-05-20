import type { HTMLAttributes, ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib/utils";

const cardVariants = cva("rounded-3xl border bg-card text-card-foreground shadow-sm transition-all", {
  variants: {
    variant: {
      default: "border-border",
      elevated: "border-border shadow-xl shadow-slate-950/5 dark:shadow-black/30",
      interactive: "border-border hover:-translate-y-0.5 hover:shadow-xl hover:shadow-primary/10",
      critical: "border-destructive/20 bg-destructive/5",
    },
    padding: {
      sm: "p-4",
      md: "p-6",
      lg: "p-8",
    },
  },
  defaultVariants: {
    variant: "default",
    padding: "md",
  },
});

export interface CardProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof cardVariants> {
  title?: string;
  description?: string;
  eyebrow?: string;
  action?: ReactNode;
}

export function Card({
  className,
  variant,
  padding,
  title,
  description,
  eyebrow,
  action,
  children,
  ...props
}: CardProps) {
  return (
    <section className={cn(cardVariants({ variant, padding, className }))} {...props}>
      {(title || description || eyebrow || action) && (
        <header className="mb-5 flex items-start justify-between gap-4">
          <div className="space-y-1.5">
            {eyebrow ? (
              <p className="text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground">{eyebrow}</p>
            ) : null}
            {title ? <h3 className="text-lg font-black tracking-tight text-foreground">{title}</h3> : null}
            {description ? <p className="text-sm leading-relaxed text-muted-foreground">{description}</p> : null}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

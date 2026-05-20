import * as React from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib/utils";

const modalVariants = cva(
  "relative w-full rounded-[2rem] border bg-card text-card-foreground shadow-2xl transition-all animate-in fade-in zoom-in-95 duration-200",
  {
    variants: {
      size: {
        sm: "max-w-md",
        md: "max-w-2xl",
        lg: "max-w-4xl",
      },
      tone: {
        default: "border-border",
        danger: "border-destructive/20",
      },
    },
    defaultVariants: {
      size: "md",
      tone: "default",
    },
  }
);

export interface ModalProps extends VariantProps<typeof modalVariants> {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  showCloseButton?: boolean;
}

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  size,
  tone,
  closeOnEscape = true,
  closeOnOverlayClick = true,
  showCloseButton = true,
}: ModalProps) {
  React.useEffect(() => {
    if (!open || !closeOnEscape) {
      return undefined;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [closeOnEscape, onOpenChange, open]);

  React.useEffect(() => {
    if (!open) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open) {
    return null;
  }

  return createPortal(
    <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm"
        onClick={() => {
          if (closeOnOverlayClick) {
            onOpenChange(false);
          }
        }}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="storybook-modal-title"
        aria-describedby={description ? "storybook-modal-description" : undefined}
        className={cn(modalVariants({ size, tone }))}
      >
        <header className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
          <div className="space-y-1.5">
            <h2 id="storybook-modal-title" className="text-2xl font-black tracking-tight text-foreground">
              {title}
            </h2>
            {description ? (
              <p id="storybook-modal-description" className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
                {description}
              </p>
            ) : null}
          </div>
          {showCloseButton ? (
            <button
              type="button"
              aria-label="Fechar modal"
              className="rounded-xl p-2 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-5 w-5" />
            </button>
          ) : null}
        </header>
        <div className="max-h-[70vh] overflow-y-auto px-6 py-6">{children}</div>
        {footer ? <footer className="border-t border-border bg-secondary/30 px-6 py-4">{footer}</footer> : null}
      </div>
    </div>,
    document.body
  );
}

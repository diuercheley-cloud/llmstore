import { Loader2, X } from "lucide-react";
import { toast as sonnerToast, Toaster } from "sonner";
import { badgeVariants } from "./badge";
import { cn } from "../lib/utils";

export type ToastTone = "neutral" | "success" | "warning" | "danger" | "info";

export interface ToastProps {
  title: string;
  description?: string;
  tone?: ToastTone;
  actionLabel?: string;
  onAction?: () => void;
  onDismiss?: () => void;
  isLoading?: boolean;
}

const toastToneClasses: Record<ToastTone, string> = {
  neutral: "border-border bg-card text-foreground",
  info: "border-accent/20 bg-accent/5 text-foreground",
  success: "border-primary/20 bg-primary/5 text-foreground",
  warning: "border-amber-500/20 bg-amber-500/5 text-foreground",
  danger: "border-destructive/20 bg-destructive/5 text-foreground",
};

export function Toast({
  title,
  description,
  tone = "neutral",
  actionLabel,
  onAction,
  onDismiss,
  isLoading = false,
}: ToastProps) {
  return (
    <div className={cn("w-full max-w-sm rounded-2xl border p-4 shadow-xl", toastToneClasses[tone])}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <span className={cn(badgeVariants({ tone, size: "sm" }))}>{tone}</span>
          <div>
            <p className="font-bold text-foreground">{title}</p>
            {description ? <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{description}</p> : null}
          </div>
        </div>
        <button
          type="button"
          aria-label="Dispensar toast"
          className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
          onClick={onDismiss}
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {(actionLabel || isLoading) && (
        <div className="mt-4 flex items-center justify-between gap-3 border-t border-border/70 pt-3">
          {isLoading ? (
            <span className="inline-flex items-center gap-2 text-xs font-semibold text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Processando
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">Acompanhe a operação em tempo real.</span>
          )}
          {actionLabel ? (
            <button
              type="button"
              onClick={onAction}
              className="rounded-lg bg-foreground px-3 py-2 text-xs font-bold text-background transition-opacity hover:opacity-90"
            >
              {actionLabel}
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}

export function showToast({ tone = "neutral", ...props }: ToastProps) {
  return sonnerToast.custom(
    (id) => (
      <Toast
        {...props}
        tone={tone}
        onDismiss={() => {
          props.onDismiss?.();
          sonnerToast.dismiss(id);
        }}
      />
    ),
    {
      duration: props.isLoading ? Infinity : 5000,
    }
  );
}

export function ToasterHost() {
  return <Toaster closeButton richColors position="top-right" />;
}

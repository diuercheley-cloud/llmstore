import { cn } from "../lib/utils";

export function Progress({ value, className }: { value: number, className?: string }) {
  return (
    <div className={cn("w-full h-2 bg-slate-100 rounded-full overflow-hidden", className)}>
      <div 
        className="h-full bg-primary transition-all duration-300 ease-out" 
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-slate-200", className)}
      {...props}
    />
  );
}

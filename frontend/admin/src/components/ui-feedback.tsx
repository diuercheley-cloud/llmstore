import { cn } from "../lib/utils";
import { CheckCircle2, XCircle, Loader2, AlertCircle, Home, ArrowLeft, Box } from "lucide-react";
import { Link } from "react-router-dom";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted/50", className)}
      {...props}
    />
  );
}

export function TableSkeleton({ rows = 5, cols = 5 }: { rows?: number, cols?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, i) => (
        <tr key={i} className="flex flex-col md:table-row p-4 md:p-0 border-b md:border-b-0">
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-6 py-4">
              <Skeleton className="h-4 w-full" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function CardSkeleton() {
  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-9 flex-1 rounded-xl" />
        <Skeleton className="h-9 flex-1 rounded-xl" />
      </div>
    </div>
  );
}

export function StatusBadge({ status }: { status: boolean | 'online' | 'offline' }) {
  const isOnline = status === true || status === 'online';
  return (
    <div className={cn(
      "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider",
      isOnline ? "bg-primary/20 text-primary" : "bg-secondary text-muted-foreground"
    )}>
      <div className={cn("w-1.5 h-1.5 rounded-full", isOnline ? "bg-primary animate-pulse" : "bg-muted-foreground")} />
      {isOnline ? 'Online' : 'Offline'}
    </div>
  );
}

export function SavingIndicator({ isSaving }: { isSaving: boolean }) {
  if (!isSaving) return null;
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground animate-in fade-in duration-300">
      <Loader2 className="w-3 h-3 animate-spin" />
      <span>Salvando alterações...</span>
    </div>
  );
}

export function Progress({ value, className }: { value: number, className?: string }) {
  return (
    <div className={cn("w-full h-2 bg-secondary rounded-full overflow-hidden", className)}>
      <div 
        className="h-full bg-primary transition-all duration-300 ease-out" 
        style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
      />
    </div>
  );
}

export function ErrorFallback({ error, resetErrorBoundary }: { error?: Error, resetErrorBoundary?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-card border border-dashed border-border rounded-3xl">
      <div className="p-4 bg-destructive/10 text-destructive rounded-full mb-4">
        <AlertCircle className="w-12 h-12" />
      </div>
      <h2 className="text-xl font-bold mb-2">Ops! Algo deu errado.</h2>
      <p className="text-muted-foreground mb-6 max-w-md">
        {error?.message || "Não foi possível carregar os dados. Verifique sua conexão ou tente novamente."}
      </p>
      <button 
        onClick={resetErrorBoundary}
        className="bg-primary text-white px-6 py-2.5 rounded-xl font-bold shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all"
      >
        Tentar Novamente
      </button>
    </div>
  );
}

export function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center p-4">
      <div className="mb-8 relative">
        <div className="text-9xl font-black text-primary/5 select-none">404</div>
        <div className="absolute inset-0 flex items-center justify-center">
          <Box className="w-20 h-20 text-primary animate-bounce" />
        </div>
      </div>
      <h1 className="text-4xl font-black mb-4">Página não encontrada</h1>
      <p className="text-muted-foreground mb-8 max-w-md">
        A página que você está procurando não existe ou foi movida para um novo endereço.
      </p>
      <div className="flex flex-col sm:flex-row gap-4">
        <Link 
          to="/" 
          className="bg-primary text-white px-8 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-primary/90 transition-all shadow-xl shadow-primary/20"
        >
          <Home className="w-5 h-5" />
          Voltar ao Hub
        </Link>
        <button 
          onClick={() => window.history.back()}
          className="bg-secondary text-foreground px-8 py-3 rounded-2xl font-bold flex items-center gap-2 hover:bg-secondary/80 transition-all"
        >
          <ArrowLeft className="w-5 h-5" />
          Voltar
        </button>
      </div>
    </div>
  );
}

import { Loader2, AlertCircle } from "lucide-react";
import { cn } from "../lib/utils";

export interface TableColumn<TData> {
  key: keyof TData | string;
  header: string;
  align?: "left" | "center" | "right";
  width?: string;
  render?: (row: TData, rowIndex: number) => React.ReactNode;
}

export interface TableProps<TData> {
  columns: TableColumn<TData>[];
  data: TData[];
  caption?: string;
  emptyMessage?: string;
  error?: string;
  isLoading?: boolean;
  isDisabled?: boolean;
  rowKey?: keyof TData | ((row: TData, rowIndex: number) => string);
}

const alignmentClasses = {
  left: "text-left",
  center: "text-center",
  right: "text-right",
};

export function Table<TData>({
  columns,
  data,
  caption,
  emptyMessage = "Nenhum dado disponível.",
  error,
  isLoading = false,
  isDisabled = false,
  rowKey,
}: TableProps<TData>) {
  if (error) {
    return (
      <div className="rounded-3xl border border-destructive/20 bg-destructive/5 p-6 text-destructive">
        <div className="flex items-center gap-2 font-bold">
          <AlertCircle className="h-5 w-5" />
          Falha ao carregar tabela
        </div>
        <p className="mt-2 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "overflow-hidden rounded-3xl border border-border bg-card shadow-sm",
        isDisabled && "pointer-events-none opacity-60"
      )}
    >
      <div className="overflow-x-auto">
        <table className="min-w-full border-collapse">
          {caption ? <caption className="sr-only">{caption}</caption> : null}
          <thead className="bg-secondary/40">
            <tr>
              {columns.map((column) => (
                <th
                  key={String(column.key)}
                  className={cn(
                    "px-5 py-4 text-[10px] font-black uppercase tracking-[0.2em] text-muted-foreground",
                    alignmentClasses[column.align ?? "left"]
                  )}
                  style={column.width ? { width: column.width } : undefined}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading ? (
              <tr>
                <td colSpan={columns.length} className="px-5 py-12">
                  <div className="flex items-center justify-center gap-3 text-sm font-semibold text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    Carregando linhas...
                  </div>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-5 py-12 text-center text-sm text-muted-foreground">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row, rowIndex) => {
                const resolvedKey =
                  typeof rowKey === "function"
                    ? rowKey(row, rowIndex)
                    : rowKey
                      ? String(row[rowKey])
                      : `${rowIndex}`;

                return (
                  <tr
                    key={resolvedKey}
                    className="transition-colors hover:bg-secondary/30 focus-within:bg-primary/5"
                  >
                    {columns.map((column) => (
                      <td
                        key={String(column.key)}
                        className={cn(
                          "px-5 py-4 text-sm text-foreground",
                          alignmentClasses[column.align ?? "left"]
                        )}
                      >
                        {column.render
                          ? column.render(row, rowIndex)
                          : String((row as Record<string, unknown>)[String(column.key)] ?? "")}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

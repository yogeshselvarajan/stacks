export function RowSkeleton({ columns }: { columns: number }) {
  return (
    <tr>
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div
            data-testid="skeleton-cell"
            className="h-4 animate-pulse rounded"
            style={{ background: "var(--color-surface-2)" }}
          />
        </td>
      ))}
    </tr>
  );
}

export function CardSkeleton() {
  return (
    <div className="rounded-lg border p-4" style={{ borderColor: "var(--color-border)" }}>
      <div data-testid="skeleton-line" className="mb-2 h-4 w-2/3 animate-pulse rounded" style={{ background: "var(--color-surface-2)" }} />
      <div data-testid="skeleton-line" className="mb-4 h-3 w-1/3 animate-pulse rounded" style={{ background: "var(--color-surface-2)" }} />
      <div data-testid="skeleton-actions" className="flex gap-2">
        <div className="h-8 w-20 animate-pulse rounded" style={{ background: "var(--color-surface-2)" }} />
        <div className="h-8 w-20 animate-pulse rounded" style={{ background: "var(--color-surface-2)" }} />
      </div>
    </div>
  );
}

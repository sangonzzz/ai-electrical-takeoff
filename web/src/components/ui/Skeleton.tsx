interface Props {
  className?: string;
}

export function Skeleton({ className = "" }: Props) {
  return <div className={`skeleton ${className}`} aria-hidden />;
}

export function SheetSkeleton() {
  return (
    <div className="flex h-full min-h-0 flex-col gap-2 p-2">
      <div className="card flex items-center gap-3 px-4 py-3">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="ml-auto h-6 w-24" />
      </div>
      <div className="flex gap-2 px-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-16 flex-1" />
        ))}
      </div>
      <div className="grid min-h-0 flex-1 gap-2 p-2 lg:grid-cols-[minmax(0,1fr)_360px]">
        <Skeleton className="h-full min-h-[320px]" />
        <Skeleton className="h-full min-h-[320px]" />
      </div>
    </div>
  );
}

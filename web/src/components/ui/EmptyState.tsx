import type { ReactNode } from "react";

interface Props {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}

export function EmptyState({ title, description, action, icon }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      {icon && <div className="text-[var(--muted)]">{icon}</div>}
      <div>
        <p className="text-sm font-semibold text-[var(--ink)]">{title}</p>
        {description && (
          <p className="mt-1 max-w-sm text-[13px] leading-relaxed text-[var(--muted)]">
            {description}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}

import { AlertCircle } from "lucide-react";
import type { ReactNode } from "react";

interface Props {
  title?: string;
  message: string;
  action?: ReactNode;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  action,
}: Props) {
  return (
    <div className="card flex flex-col items-start gap-3 border-red-200 bg-[var(--danger-soft)] p-6">
      <div className="flex items-center gap-2 text-[var(--danger)]">
        <AlertCircle size={18} />
        <p className="text-sm font-semibold">{title}</p>
      </div>
      <p className="text-[13px] text-[var(--ink-soft)]">{message}</p>
      {action}
    </div>
  );
}

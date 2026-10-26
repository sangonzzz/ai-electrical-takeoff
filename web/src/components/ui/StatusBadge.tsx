import type { JobStatus } from "@/api/types";

const STYLES: Record<JobStatus, string> = {
  queued: "bg-slate-100 text-slate-700",
  running: "bg-sky-100 text-sky-800",
  succeeded: "bg-emerald-100 text-emerald-800",
  failed: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={`chip capitalize ${STYLES[status]}`}
      data-status={status}
    >
      {status}
    </span>
  );
}

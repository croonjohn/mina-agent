const colors: Record<string, string> = {
  pending: "bg-yellow-900/50 text-yellow-300 border-yellow-700",
  approved: "bg-blue-900/50 text-blue-300 border-blue-700",
  published: "bg-green-900/50 text-green-300 border-green-700",
  rejected: "bg-red-900/50 text-red-300 border-red-700",
  failed: "bg-red-900/50 text-red-300 border-red-700",
  running: "bg-purple-900/50 text-purple-300 border-purple-700",
  completed: "bg-green-900/50 text-green-300 border-green-700",
};

export default function StatusBadge({ status }: { status: string }) {
  const c = colors[status] || "bg-zinc-800 text-zinc-300 border-zinc-600";
  return (
    <span className={`inline-block px-2 py-0.5 text-xs font-medium rounded border ${c}`}>
      {status}
    </span>
  );
}

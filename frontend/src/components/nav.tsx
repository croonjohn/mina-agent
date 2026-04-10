"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getEscalationCount } from "@/lib/api";

const links: { href: string; label: string; hasBadge?: boolean }[] = [
  { href: "/", label: "Dashboard" },
  { href: "/content", label: "Content Queue" },
  { href: "/trends", label: "Trends" },
  { href: "/pipeline", label: "Pipeline" },
  { href: "/published", label: "Published" },
  { href: "/templates", label: "Templates" },
  { href: "/tone-guide", label: "Tone Guide" },
  { href: "/escalations", label: "Escalations", hasBadge: true },
  { href: "/metrics", label: "Metrics" },
  { href: "/settings", label: "Settings" },
];

export default function Nav() {
  const pathname = usePathname();
  const [escalationCount, setEscalationCount] = useState(0);

  useEffect(() => {
    getEscalationCount()
      .then((data) => setEscalationCount(data.open))
      .catch(() => {});
  }, []);

  return (
    <nav className="bg-zinc-900 border-b border-zinc-800">
      <div className="max-w-7xl mx-auto px-4 flex items-center h-14 gap-8">
        <Link href="/" className="text-lg font-bold text-white tracking-tight">
          Mina Agent
        </Link>
        <div className="flex gap-1">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={`px-3 py-1.5 rounded text-sm transition-colors flex items-center gap-1.5 ${
                pathname === l.href
                  ? "bg-zinc-700 text-white"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800"
              }`}
            >
              {l.label}
              {l.hasBadge && escalationCount > 0 && (
                <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold bg-red-600 text-white rounded-full">
                  {escalationCount}
                </span>
              )}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

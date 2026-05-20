"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  User,
  Briefcase,
  FileText,
  CheckSquare,
  MessageSquare,
  ScrollText,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/profile", label: "Profile", icon: User },
  { href: "/jobs", label: "Jobs", icon: Briefcase },
  { href: "/applications", label: "Applications", icon: FileText },
  { href: "/approvals", label: "Approvals", icon: CheckSquare, badge: true },
  { href: "/conversations", label: "Conversations", icon: MessageSquare },
  { href: "/logs", label: "Logs", icon: ScrollText },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [pendingApprovals, setPendingApprovals] = useState(0);

  useEffect(() => {
    if (!isAuthenticated()) return;
    const fetchPending = () => {
      api
        .get<{ total: number }>("/api/v1/approvals/?status=pending&limit=1")
        .then((d) => setPendingApprovals(d.total))
        .catch(() => {});
    };
    fetchPending();
    const interval = setInterval(fetchPending, 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <aside className="w-64 min-h-screen bg-card border-r border-border flex flex-col">
      <div className="p-6 border-b border-border">
        <h1 className="text-xl font-bold text-primary">Job CRM</h1>
        <p className="text-xs text-muted-foreground mt-1">AI-powered job search</p>
      </div>

      <nav className="flex-1 p-4">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href || pathname.startsWith(item.href + "/");
            const showBadge = item.badge && pendingApprovals > 0;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="flex-1">{item.label}</span>
                  {showBadge && (
                    <span className="min-w-[1.25rem] h-5 flex items-center justify-center rounded-full bg-destructive text-destructive-foreground text-xs font-bold px-1">
                      {pendingApprovals > 99 ? "99+" : pendingApprovals}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="p-4 border-t border-border">
        <p className="text-xs text-muted-foreground">Phase 5</p>
      </div>
    </aside>
  );
}

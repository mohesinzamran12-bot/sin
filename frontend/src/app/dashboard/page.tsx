"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Briefcase, User, CheckSquare, Activity, Sparkles, DollarSign } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import type { DashboardStats } from "@/types";

type SystemEvent = {
  id: string;
  level: string;
  source: string;
  message: string;
  event_metadata: Record<string, unknown> | null;
  created_at: string;
};

type SystemEventListResponse = {
  items: SystemEvent[];
  total: number;
  skip: number;
  limit: number;
};

function relativeTime(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function eventIcon(source: string): string {
  if (source.includes("collect")) return "🔍";
  if (source.includes("send") || source.includes("message")) return "✉️";
  if (source.includes("sync")) return "🔄";
  return "ℹ️";
}

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activity, setActivity] = useState<SystemEvent[]>([]);
  const [activityLoading, setActivityLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    api.get<DashboardStats>("/api/v1/stats/dashboard")
      .then(setStats)
      .catch(() => {});

    setActivityLoading(true);
    api.get<SystemEventListResponse>("/api/v1/logs/system?limit=10")
      .then((data) => setActivity(data.items))
      .catch(() => {})
      .finally(() => setActivityLoading(false));
  }, [router]);

  const statCards = [
    {
      title: "Total Jobs",
      value: stats?.total_jobs ?? "—",
      icon: Briefcase,
      description: `${stats?.active_jobs ?? "—"} active`,
      href: "/jobs",
    },
    {
      title: "Applications",
      value: stats?.total_applications ?? "—",
      icon: Activity,
      description: `${stats?.pending_approvals ?? "—"} pending approval`,
      href: "/applications",
    },
    {
      title: "Pending Approvals",
      value: stats?.pending_approvals ?? "—",
      icon: CheckSquare,
      description: "Awaiting your review",
      href: "/approvals",
    },
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Dashboard" />
        <main className="flex-1 p-6 space-y-6">

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {statCards.map((stat) => {
              const Icon = stat.icon;
              return (
                <Link key={stat.title} href={stat.href} className="block hover:no-underline">
                  <Card className="hover:shadow-md transition-shadow cursor-pointer">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-bold">{stat.value}</div>
                      <p className="text-xs text-muted-foreground">{stat.description}</p>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">AI Usage Today</CardTitle>
                <Sparkles className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent className="space-y-1">
                <div className="text-2xl font-bold">
                  {stats?.total_tokens_today.toLocaleString() ?? "—"}
                </div>
                <p className="text-xs text-muted-foreground">tokens used today</p>
                <div className="flex items-center gap-1 text-xs text-muted-foreground mt-2">
                  <DollarSign className="h-3 w-3" />
                  Est. cost: ${stats?.estimated_cost_today_usd.toFixed(4) ?? "0.0000"}
                  {" · "}
                  {stats?.total_ai_calls ?? 0} total AI calls
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-2">
                <Button asChild>
                  <Link href="/jobs">
                    <Briefcase className="h-4 w-4 mr-2" />
                    Browse Jobs
                  </Link>
                </Button>
                <Button variant="outline" asChild>
                  <Link href="/profile">
                    <User className="h-4 w-4 mr-2" />
                    Update Profile &amp; CV
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              {activityLoading ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : activity.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No activity yet — start by collecting jobs.
                </p>
              ) : (
                <ul className="space-y-3">
                  {activity.map((event) => (
                    <li key={event.id} className="flex items-start gap-3">
                      <span className="text-lg leading-none mt-0.5" aria-hidden>
                        {eventIcon(event.source)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate">{event.message}</p>
                        <p className="text-xs text-muted-foreground">
                          {event.source} · {relativeTime(event.created_at)}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

        </main>
      </div>
    </div>
  );
}

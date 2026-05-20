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

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    api.get<DashboardStats>("/api/v1/stats/dashboard")
      .then(setStats)
      .catch(() => {});
  }, [router]);

  const statCards = [
    {
      title: "Total Jobs",
      value: stats?.total_jobs ?? "—",
      icon: Briefcase,
      description: `${stats?.active_jobs ?? "—"} active`,
    },
    {
      title: "Applications",
      value: stats?.total_applications ?? "—",
      icon: Activity,
      description: `${stats?.pending_approvals ?? "—"} pending approval`,
    },
    {
      title: "Pending Approvals",
      value: stats?.pending_approvals ?? "—",
      icon: CheckSquare,
      description: "Awaiting your review",
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
                <Card key={stat.title}>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stat.value}</div>
                    <p className="text-xs text-muted-foreground">{stat.description}</p>
                  </CardContent>
                </Card>
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

        </main>
      </div>
    </div>
  );
}

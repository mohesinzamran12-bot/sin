"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Briefcase, User, CheckSquare, Activity } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { isAuthenticated } from "@/lib/auth";

const statCards = [
  { title: "Total Jobs", value: "—", icon: Briefcase, description: "Collected jobs" },
  { title: "Active Applications", value: "0", icon: Activity, description: "In progress" },
  { title: "Pending Approvals", value: "0", icon: CheckSquare, description: "Awaiting review" },
];

export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Dashboard" />
        <main className="flex-1 p-6 space-y-6">
          {/* Stat cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {statCards.map((stat) => {
              const Icon = stat.icon;
              return (
                <Card key={stat.title}>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium">
                      {stat.title}
                    </CardTitle>
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stat.value}</div>
                    <p className="text-xs text-muted-foreground">
                      {stat.description}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Quick actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="flex gap-3">
              <Button asChild>
                <Link href="/jobs">
                  <Briefcase className="h-4 w-4 mr-2" />
                  Go to Jobs
                </Link>
              </Button>
              <Button variant="outline" asChild>
                <Link href="/profile">
                  <User className="h-4 w-4 mr-2" />
                  Go to Profile
                </Link>
              </Button>
            </CardContent>
          </Card>

          {/* Recent activity placeholder */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                No recent activity. Start by adding jobs or uploading your CV.
              </p>
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { toast } from "sonner";
import { ArrowLeft, ExternalLink, Building2, MapPin, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api-client";
import { formatDate, formatSalary } from "@/lib/utils";
import type { Job } from "@/types";

export default function JobDetailPage() {
  const router = useRouter();
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    api.get<Job>(`/api/v1/jobs/${id}`)
      .then(setJob)
      .catch(() => toast.error("Job not found"))
      .finally(() => setLoading(false));
  }, [id, router]);

  async function handleDeactivate() {
    if (!job) return;
    try {
      const updated = await api.delete<Job>(`/api/v1/jobs/${job.id}`);
      setJob(updated);
      toast.success("Job deactivated");
    } catch {
      toast.error("Failed to deactivate job");
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Header title="Job Detail" />
          <main className="p-6 text-sm text-muted-foreground">Loading…</main>
        </div>
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Job Detail" />
        <main className="flex-1 p-6 max-w-3xl space-y-4">

          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>

          <Card>
            <CardHeader>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <CardTitle className="text-xl">{job.title}</CardTitle>
                  <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Building2 className="h-3.5 w-3.5" />
                      {job.company_name}
                    </span>
                    {job.city && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3.5 w-3.5" />
                        {job.city}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Badge variant={job.is_active ? "default" : "destructive"}>
                    {job.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <Badge variant="secondary">{job.source}</Badge>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Salary</span>
                  <p className="text-muted-foreground">
                    {formatSalary(job.salary_min, job.salary_max, job.salary_range)}
                  </p>
                </div>
                <div>
                  <span className="font-medium">Added</span>
                  <p className="text-muted-foreground">{formatDate(job.created_at)}</p>
                </div>
              </div>

              {job.url && (
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  View original posting
                </a>
              )}

              <Separator />

              {job.description && (
                <div>
                  <h3 className="font-medium mb-2">Description</h3>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{job.description}</p>
                </div>
              )}

              {job.requirements && (
                <div>
                  <h3 className="font-medium mb-2">Requirements</h3>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{job.requirements}</p>
                </div>
              )}

              <div className="pt-2 border-t">
                <p className="text-xs text-muted-foreground mb-3">
                  AI scoring available in Phase 2.
                </p>
                {job.is_active && (
                  <Button variant="destructive" size="sm" onClick={handleDeactivate}>
                    <Trash2 className="h-4 w-4 mr-2" />
                    Deactivate Job
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>

        </main>
      </div>
    </div>
  );
}

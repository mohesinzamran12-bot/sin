"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Plus, Search, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { JobCard } from "@/components/job-card";
import { isAuthenticated } from "@/lib/auth";
import { api } from "@/lib/api-client";
import type { Job, JobListResponse } from "@/types";

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [cityFilter, setCityFilter] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  // Add job form
  const [newTitle, setNewTitle] = useState("");
  const [newCompany, setNewCompany] = useState("");
  const [newCity, setNewCity] = useState("");
  const [newSalary, setNewSalary] = useState("");
  const [newUrl, setNewUrl] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push("/login");
      return;
    }
    fetchJobs();
  }, [router]);

  async function fetchJobs(city?: string) {
    setLoading(true);
    try {
      const params = new URLSearchParams({ is_active: "true", limit: "50" });
      if (city) params.append("city", city);
      const res = await api.get<JobListResponse>(`/api/v1/jobs/?${params}`);
      setJobs(res.items);
      setTotal(res.total);
    } catch (err) {
      toast.error("Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    fetchJobs(cityFilter || undefined);
  }

  async function handleAddJob(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    try {
      const job = await api.post<Job>("/api/v1/jobs/", {
        title: newTitle,
        company_name: newCompany,
        city: newCity || null,
        salary_range: newSalary || null,
        url: newUrl || null,
      });
      setJobs((prev) => [job, ...prev]);
      setTotal((t) => t + 1);
      setNewTitle("");
      setNewCompany("");
      setNewCity("");
      setNewSalary("");
      setNewUrl("");
      setShowAddForm(false);
      toast.success("Job added");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add job");
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Jobs" />
        <main className="flex-1 p-6 space-y-4">

          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">{total} jobs found</p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => fetchJobs(cityFilter || undefined)}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
              <Button size="sm" onClick={() => setShowAddForm((v) => !v)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Job
              </Button>
            </div>
          </div>

          <form onSubmit={handleSearch} className="flex gap-2">
            <Input
              placeholder="Filter by city…"
              value={cityFilter}
              onChange={(e) => setCityFilter(e.target.value)}
              className="max-w-xs"
            />
            <Button type="submit" variant="outline" size="sm">
              <Search className="h-4 w-4" />
            </Button>
          </form>

          {showAddForm && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Add Job Manually</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleAddJob} className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="jTitle">Job Title *</Label>
                    <Input
                      id="jTitle"
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="jCompany">Company *</Label>
                    <Input
                      id="jCompany"
                      value={newCompany}
                      onChange={(e) => setNewCompany(e.target.value)}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="jCity">City</Label>
                    <Input id="jCity" value={newCity} onChange={(e) => setNewCity(e.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="jSalary">Salary Range</Label>
                    <Input
                      id="jSalary"
                      value={newSalary}
                      onChange={(e) => setNewSalary(e.target.value)}
                      placeholder="20k-30k"
                    />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label htmlFor="jUrl">Job URL</Label>
                    <Input
                      id="jUrl"
                      type="url"
                      value={newUrl}
                      onChange={(e) => setNewUrl(e.target.value)}
                      placeholder="https://…"
                    />
                  </div>
                  <div className="col-span-2 flex gap-2">
                    <Button type="submit" disabled={adding}>
                      {adding ? "Adding…" : "Add Job"}
                    </Button>
                    <Button type="button" variant="outline" onClick={() => setShowAddForm(false)}>
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {loading ? (
            <div className="text-sm text-muted-foreground">Loading…</div>
          ) : jobs.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              No jobs yet. Add one manually or wait for the collector to run.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onClick={() => router.push(`/jobs/${job.id}`)}
                />
              ))}
            </div>
          )}

        </main>
      </div>
    </div>
  );
}

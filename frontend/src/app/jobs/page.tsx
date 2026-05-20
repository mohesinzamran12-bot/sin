"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { JobCard } from "@/components/job-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import type { Job, JobListResponse } from "@/types";

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [cityFilter, setCityFilter] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);
  const [skip, setSkip] = useState(0);
  const limit = 20;

  // Add job form state
  const [showForm, setShowForm] = useState(false);
  const [formTitle, setFormTitle] = useState("");
  const [formCompany, setFormCompany] = useState("");
  const [formCity, setFormCity] = useState("");
  const [formSalary, setFormSalary] = useState("");
  const [formUrl, setFormUrl] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    fetchJobs();
  }, [router, cityFilter, activeOnly, skip]);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: limit.toString(),
      });
      if (activeOnly) params.set("is_active", "true");
      if (cityFilter) params.set("city", cityFilter);

      const data = await api.get<JobListResponse>(
        `/api/v1/jobs/?${params.toString()}`
      );
      setJobs(data.items);
      setTotal(data.total);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to fetch jobs");
    } finally {
      setLoading(false);
    }
  };

  const handleAddJob = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const newJob = await api.post<Job>("/api/v1/jobs/", {
        title: formTitle,
        company_name: formCompany,
        city: formCity || null,
        salary_range: formSalary || null,
        url: formUrl || null,
        description: formDescription || null,
      });
      setJobs((prev) => [newJob, ...prev]);
      setTotal((t) => t + 1);
      setShowForm(false);
      setFormTitle("");
      setFormCompany("");
      setFormCity("");
      setFormSalary("");
      setFormUrl("");
      setFormDescription("");
      toast.success("Job added");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add job");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Jobs" />
        <main className="flex-1 p-6 space-y-4">
          {/* Filters + Add button */}
          <div className="flex items-end gap-4 flex-wrap">
            <div className="space-y-1">
              <Label htmlFor="city-filter">Filter by City</Label>
              <Input
                id="city-filter"
                value={cityFilter}
                onChange={(e) => {
                  setCityFilter(e.target.value);
                  setSkip(0);
                }}
                placeholder="Shanghai, Beijing..."
                className="w-48"
              />
            </div>
            <label className="flex items-center gap-2 cursor-pointer pb-1">
              <input
                type="checkbox"
                checked={activeOnly}
                onChange={(e) => {
                  setActiveOnly(e.target.checked);
                  setSkip(0);
                }}
              />
              <span className="text-sm">Active only</span>
            </label>
            <div className="ml-auto">
              <Button onClick={() => setShowForm(!showForm)}>
                <Plus className="h-4 w-4 mr-2" />
                Add Job
              </Button>
            </div>
          </div>

          {/* Add job form */}
          {showForm && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Add New Job</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleAddJob} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="job-title">Job Title *</Label>
                      <Input
                        id="job-title"
                        value={formTitle}
                        onChange={(e) => setFormTitle(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="job-company">Company *</Label>
                      <Input
                        id="job-company"
                        value={formCompany}
                        onChange={(e) => setFormCompany(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="job-city">City</Label>
                      <Input
                        id="job-city"
                        value={formCity}
                        onChange={(e) => setFormCity(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="job-salary">Salary Range</Label>
                      <Input
                        id="job-salary"
                        value={formSalary}
                        onChange={(e) => setFormSalary(e.target.value)}
                        placeholder="20k-30k"
                      />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="job-url">URL</Label>
                      <Input
                        id="job-url"
                        value={formUrl}
                        onChange={(e) => setFormUrl(e.target.value)}
                        placeholder="https://..."
                      />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="job-desc">Description</Label>
                      <textarea
                        id="job-desc"
                        value={formDescription}
                        onChange={(e) => setFormDescription(e.target.value)}
                        className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                        placeholder="Job description..."
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button type="submit" disabled={submitting}>
                      {submitting ? "Adding..." : "Add Job"}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowForm(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}

          {/* Stats */}
          <p className="text-sm text-muted-foreground">
            {total} job{total !== 1 ? "s" : ""} found
          </p>

          {/* Job grid */}
          {loading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : jobs.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">
                  No jobs found. Add your first job using the button above.
                </p>
              </CardContent>
            </Card>
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

          {/* Pagination */}
          {total > limit && (
            <div className="flex gap-2 justify-center pt-4">
              <Button
                variant="outline"
                size="sm"
                disabled={skip === 0}
                onClick={() => setSkip(Math.max(0, skip - limit))}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground self-center">
                Page {Math.floor(skip / limit) + 1} of {Math.ceil(total / limit)}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={skip + limit >= total}
                onClick={() => setSkip(skip + limit)}
              >
                Next
              </Button>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

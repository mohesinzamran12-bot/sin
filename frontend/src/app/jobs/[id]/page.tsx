"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { ArrowLeft, ExternalLink, Sparkles, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import { formatDate, formatSalary } from "@/lib/utils";
import type { Job, JobScore } from "@/types";

// ── ScoreDisplay component ────────────────────────────────────────────────────

function ScoreDisplay({ score }: { score: JobScore }) {
  const scoreColor =
    score.score >= 70
      ? "text-green-600"
      : score.score >= 40
      ? "text-yellow-600"
      : "text-red-600";

  const breakdownItems = [
    { label: "Skills", value: score.score_breakdown.skills, max: 25 },
    { label: "Experience", value: score.score_breakdown.experience, max: 25 },
    { label: "Salary", value: score.score_breakdown.salary, max: 25 },
    { label: "Culture / Location", value: score.score_breakdown.culture, max: 25 },
  ];

  return (
    <div className="space-y-4">
      {/* Score number */}
      <div className="flex items-center gap-3">
        <span className={`text-5xl font-bold ${scoreColor}`}>
          {Math.round(score.score)}
        </span>
        <span className="text-muted-foreground text-lg">/100</span>
      </div>

      {/* Breakdown bars */}
      <div className="space-y-2">
        {breakdownItems.map(({ label, value, max }) => (
          <div key={label}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">{label}</span>
              <span className="font-medium">
                {value}/{max}
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${(value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <p className="text-sm text-muted-foreground">{score.match_summary}</p>

      {/* Strengths */}
      {score.strengths.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-1">Strengths</p>
          <ul className="space-y-1">
            {score.strengths.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-green-700">
                <span className="mt-0.5">+</span>
                <span>{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Concerns */}
      {score.concerns.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-1">Concerns</p>
          <ul className="space-y-1">
            {score.concerns.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-amber-700">
                <span className="mt-0.5">!</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Model: {score.model_used} &middot; {score.prompt_tokens + score.completion_tokens} tokens
      </p>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function JobDetailPage() {
  const router = useRouter();
  const params = useParams();
  const jobId = params.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // Scoring state
  const [score, setScore] = useState<JobScore | null>(null);
  const [scoring, setScoring] = useState(false);
  const [scoreError, setScoreError] = useState<string | null>(null);

  // Edit form
  const [editTitle, setEditTitle] = useState("");
  const [editCompany, setEditCompany] = useState("");
  const [editCity, setEditCity] = useState("");
  const [editSalary, setEditSalary] = useState("");
  const [editUrl, setEditUrl] = useState("");
  const [editDescription, setEditDescription] = useState("");

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    fetchJob();
  }, [router, jobId]);

  const fetchExistingScore = async (candidateId: string) => {
    try {
      const data = await api.get<JobScore>(
        `/api/v1/jobs/${jobId}/score?candidate_id=${candidateId}`
      );
      setScore(data);
    } catch {
      // 404 is expected if no score exists yet — silently ignore
    }
  };

  const handleGetScore = async () => {
    const candidateId = localStorage.getItem("candidate_id");
    if (!candidateId) {
      toast.error("No candidate profile found. Set up your profile first.");
      return;
    }
    setScoring(true);
    setScoreError(null);
    try {
      const data = await api.post<JobScore>(`/api/v1/jobs/${jobId}/score`, {
        candidate_id: candidateId,
      });
      setScore(data);
      toast.success("Job scored successfully");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Scoring failed";
      if (msg.includes("503") || msg.toLowerCase().includes("api key")) {
        setScoreError("AI scoring is not available (API key not configured).");
      } else {
        setScoreError(msg);
        toast.error(msg);
      }
    } finally {
      setScoring(false);
    }
  };

  const fetchJob = async () => {
    setLoading(true);
    try {
      const data = await api.get<Job>(`/api/v1/jobs/${jobId}`);
      setJob(data);
      populateEdit(data);
      // Try to load existing score
      const candidateId = localStorage.getItem("candidate_id");
      if (candidateId) {
        await fetchExistingScore(candidateId);
      }
    } catch {
      toast.error("Job not found");
      router.push("/jobs");
    } finally {
      setLoading(false);
    }
  };

  const populateEdit = (j: Job) => {
    setEditTitle(j.title);
    setEditCompany(j.company_name);
    setEditCity(j.city || "");
    setEditSalary(j.salary_range || "");
    setEditUrl(j.url || "");
    setEditDescription(j.description || "");
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await api.patch<Job>(`/api/v1/jobs/${jobId}`, {
        title: editTitle,
        company_name: editCompany,
        city: editCity || null,
        salary_range: editSalary || null,
        url: editUrl || null,
        description: editDescription || null,
      });
      setJob(updated);
      setEditing(false);
      toast.success("Job updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to update job");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Mark this job as inactive?")) return;
    try {
      const updated = await api.delete<Job>(`/api/v1/jobs/${jobId}`);
      setJob(updated);
      toast.success("Job marked as inactive");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete job");
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Header title="Job Detail" />
          <main className="flex-1 p-6">
            <p className="text-muted-foreground">Loading...</p>
          </main>
        </div>
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title={job.title} />
        <main className="flex-1 p-6 max-w-3xl space-y-6">
          <Button variant="ghost" size="sm" onClick={() => router.push("/jobs")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Jobs
          </Button>

          {/* Job info */}
          {!editing ? (
            <Card>
              <CardHeader className="flex flex-row items-start justify-between">
                <div>
                  <CardTitle>{job.title}</CardTitle>
                  <p className="text-muted-foreground mt-1">{job.company_name}</p>
                </div>
                <div className="flex gap-2">
                  <Badge variant={job.is_active ? "default" : "destructive"}>
                    {job.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <Badge variant="secondary">{job.source}</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  {job.city && (
                    <div>
                      <span className="font-medium">City:</span> {job.city}
                    </div>
                  )}
                  <div>
                    <span className="font-medium">Salary:</span>{" "}
                    {formatSalary(job.salary_min, job.salary_max, job.salary_range)}
                  </div>
                  <div>
                    <span className="font-medium">Added:</span>{" "}
                    {formatDate(job.created_at)}
                  </div>
                </div>

                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-sm text-primary hover:underline"
                  >
                    <ExternalLink className="h-4 w-4" />
                    View original posting
                  </a>
                )}

                {job.description && (
                  <div>
                    <h4 className="font-medium mb-2 text-sm">Description</h4>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {job.description}
                    </p>
                  </div>
                )}

                {/* AI Match Score */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-primary" />
                      AI Match Score
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {score ? (
                      <ScoreDisplay score={score} />
                    ) : scoreError ? (
                      <div className="flex items-start gap-2 text-sm text-amber-700">
                        <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                        <span>{scoreError}</span>
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        No score yet. Click below to have Claude evaluate this
                        job against your profile.
                      </p>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleGetScore}
                      disabled={scoring}
                    >
                      {scoring
                        ? "Scoring..."
                        : score
                        ? "Re-score"
                        : "Get AI Score"}
                    </Button>
                  </CardContent>
                </Card>

                <div className="flex gap-2">
                  <Button onClick={() => setEditing(true)}>Edit Job</Button>
                  {job.is_active && (
                    <Button variant="destructive" onClick={handleDelete}>
                      Mark Inactive
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Edit Job</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSave} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="edit-title">Job Title *</Label>
                      <Input
                        id="edit-title"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="edit-company">Company *</Label>
                      <Input
                        id="edit-company"
                        value={editCompany}
                        onChange={(e) => setEditCompany(e.target.value)}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="edit-city">City</Label>
                      <Input
                        id="edit-city"
                        value={editCity}
                        onChange={(e) => setEditCity(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="edit-salary">Salary Range</Label>
                      <Input
                        id="edit-salary"
                        value={editSalary}
                        onChange={(e) => setEditSalary(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="edit-url">URL</Label>
                      <Input
                        id="edit-url"
                        value={editUrl}
                        onChange={(e) => setEditUrl(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="edit-desc">Description</Label>
                      <textarea
                        id="edit-desc"
                        value={editDescription}
                        onChange={(e) => setEditDescription(e.target.value)}
                        className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button type="submit" disabled={saving}>
                      {saving ? "Saving..." : "Save Changes"}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setEditing(false);
                        populateEdit(job);
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </div>
  );
}

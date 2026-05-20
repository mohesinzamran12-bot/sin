"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { CvUploader } from "@/components/cv-uploader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import type { Candidate, JobPreferences } from "@/types";

export default function ProfilePage() {
  const router = useRouter();
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPrefs, setSavingPrefs] = useState(false);

  // Profile form state
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  // Preferences form state
  const [targetTitles, setTargetTitles] = useState("");
  const [targetCities, setTargetCities] = useState("");
  const [minSalary, setMinSalary] = useState("");
  const [maxSalary, setMaxSalary] = useState("");
  const [excludedCompanies, setExcludedCompanies] = useState("");
  const [preferredIndustries, setPreferredIndustries] = useState("");
  const [remoteOk, setRemoteOk] = useState(false);
  const [fullTimeOnly, setFullTimeOnly] = useState(true);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    loadProfile();
  }, [router]);

  const loadProfile = async () => {
    try {
      // Try fetching all candidates — for Phase 1 we use the admin email
      // In a real app we'd track the current user's candidate ID
      const me = await api.get<{ email: string }>("/api/v1/auth/me");

      // Try to create or get the candidate for admin
      try {
        const created = await api.post<Candidate>("/api/v1/candidates/", {
          name: "Admin",
          email: me.email,
        });
        setCandidate(created);
        populateForm(created);
      } catch {
        // Candidate might already exist — search isn't available in phase 1
        // We'll show a create form instead
        setCandidate(null);
      }
    } catch {
      toast.error("Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const populateForm = (c: Candidate) => {
    setName(c.name);
    setEmail(c.email);
    setPhone(c.phone || "");
    if (c.preferences) {
      populatePrefs(c.preferences);
    }
  };

  const populatePrefs = (p: JobPreferences) => {
    setTargetTitles(p.target_titles.join(", "));
    setTargetCities(p.target_cities.join(", "));
    setMinSalary(p.min_salary?.toString() || "");
    setMaxSalary(p.max_salary?.toString() || "");
    setExcludedCompanies(p.excluded_companies.join(", "));
    setPreferredIndustries(p.preferred_industries.join(", "));
    setRemoteOk(p.remote_ok);
    setFullTimeOnly(p.full_time_only);
  };

  const parseList = (val: string): string[] =>
    val
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      const created = await api.post<Candidate>("/api/v1/candidates/", {
        name,
        email,
        phone: phone || null,
      });
      setCandidate(created);
      toast.success("Profile created");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to create profile");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidate) return;
    setSavingProfile(true);
    try {
      const updated = await api.patch<Candidate>(
        `/api/v1/candidates/${candidate.id}`,
        { name, phone: phone || null }
      );
      setCandidate(updated);
      toast.success("Profile saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save profile");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!candidate) return;
    setSavingPrefs(true);
    try {
      const prefs = await api.put<JobPreferences>(
        `/api/v1/candidates/${candidate.id}/preferences`,
        {
          target_titles: parseList(targetTitles),
          target_cities: parseList(targetCities),
          min_salary: minSalary ? parseInt(minSalary) : null,
          max_salary: maxSalary ? parseInt(maxSalary) : null,
          excluded_companies: parseList(excludedCompanies),
          preferred_industries: parseList(preferredIndustries),
          remote_ok: remoteOk,
          full_time_only: fullTimeOnly,
        }
      );
      setCandidate((prev) => prev ? { ...prev, preferences: prefs } : prev);
      toast.success("Preferences saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to save preferences");
    } finally {
      setSavingPrefs(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Header title="Profile" />
          <main className="flex-1 p-6">
            <p className="text-muted-foreground">Loading...</p>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Profile" />
        <main className="flex-1 p-6 space-y-6 max-w-2xl">
          {/* Profile form */}
          <Card>
            <CardHeader>
              <CardTitle>Personal Information</CardTitle>
            </CardHeader>
            <CardContent>
              <form
                onSubmit={candidate ? handleSaveProfile : handleCreateProfile}
                className="space-y-4"
              >
                <div className="space-y-2">
                  <Label htmlFor="name">Full Name</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    disabled={!!candidate}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+1 234 567 8900"
                  />
                </div>
                <Button type="submit" disabled={savingProfile}>
                  {savingProfile
                    ? "Saving..."
                    : candidate
                    ? "Save Profile"
                    : "Create Profile"}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* CV Upload section */}
          {candidate && (
            <Card>
              <CardHeader>
                <CardTitle>CV / Resume</CardTitle>
              </CardHeader>
              <CardContent>
                <CvUploader
                  candidateId={candidate.id}
                  currentCvPath={candidate.cv_file_path}
                  wordCount={
                    candidate.cv_parsed_json
                      ? (candidate.cv_parsed_json.word_count as number)
                      : null
                  }
                  onUploadSuccess={(updated) => {
                    setCandidate(updated);
                    toast.success("CV processed successfully");
                  }}
                />
              </CardContent>
            </Card>
          )}

          {/* Job preferences */}
          {candidate && (
            <Card>
              <CardHeader>
                <CardTitle>Job Preferences</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSavePreferences} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="target-titles">Target Job Titles</Label>
                      <Input
                        id="target-titles"
                        value={targetTitles}
                        onChange={(e) => setTargetTitles(e.target.value)}
                        placeholder="Engineer, Developer, Manager"
                      />
                      <p className="text-xs text-muted-foreground">Comma-separated</p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="target-cities">Target Cities</Label>
                      <Input
                        id="target-cities"
                        value={targetCities}
                        onChange={(e) => setTargetCities(e.target.value)}
                        placeholder="Beijing, Shanghai, Remote"
                      />
                      <p className="text-xs text-muted-foreground">Comma-separated</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="min-salary">Min Salary</Label>
                      <Input
                        id="min-salary"
                        type="number"
                        value={minSalary}
                        onChange={(e) => setMinSalary(e.target.value)}
                        placeholder="20000"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="max-salary">Max Salary</Label>
                      <Input
                        id="max-salary"
                        type="number"
                        value={maxSalary}
                        onChange={(e) => setMaxSalary(e.target.value)}
                        placeholder="50000"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="preferred-industries">Preferred Industries</Label>
                    <Input
                      id="preferred-industries"
                      value={preferredIndustries}
                      onChange={(e) => setPreferredIndustries(e.target.value)}
                      placeholder="Tech, Finance, Healthcare"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="excluded-companies">Excluded Companies</Label>
                    <Input
                      id="excluded-companies"
                      value={excludedCompanies}
                      onChange={(e) => setExcludedCompanies(e.target.value)}
                      placeholder="Company A, Company B"
                    />
                  </div>

                  <Separator />

                  <div className="flex gap-6">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={remoteOk}
                        onChange={(e) => setRemoteOk(e.target.checked)}
                        className="rounded border-border"
                      />
                      <span className="text-sm">Remote OK</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={fullTimeOnly}
                        onChange={(e) => setFullTimeOnly(e.target.checked)}
                        className="rounded border-border"
                      />
                      <span className="text-sm">Full-time Only</span>
                    </label>
                  </div>

                  <Button type="submit" disabled={savingPrefs}>
                    {savingPrefs ? "Saving..." : "Save Preferences"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          )}
        </main>
      </div>
    </div>
  );
}

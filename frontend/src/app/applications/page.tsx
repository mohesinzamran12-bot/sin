"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Send, MessageSquare, Clock, FileText } from "lucide-react";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import { formatDate } from "@/lib/utils";
import type { Application, ApplicationListResponse } from "@/types";

type StatusFilter =
  | "all"
  | "pending_approval"
  | "approved"
  | "sent"
  | "replied"
  | "interviewing"
  | "rejected"
  | "withdrawn";

const STATUS_COLORS: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  pending_approval: "outline",
  approved: "secondary",
  sent: "default",
  replied: "default",
  interviewing: "secondary",
  rejected: "destructive",
  withdrawn: "destructive",
};

const STATUS_LABELS: Record<string, string> = {
  pending_approval: "Pending",
  approved: "Approved",
  sent: "Sent",
  replied: "Replied",
  interviewing: "Interviewing",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const TABS: { label: string; value: StatusFilter }[] = [
  { label: "All", value: "all" },
  { label: "Pending", value: "pending_approval" },
  { label: "Approved", value: "approved" },
  { label: "Sent", value: "sent" },
  { label: "Replied", value: "replied" },
  { label: "Interviewing", value: "interviewing" },
  { label: "Rejected", value: "rejected" },
];

export default function ApplicationsPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<Application[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [skip, setSkip] = useState(0);
  const [sendingId, setSendingId] = useState<string | null>(null);
  const limit = 20;

  const fetchApplications = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: skip.toString(),
        limit: limit.toString(),
      });
      if (statusFilter !== "all") params.set("status", statusFilter);

      const data = await api.get<ApplicationListResponse>(
        `/api/v1/applications/?${params}`
      );
      setApplications(data.items);
      setTotal(data.total);
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to load applications"
      );
    } finally {
      setLoading(false);
    }
  }, [statusFilter, skip]);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    fetchApplications();
  }, [router, fetchApplications]);

  const handleSend = async (applicationId: string) => {
    setSendingId(applicationId);
    try {
      const result = await api.post<{ task_id: string; status: string }>(
        `/api/v1/applications/${applicationId}/send`,
        {}
      );
      toast.success(`Send queued (task ${result.task_id})`);
      // Refresh to show updated status
      fetchApplications();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Send failed");
    } finally {
      setSendingId(null);
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Applications" />
        <main className="flex-1 p-6 space-y-4">
          {/* Status filter tabs */}
          <div className="flex gap-2 border-b border-border pb-2 flex-wrap">
            {TABS.map((tab) => (
              <button
                key={tab.value}
                onClick={() => {
                  setStatusFilter(tab.value);
                  setSkip(0);
                }}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  statusFilter === tab.value
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`}
              >
                {tab.label}
              </button>
            ))}
            <span className="ml-auto text-sm text-muted-foreground self-center">
              {total} application{total !== 1 ? "s" : ""}
            </span>
          </div>

          {loading && (
            <p className="text-muted-foreground text-sm">Loading...</p>
          )}

          {!loading && applications.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p>No applications found</p>
              <p className="text-xs mt-1">
                Create an application from the job detail page.
              </p>
            </div>
          )}

          <div className="space-y-3">
            {applications.map((app) => (
              <Card key={app.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-base text-muted-foreground font-normal">
                        Application{" "}
                        <span className="text-foreground font-medium">
                          {app.id.slice(0, 8)}…
                        </span>
                      </CardTitle>
                      <div className="flex items-center gap-3 mt-1 flex-wrap">
                        <Badge variant={STATUS_COLORS[app.status] ?? "outline"}>
                          {STATUS_LABELS[app.status] ?? app.status}
                        </Badge>
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(app.created_at)}
                        </span>
                        {app.sent_at && (
                          <span className="text-xs text-muted-foreground">
                            Sent {formatDate(app.sent_at)}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div className="flex gap-2 shrink-0">
                      {app.status === "approved" && (
                        <Button
                          size="sm"
                          onClick={() => handleSend(app.id)}
                          disabled={sendingId === app.id}
                        >
                          <Send className="h-3 w-3 mr-1" />
                          {sendingId === app.id ? "Sending..." : "Send"}
                        </Button>
                      )}
                      {(app.status === "sent" ||
                        app.status === "replied" ||
                        app.status === "interviewing") && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            router.push(
                              `/conversations?application_id=${app.id}`
                            )
                          }
                        >
                          <MessageSquare className="h-3 w-3 mr-1" />
                          View Chat
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>

                {app.draft_message && (
                  <CardContent>
                    <p className="text-xs font-medium text-muted-foreground mb-1">
                      {app.final_message ? "Final message" : "Draft message"}
                    </p>
                    <p className="text-sm bg-muted/50 rounded-md p-3 whitespace-pre-wrap line-clamp-3">
                      {app.final_message || app.draft_message}
                    </p>
                  </CardContent>
                )}
              </Card>
            ))}
          </div>

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
                Page {Math.floor(skip / limit) + 1} of{" "}
                {Math.ceil(total / limit)}
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

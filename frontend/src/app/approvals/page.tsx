"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle, XCircle, Edit2, Clock } from "lucide-react";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import { formatDate } from "@/lib/utils";
import type { ApprovalQueue, ApprovalQueueListResponse } from "@/types";

type StatusFilter = "pending" | "approved" | "rejected" | "all";

export default function ApprovalsPage() {
  const router = useRouter();
  const [items, setItems] = useState<ApprovalQueue[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<StatusFilter>("pending");

  // Per-item edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editMessage, setEditMessage] = useState("");
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectNotes, setRejectNotes] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    fetchApprovals();
  }, [router, filter]);

  const fetchApprovals = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "50" });
      if (filter !== "all") params.set("status", filter);
      const data = await api.get<ApprovalQueueListResponse>(
        `/api/v1/approvals/?${params}`
      );
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load approvals");
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approval: ApprovalQueue, message?: string) => {
    setActionLoading(approval.id);
    try {
      await api.post(`/api/v1/approvals/${approval.id}/approve`, {
        message: message || null,
      });
      toast.success(`Approved: ${approval.payload.job_title} @ ${approval.payload.company}`);
      setEditingId(null);
      fetchApprovals();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (approval: ApprovalQueue) => {
    setActionLoading(approval.id);
    try {
      await api.post(`/api/v1/approvals/${approval.id}/reject`, {
        notes: rejectNotes || null,
      });
      toast.success(`Rejected: ${approval.payload.job_title} @ ${approval.payload.company}`);
      setRejectingId(null);
      setRejectNotes("");
      fetchApprovals();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setActionLoading(null);
    }
  };

  const scoreColor = (score: number | null) => {
    if (score === null) return "text-muted-foreground";
    if (score >= 70) return "text-green-600 font-bold";
    if (score >= 40) return "text-yellow-600 font-bold";
    return "text-red-600 font-bold";
  };

  const statusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      pending: "default",
      approved: "secondary",
      rejected: "destructive",
      expired: "outline",
    };
    return <Badge variant={variants[status] ?? "outline"}>{status}</Badge>;
  };

  const tabs: { label: string; value: StatusFilter }[] = [
    { label: "Pending", value: "pending" },
    { label: "Approved", value: "approved" },
    { label: "Rejected", value: "rejected" },
    { label: "All", value: "all" },
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Approvals" />
        <main className="flex-1 p-6 space-y-4">
          {/* Filter tabs */}
          <div className="flex gap-2 border-b border-border pb-2">
            {tabs.map((tab) => (
              <button
                key={tab.value}
                onClick={() => setFilter(tab.value)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  filter === tab.value
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`}
              >
                {tab.label}
              </button>
            ))}
            <span className="ml-auto text-sm text-muted-foreground self-center">
              {total} item{total !== 1 ? "s" : ""}
            </span>
          </div>

          {loading && <p className="text-muted-foreground text-sm">Loading...</p>}

          {!loading && items.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <CheckCircle className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p>No {filter !== "all" ? filter : ""} approvals</p>
            </div>
          )}

          <div className="space-y-3">
            {items.map((item) => (
              <Card key={item.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-base">
                        {item.payload.job_title}
                        <span className="text-muted-foreground font-normal ml-2">
                          @ {item.payload.company}
                        </span>
                      </CardTitle>
                      <div className="flex items-center gap-3 mt-1">
                        {statusBadge(item.status)}
                        {item.payload.score !== null && (
                          <span className={`text-sm ${scoreColor(item.payload.score)}`}>
                            Score: {item.payload.score.toFixed(0)}/100
                          </span>
                        )}
                        <span className="text-xs text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(item.created_at)}
                        </span>
                      </div>
                    </div>
                    {item.status === "pending" && (
                      <div className="flex gap-2 shrink-0">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setEditingId(editingId === item.id ? null : item.id);
                            setEditMessage(item.payload.message);
                            setRejectingId(null);
                          }}
                        >
                          <Edit2 className="h-3 w-3 mr-1" />
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => handleApprove(item)}
                          disabled={actionLoading === item.id}
                        >
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => {
                            setRejectingId(rejectingId === item.id ? null : item.id);
                            setEditingId(null);
                          }}
                          disabled={actionLoading === item.id}
                        >
                          <XCircle className="h-3 w-3 mr-1" />
                          Reject
                        </Button>
                      </div>
                    )}
                  </div>
                </CardHeader>

                <CardContent className="space-y-3">
                  {/* Draft message */}
                  {item.status !== "pending" || (editingId !== item.id) ? (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        {item.status === "approved" ? "Final message" : "Draft message"}
                      </p>
                      <p className="text-sm bg-muted/50 rounded-md p-3 whitespace-pre-wrap">
                        {item.payload.message || "(no draft)"}
                      </p>
                    </div>
                  ) : null}

                  {/* Edit & approve inline */}
                  {editingId === item.id && (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">Edit message before approving</p>
                      <textarea
                        value={editMessage}
                        onChange={(e) => setEditMessage(e.target.value)}
                        className="w-full min-h-[100px] rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleApprove(item, editMessage)}
                          disabled={actionLoading === item.id}
                        >
                          <CheckCircle className="h-3 w-3 mr-1" />
                          Approve with edits
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => setEditingId(null)}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Reject inline */}
                  {rejectingId === item.id && (
                    <div className="space-y-2">
                      <p className="text-xs font-medium text-muted-foreground">Rejection reason (optional)</p>
                      <input
                        type="text"
                        value={rejectNotes}
                        onChange={(e) => setRejectNotes(e.target.value)}
                        placeholder="Not a good fit, salary too low..."
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleReject(item)}
                          disabled={actionLoading === item.id}
                        >
                          Confirm Reject
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => { setRejectingId(null); setRejectNotes(""); }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Reviewed info */}
                  {item.reviewed_at && (
                    <p className="text-xs text-muted-foreground">
                      Reviewed {formatDate(item.reviewed_at)}
                      {item.reviewer_notes && ` — "${item.reviewer_notes}"`}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}

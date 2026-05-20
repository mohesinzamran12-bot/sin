"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MessageSquare, RefreshCw, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import { formatDate } from "@/lib/utils";
import type {
  Conversation,
  ConversationListResponse,
  Application,
  ApplicationListResponse,
} from "@/types";

type Tab = "all" | "needs_reply";

export default function ConversationsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>("all");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [applications, setApplications] = useState<Record<string, Application>>({});
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Read application_id filter from query string
  const applicationIdFilter = searchParams.get("application_id");

  const fetchConversations = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: "200" });
      if (tab === "needs_reply") params.set("reply_needed", "true");
      if (applicationIdFilter) params.set("application_id", applicationIdFilter);

      const data = await api.get<ConversationListResponse>(
        `/api/v1/conversations/?${params}`
      );
      setConversations(data.items);
      setTotal(data.total);

      // Fetch applications for the conversation group headers
      if (data.items.length > 0) {
        const appIds = [...new Set(data.items.map((c) => c.application_id))];
        const appMap: Record<string, Application> = {};
        await Promise.all(
          appIds.map(async (id) => {
            try {
              const app = await api.get<Application>(`/api/v1/applications/${id}`);
              appMap[id] = app;
            } catch {
              // ignore — group still shows without metadata
            }
          })
        );
        setApplications(appMap);
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to load conversations");
    } finally {
      setLoading(false);
    }
  }, [tab, applicationIdFilter]);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    fetchConversations();
  }, [router, fetchConversations]);

  const handleSync = async () => {
    // Get candidateId from localStorage (set when profile is created/loaded)
    const candidateId = localStorage.getItem("candidateId");
    if (!candidateId) {
      toast.error("No candidate profile found. Please create your profile first.");
      return;
    }
    setSyncing(true);
    try {
      const data = await api.post<{ task_id: string; status: string }>(
        "/api/v1/conversations/sync",
        { candidate_id: candidateId }
      );
      toast.success(`Sync queued (task ${data.task_id})`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  // Group conversations by application_id
  const grouped = conversations.reduce<Record<string, Conversation[]>>(
    (acc, conv) => {
      if (!acc[conv.application_id]) acc[conv.application_id] = [];
      acc[conv.application_id].push(conv);
      return acc;
    },
    {}
  );

  const tabs: { label: string; value: Tab }[] = [
    { label: "All", value: "all" },
    { label: "Needs Reply", value: "needs_reply" },
  ];

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Conversations" />
        <main className="flex-1 p-6 space-y-4">
          {/* Tab bar + sync button */}
          <div className="flex items-center gap-2 border-b border-border pb-2">
            {tabs.map((t) => (
              <button
                key={t.value}
                onClick={() => setTab(t.value)}
                className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                  tab === t.value
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`}
              >
                {t.label}
              </button>
            ))}
            <span className="ml-auto text-sm text-muted-foreground self-center">
              {total} message{total !== 1 ? "s" : ""}
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={handleSync}
              disabled={syncing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? "animate-spin" : ""}`} />
              Sync
            </Button>
          </div>

          {loading && (
            <p className="text-muted-foreground text-sm">Loading...</p>
          )}

          {!loading && Object.keys(grouped).length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-30" />
              <p>No conversations yet</p>
              <p className="text-xs mt-1">
                {tab === "needs_reply"
                  ? "No messages need a reply right now."
                  : "Send an application to start a conversation."}
              </p>
            </div>
          )}

          {/* Conversation groups */}
          <div className="space-y-6">
            {Object.entries(grouped).map(([appId, messages]) => {
              const app = applications[appId];
              return (
                <Card key={appId}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-base flex items-center justify-between">
                      <span>
                        {app ? (
                          <>
                            <span className="font-semibold">{app.job_id}</span>
                            <span className="text-muted-foreground font-normal ml-2 text-sm">
                              app {appId.slice(0, 8)}…
                            </span>
                          </>
                        ) : (
                          <span className="text-muted-foreground text-sm">
                            Application {appId.slice(0, 8)}…
                          </span>
                        )}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {messages.length} message{messages.length !== 1 ? "s" : ""}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {messages.map((msg) => (
                      <div key={msg.id} className="space-y-1">
                        {/* Chat bubble */}
                        <div
                          className={`flex ${
                            msg.direction === "outbound" ? "justify-end" : "justify-start"
                          }`}
                        >
                          <div
                            className={`max-w-[75%] rounded-lg px-4 py-2 text-sm ${
                              msg.direction === "outbound"
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted text-foreground"
                            }`}
                          >
                            {msg.sender_name && (
                              <p className="text-xs font-medium mb-1 opacity-70">
                                {msg.sender_name}
                              </p>
                            )}
                            <p className="whitespace-pre-wrap">{msg.body}</p>
                            <p className="text-xs mt-1 opacity-60 text-right">
                              {formatDate(msg.sent_at)}
                            </p>
                          </div>
                        </div>

                        {/* Draft reply box for inbound messages that need a reply */}
                        {msg.reply_needed && (
                          <div className="ml-4 border border-yellow-300 bg-yellow-50 dark:bg-yellow-950/20 dark:border-yellow-800 rounded-lg p-3 space-y-2">
                            <div className="flex items-center gap-2 text-yellow-700 dark:text-yellow-400">
                              <AlertCircle className="h-4 w-4 shrink-0" />
                              <span className="text-xs font-semibold">Reply needed</span>
                            </div>
                            {msg.draft_reply && (
                              <>
                                <p className="text-xs text-muted-foreground font-medium">
                                  Draft reply (AI-generated):
                                </p>
                                <p className="text-sm bg-background rounded p-2 whitespace-pre-wrap border border-border">
                                  {msg.draft_reply}
                                </p>
                              </>
                            )}
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => router.push("/approvals")}
                              className="text-xs"
                            >
                              Approve Reply in Approvals
                            </Button>
                          </div>
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </main>
      </div>
    </div>
  );
}

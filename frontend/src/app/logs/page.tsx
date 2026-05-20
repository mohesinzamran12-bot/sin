"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import { formatDate } from "@/lib/utils";
import type { AIAuditLogListResponse, AIAuditLog } from "@/types";

const EVENT_COLORS: Record<string, "default" | "secondary" | "outline"> = {
  score: "default",
  draft_message: "secondary",
  draft_reply: "secondary",
  classify: "outline",
};

const COST_PER_M_INPUT = 3.0;
const COST_PER_M_OUTPUT = 15.0;

function estimateCost(input: number, output: number): string {
  const cost = (input * COST_PER_M_INPUT + output * COST_PER_M_OUTPUT) / 1_000_000;
  return cost < 0.0001 ? "<$0.0001" : `$${cost.toFixed(4)}`;
}

type SystemEvent = {
  id: string;
  level: string;
  source: string;
  message: string;
  event_metadata: Record<string, unknown> | null;
  created_at: string;
};

type SystemEventListResponse = {
  items: SystemEvent[];
  total: number;
  skip: number;
  limit: number;
};

const LEVEL_BADGE: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  info: "default",
  warn: "secondary",
  warning: "secondary",
  error: "destructive",
};

function LevelBadge({ level }: { level: string }) {
  const variant = LEVEL_BADGE[level.toLowerCase()] ?? "outline";
  const label = level.toUpperCase();
  // Apply color classes manually since shadcn Badge uses variant
  const colorClass =
    level.toLowerCase() === "info"
      ? "bg-blue-100 text-blue-800 border-blue-200"
      : level.toLowerCase() === "warn" || level.toLowerCase() === "warning"
      ? "bg-yellow-100 text-yellow-800 border-yellow-200"
      : level.toLowerCase() === "error"
      ? "bg-red-100 text-red-800 border-red-200"
      : "";
  return (
    <Badge variant={variant} className={colorClass}>
      {label}
    </Badge>
  );
}

function MetadataSnippet({ data }: { data: Record<string, unknown> | null }) {
  const [open, setOpen] = useState(false);
  if (!data || Object.keys(data).length === 0) return null;
  return (
    <span className="ml-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="text-xs text-blue-600 underline hover:text-blue-800"
      >
        {open ? "hide" : "details"}
      </button>
      {open && (
        <pre className="mt-1 text-xs bg-muted rounded p-2 max-w-xs overflow-auto whitespace-pre-wrap">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </span>
  );
}

export default function LogsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"ai" | "system">("ai");

  // AI Audit state
  const [logs, setLogs] = useState<AIAuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [loading, setLoading] = useState(true);
  const limit = 20;

  // System Events state
  const [sysEvents, setSysEvents] = useState<SystemEvent[]>([]);
  const [sysTotal, setSysTotal] = useState(0);
  const [sysSkip, setSysSkip] = useState(0);
  const [sysLoading, setSysLoading] = useState(false);
  const sysLimit = 20;

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    fetchLogs();
  }, [router, skip]);

  useEffect(() => {
    if (activeTab === "system") {
      fetchSysEvents();
    }
  }, [activeTab, sysSkip]);

  async function fetchLogs() {
    setLoading(true);
    try {
      const data = await api.get<AIAuditLogListResponse>(
        `/api/v1/logs/ai?skip=${skip}&limit=${limit}`
      );
      setLogs(data.items);
      setTotal(data.total);
    } catch {
    } finally {
      setLoading(false);
    }
  }

  async function fetchSysEvents() {
    setSysLoading(true);
    try {
      const data = await api.get<SystemEventListResponse>(
        `/api/v1/logs/system?skip=${sysSkip}&limit=${sysLimit}`
      );
      setSysEvents(data.items);
      setSysTotal(data.total);
    } catch {
    } finally {
      setSysLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Logs" />
        <main className="flex-1 p-6 space-y-4">

          {/* Tab switcher */}
          <div className="flex gap-2 border-b pb-0">
            <button
              onClick={() => setActiveTab("ai")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "ai"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              AI Audit
            </button>
            <button
              onClick={() => setActiveTab("system")}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === "system"
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              System Events
            </button>
          </div>

          {/* AI Audit Tab */}
          {activeTab === "ai" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">AI Audit Log</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <p className="text-sm text-muted-foreground">Loading…</p>
                ) : logs.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No AI calls logged yet. Score a job or create an application to see entries here.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-muted-foreground">
                          <th className="pb-2 pr-4 font-medium">Time</th>
                          <th className="pb-2 pr-4 font-medium">Event</th>
                          <th className="pb-2 pr-4 font-medium">Model</th>
                          <th className="pb-2 pr-4 font-medium text-right">Tokens In</th>
                          <th className="pb-2 pr-4 font-medium text-right">Tokens Out</th>
                          <th className="pb-2 pr-4 font-medium text-right">Est. Cost</th>
                          <th className="pb-2 font-medium">Summary</th>
                        </tr>
                      </thead>
                      <tbody>
                        {logs.map((log) => (
                          <tr key={log.id} className="border-b last:border-0 hover:bg-muted/30">
                            <td className="py-2 pr-4 text-muted-foreground whitespace-nowrap">
                              {formatDate(log.created_at)}
                            </td>
                            <td className="py-2 pr-4">
                              <Badge variant={EVENT_COLORS[log.event_type] ?? "outline"}>
                                {log.event_type}
                              </Badge>
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground text-xs">
                              {log.model}
                            </td>
                            <td className="py-2 pr-4 text-right tabular-nums">
                              {log.input_tokens.toLocaleString()}
                            </td>
                            <td className="py-2 pr-4 text-right tabular-nums">
                              {log.output_tokens.toLocaleString()}
                            </td>
                            <td className="py-2 pr-4 text-right tabular-nums text-muted-foreground">
                              {estimateCost(log.input_tokens, log.output_tokens)}
                            </td>
                            <td className="py-2 max-w-xs truncate text-muted-foreground">
                              {log.result_summary}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {total > limit && (
                  <div className="flex items-center justify-between mt-4 text-sm">
                    <span className="text-muted-foreground">
                      {skip + 1}–{Math.min(skip + limit, total)} of {total}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline" size="sm"
                        disabled={skip === 0}
                        onClick={() => setSkip(Math.max(0, skip - limit))}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline" size="sm"
                        disabled={skip + limit >= total}
                        onClick={() => setSkip(skip + limit)}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* System Events Tab */}
          {activeTab === "system" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">System Events</CardTitle>
              </CardHeader>
              <CardContent>
                {sysLoading ? (
                  <p className="text-sm text-muted-foreground">Loading…</p>
                ) : sysEvents.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    No system events logged yet.
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-left text-muted-foreground">
                          <th className="pb-2 pr-4 font-medium">Time</th>
                          <th className="pb-2 pr-4 font-medium">Level</th>
                          <th className="pb-2 pr-4 font-medium">Source</th>
                          <th className="pb-2 font-medium">Message</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sysEvents.map((event) => (
                          <tr key={event.id} className="border-b last:border-0 hover:bg-muted/30">
                            <td className="py-2 pr-4 text-muted-foreground whitespace-nowrap">
                              {formatDate(event.created_at)}
                            </td>
                            <td className="py-2 pr-4">
                              <LevelBadge level={event.level} />
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground text-xs whitespace-nowrap">
                              {event.source}
                            </td>
                            <td className="py-2 text-sm">
                              <span>{event.message}</span>
                              <MetadataSnippet data={event.event_metadata} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {sysTotal > sysLimit && (
                  <div className="flex items-center justify-between mt-4 text-sm">
                    <span className="text-muted-foreground">
                      {sysSkip + 1}–{Math.min(sysSkip + sysLimit, sysTotal)} of {sysTotal}
                    </span>
                    <div className="flex gap-2">
                      <Button
                        variant="outline" size="sm"
                        disabled={sysSkip === 0}
                        onClick={() => setSysSkip(Math.max(0, sysSkip - sysLimit))}
                      >
                        Previous
                      </Button>
                      <Button
                        variant="outline" size="sm"
                        disabled={sysSkip + sysLimit >= sysTotal}
                        onClick={() => setSysSkip(sysSkip + sysLimit)}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

        </main>
      </div>
    </div>
  );
}

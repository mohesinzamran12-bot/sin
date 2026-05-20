"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import type { NotificationSettings, BrowserSession, CollectionStatus } from "@/types";

export default function SettingsPage() {
  const router = useRouter();
  const [notifSettings, setNotifSettings] = useState<NotificationSettings | null>(null);
  const [testing, setTesting] = useState(false);

  // Browser session state
  const [sessions, setSessions] = useState<BrowserSession[]>([]);
  const [collectionStatus, setCollectionStatus] = useState<CollectionStatus | null>(null);
  const [showAddSession, setShowAddSession] = useState(false);
  const [cookiesJson, setCookiesJson] = useState("");
  const [userAgent, setUserAgent] = useState("");
  const [addingSession, setAddingSession] = useState(false);

  const fetchSessionData = async () => {
    try {
      const [sessData, statusData] = await Promise.all([
        api.get<BrowserSession[]>("/api/v1/collection/sessions"),
        api.get<CollectionStatus>("/api/v1/collection/status"),
      ]);
      setSessions(sessData);
      setCollectionStatus(statusData);
    } catch {
      // silently ignore
    }
  };

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    api.get<NotificationSettings>("/api/v1/notifications/settings")
      .then(setNotifSettings)
      .catch(() => {});
    fetchSessionData();
  }, [router]);

  const handleTestNotification = async () => {
    setTesting(true);
    try {
      const result = await api.post<{ ok: boolean; error: string | null }>(
        "/api/v1/notifications/test",
        {}
      );
      if (result.ok) {
        toast.success("Test notification sent!");
      } else {
        toast.error(result.error || "Failed to send test notification");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Request failed");
    } finally {
      setTesting(false);
    }
  };

  const handleAddSession = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddingSession(true);
    try {
      let cookies: object[];
      try {
        cookies = JSON.parse(cookiesJson);
        if (!Array.isArray(cookies)) throw new Error("Must be a JSON array");
      } catch {
        toast.error("Invalid JSON — paste a cookie array from your browser");
        setAddingSession(false);
        return;
      }
      await api.post("/api/v1/collection/sessions", {
        cookies,
        user_agent: userAgent,
        platform: "boss_zhipin",
      });
      toast.success("Session added successfully");
      setCookiesJson("");
      setUserAgent("");
      setShowAddSession(false);
      await fetchSessionData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add session");
    } finally {
      setAddingSession(false);
    }
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await api.delete(`/api/v1/collection/sessions/${sessionId}`);
      toast.success("Session removed");
      await fetchSessionData();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to delete session");
    }
  };

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header title="Settings" />
        <main className="flex-1 p-6 max-w-2xl space-y-6">
          {/* Telegram */}
          <Card>
            <CardHeader>
              <CardTitle>Telegram Notifications</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium">Status:</span>
                {notifSettings?.telegram_configured ? (
                  <Badge variant="default">Configured</Badge>
                ) : (
                  <Badge variant="secondary">Not configured</Badge>
                )}
              </div>

              {notifSettings?.telegram_chat_id && (
                <div className="text-sm">
                  <span className="font-medium">Chat ID:</span>{" "}
                  <code className="bg-muted px-1 rounded">{notifSettings.telegram_chat_id}</code>
                </div>
              )}

              {notifSettings?.telegram_configured ? (
                <Button onClick={handleTestNotification} disabled={testing} size="sm">
                  {testing ? "Sending..." : "Send Test Message"}
                </Button>
              ) : (
                <div className="rounded-md bg-muted p-4 text-sm space-y-2">
                  <p className="font-medium">How to configure Telegram:</p>
                  <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                    <li>Create a bot via @BotFather on Telegram</li>
                    <li>Copy the bot token</li>
                    <li>Send a message to your bot to get your chat ID</li>
                    <li>Set in <code className="bg-background px-1 rounded">.env</code>:</li>
                  </ol>
                  <pre className="bg-background rounded p-2 text-xs mt-2">
{`TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id`}
                  </pre>
                  <p className="text-muted-foreground">Restart the backend after updating .env.</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Rate limits (informational) */}
          <Card>
            <CardHeader>
              <CardTitle>Rate Limits</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                These safety limits are set in <code className="bg-muted px-1 rounded">.env</code>{" "}
                and enforced server-side. They cannot be changed from the UI.
              </p>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-muted/50 rounded p-3">
                  <p className="font-medium">Max Applications/Day</p>
                  <p className="text-2xl font-bold mt-1">10</p>
                </div>
                <div className="bg-muted/50 rounded p-3">
                  <p className="font-medium">Max Jobs Collected/Run</p>
                  <p className="text-2xl font-bold mt-1">30</p>
                </div>
                <div className="bg-muted/50 rounded p-3">
                  <p className="font-medium">Collection Runs/Day</p>
                  <p className="text-2xl font-bold mt-1">4</p>
                </div>
                <div className="bg-muted/50 rounded p-3">
                  <p className="font-medium">Claude Daily Budget</p>
                  <p className="text-2xl font-bold mt-1">$5</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Browser Session (BOSS Zhipin) */}
          <Card>
            <CardHeader>
              <CardTitle>Browser Session (BOSS Zhipin)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Collection status */}
              {collectionStatus && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-muted/50 rounded p-3">
                    <p className="font-medium">Runs Today</p>
                    <p className="text-2xl font-bold mt-1">
                      {collectionStatus.runs_today} / {collectionStatus.max_runs_per_day}
                    </p>
                  </div>
                  <div className="bg-muted/50 rounded p-3">
                    <p className="font-medium">Session Status</p>
                    <div className="mt-1">
                      {collectionStatus.has_valid_session ? (
                        <Badge variant="default">Valid</Badge>
                      ) : (
                        <Badge variant="destructive">No valid session</Badge>
                      )}
                    </div>
                  </div>
                  {collectionStatus.last_run_at && (
                    <div className="bg-muted/50 rounded p-3 col-span-2">
                      <p className="font-medium">Last Run</p>
                      <p className="text-muted-foreground mt-1">
                        {new Date(collectionStatus.last_run_at).toLocaleString()}
                        {collectionStatus.last_run_result && (
                          <span className="ml-2">
                            — {collectionStatus.last_run_result.collected} collected,{" "}
                            {collectionStatus.last_run_result.new} new
                          </span>
                        )}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Existing sessions */}
              {sessions.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium">Saved Sessions</p>
                  {sessions.map((s) => (
                    <div
                      key={s.id}
                      className="flex items-center justify-between rounded border p-3 text-sm"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{s.platform}</span>
                          {s.is_valid ? (
                            <Badge variant="default" className="text-xs">Valid</Badge>
                          ) : (
                            <Badge variant="destructive" className="text-xs">Invalid</Badge>
                          )}
                        </div>
                        <p className="text-muted-foreground text-xs">
                          Created: {new Date(s.created_at).toLocaleDateString()}
                          {s.last_used_at && (
                            <span> &middot; Last used: {new Date(s.last_used_at).toLocaleDateString()}</span>
                          )}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => handleDeleteSession(s.id)}
                      >
                        Remove
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add session form */}
              {showAddSession ? (
                <form onSubmit={handleAddSession} className="space-y-4 rounded border p-4">
                  <div className="rounded-md bg-muted p-4 text-sm space-y-2">
                    <p className="font-medium">How to export BOSS Zhipin cookies:</p>
                    <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                      <li>Log into boss.zhipin.com in your browser</li>
                      <li>Open DevTools (F12) → Application → Cookies → www.zhipin.com</li>
                      <li>
                        Use a browser extension like &ldquo;Cookie Editor&rdquo; → Export as JSON
                        (or manually copy the cookie values)
                      </li>
                      <li>Paste the JSON array below</li>
                    </ol>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="cookies-json">Cookies JSON *</Label>
                    <textarea
                      id="cookies-json"
                      value={cookiesJson}
                      onChange={(e) => setCookiesJson(e.target.value)}
                      className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                      placeholder='[{"name": "wt2", "value": "...", "domain": ".zhipin.com", "path": "/"}]'
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="user-agent">User-Agent (optional)</Label>
                    <Input
                      id="user-agent"
                      value={userAgent}
                      onChange={(e) => setUserAgent(e.target.value)}
                      placeholder="Leave blank to use default"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button type="submit" disabled={addingSession}>
                      {addingSession ? "Saving..." : "Save Session"}
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setShowAddSession(false);
                        setCookiesJson("");
                        setUserAgent("");
                      }}
                    >
                      Cancel
                    </Button>
                  </div>
                </form>
              ) : (
                <Button onClick={() => setShowAddSession(true)} size="sm">
                  Add Session
                </Button>
              )}
            </CardContent>
          </Card>
        </main>
      </div>
    </div>
  );
}

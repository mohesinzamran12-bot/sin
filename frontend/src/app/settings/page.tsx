"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api-client";
import { isAuthenticated } from "@/lib/auth";
import type { NotificationSettings } from "@/types";

export default function SettingsPage() {
  const router = useRouter();
  const [notifSettings, setNotifSettings] = useState<NotificationSettings | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    api.get<NotificationSettings>("/api/v1/notifications/settings")
      .then(setNotifSettings)
      .catch(() => {});
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
        </main>
      </div>
    </div>
  );
}

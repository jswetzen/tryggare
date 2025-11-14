"use client";

import { api } from "~/trpc/react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Clock, Users } from "lucide-react";
import { useState } from "react";

export function ActiveSessions() {
  const t = useTranslations("dashboard");
  const tSession = useTranslations("session");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const { data: sessions, isLoading, refetch } = api.session.getActive.useQuery();
  const activateMutation = api.session.activate.useMutation();
  const deactivateMutation = api.session.deactivate.useMutation();

  const handleToggleSession = async (sessionId: string, isActive: boolean) => {
    setActionLoading(sessionId);
    try {
      if (isActive) {
        await deactivateMutation.mutateAsync({ id: sessionId });
      } else {
        await activateMutation.mutateAsync({ id: sessionId });
      }
      await refetch();
    } catch (error) {
      console.error("Failed to toggle session:", error);
    } finally {
      setActionLoading(null);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-24 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!sessions || sessions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("activeSessions.title")}</CardTitle>
          <CardDescription>{t("activeSessions.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {t("activeSessions.noSessions")}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("activeSessions.title")}</CardTitle>
        <CardDescription>{t("activeSessions.description")}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {sessions.map((session) => (
            <div
              key={session.id}
              className="flex items-center justify-between p-4 border rounded-lg"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{session.name}</h3>
                  <Badge variant={session.isActive ? "default" : "secondary"}>
                    {session.isActive ? tSession("active") : tSession("inactive")}
                  </Badge>
                </div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4" />
                    {new Date(session.startTime).toLocaleTimeString()} -{" "}
                    {new Date(session.endTime).toLocaleTimeString()}
                  </div>
                  <div className="flex items-center gap-1">
                    <Users className="h-4 w-4" />
                    {session.event.name}
                  </div>
                </div>
              </div>
              <Button
                size="sm"
                variant={session.isActive ? "outline" : "default"}
                onClick={() => handleToggleSession(session.id, session.isActive)}
                disabled={actionLoading === session.id}
              >
                {actionLoading === session.id
                  ? tSession("loading")
                  : session.isActive
                  ? tSession("endSession")
                  : tSession("startSession")}
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

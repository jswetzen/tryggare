"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useTranslations } from "next-intl";
import { api } from "~/trpc/react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";

interface SessionSelectorProps {
  selectedSessionId?: string;
  onSelectSession: (sessionId: string) => void;
}

export function SessionSelector({ selectedSessionId, onSelectSession }: SessionSelectorProps) {
  const t = useTranslations("checkIn");
  const tSession = useTranslations("session");

  const { data: sessions, isLoading } = api.session.getActive.useQuery();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (!sessions || sessions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("selectSession")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            {t("noActiveSession")}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("selectSession")}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => onSelectSession(session.id)}
              className={`w-full rounded-lg border p-4 text-left transition-colors hover:bg-accent ${
                selectedSessionId === session.id ? "border-primary bg-accent" : ""
              }`}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="font-medium">{session.name}</div>
                  <Badge variant="secondary">{tSession("active")}</Badge>
                </div>
                <div className="text-sm text-muted-foreground">
                  {session.event.name} • {format(new Date(session.startTime), "PPp")}
                </div>
                {session.requiresTicket && (
                  <div className="text-xs text-muted-foreground">
                    {tSession("requiresTicket")}
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

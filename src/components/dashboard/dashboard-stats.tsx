"use client";

import { api } from "~/trpc/react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function DashboardStats() {
  const t = useTranslations("dashboard");

  // Fetch active sessions
  const { data: activeSessions, isLoading: sessionsLoading } = api.session.getActive.useQuery();

  // Fetch current check-ins across all sessions
  const { data: currentCheckIns, isLoading: checkInsLoading } = api.checkIn.getCurrentCheckIns.useQuery({});

  // Count unique checked-in children
  const checkedInCount = currentCheckIns?.length || 0;
  const activeSessionCount = activeSessions?.length || 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("stats.title")}</CardTitle>
        <CardDescription>
          {t("stats.description")}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            {checkInsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{checkedInCount}</div>
            )}
            <p className="text-xs text-muted-foreground">{t("stats.checkedIn")}</p>
          </div>
          <div>
            {sessionsLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{activeSessionCount}</div>
            )}
            <p className="text-xs text-muted-foreground">{t("stats.activeSessions")}</p>
          </div>
          <div>
            <div className="text-2xl font-bold">--</div>
            <p className="text-xs text-muted-foreground">{t("stats.totalFamilies")}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

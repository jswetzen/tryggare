import { auth } from "~/lib/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { DashboardStats } from "~/components/dashboard/dashboard-stats";
import { ActiveSessions } from "~/components/dashboard/active-sessions";

// Dashboard page with i18n support
export default async function DashboardPage() {
  const session = await auth();
  const t = await getTranslations("dashboard");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
        <p className="text-muted-foreground">
          {t("welcome", { name: session?.user?.name || "User" })}
        </p>
      </div>

      {/* Active Sessions */}
      <ActiveSessions />

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>{t("checkInCard.title")}</CardTitle>
            <CardDescription>
              {t("checkInCard.description")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/check-in">{t("checkInCard.button")}</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("checkOutCard.title")}</CardTitle>
            <CardDescription>
              {t("checkOutCard.description")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/check-out">{t("checkOutCard.button")}</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{t("adminCard.title")}</CardTitle>
            <CardDescription>
              {t("adminCard.description")}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="secondary">
              <Link href="/admin">{t("adminCard.button")}</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Stats */}
      <DashboardStats />
    </div>
  );
}

import { auth } from "~/lib/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default async function DashboardPage() {
  const session = await auth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back, {session?.user?.name}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Check-In Station</CardTitle>
            <CardDescription>
              Check children into sessions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/check-in">Start Check-In</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Check-Out Station</CardTitle>
            <CardDescription>
              Check children out of sessions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/check-out">Start Check-Out</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Admin Management</CardTitle>
            <CardDescription>
              Manage families, sessions, and users
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="secondary">
              <Link href="/admin">Admin Panel</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick Stats</CardTitle>
          <CardDescription>
            System overview (Phase 2: will display real data)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <div className="text-2xl font-bold">--</div>
              <p className="text-xs text-muted-foreground">Children Checked In</p>
            </div>
            <div>
              <div className="text-2xl font-bold">--</div>
              <p className="text-xs text-muted-foreground">Active Sessions</p>
            </div>
            <div>
              <div className="text-2xl font-bold">--</div>
              <p className="text-xs text-muted-foreground">Total Families</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

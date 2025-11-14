"use client";

import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Calendar, Users, UsersRound, Database } from "lucide-react";

export default function AdminPage() {
  const t = useTranslations("dashboard");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Admin Management</h1>
        <p className="text-muted-foreground">
          Manage sessions, users, families, and data
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <Calendar className="h-8 w-8 text-primary" />
            <CardTitle>Sessions</CardTitle>
            <CardDescription>
              Manage events and sessions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/admin/sessions">Manage Sessions</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Users className="h-8 w-8 text-primary" />
            <CardTitle>Staff Users</CardTitle>
            <CardDescription>
              Manage admin users and permissions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/admin/users">Manage Users</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <UsersRound className="h-8 w-8 text-primary" />
            <CardTitle>Families</CardTitle>
            <CardDescription>
              Search, edit, and manage family records
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link href="/admin/families">Manage Families</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Database className="h-8 w-8 text-primary" />
            <CardTitle>Data Management</CardTitle>
            <CardDescription>
              GDPR compliance and data review
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full" variant="secondary">
              <Link href="/admin/data">Review Data</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

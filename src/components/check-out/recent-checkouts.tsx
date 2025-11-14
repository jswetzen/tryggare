"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useTranslations } from "next-intl";
import { api } from "~/trpc/react";
import { Skeleton } from "@/components/ui/skeleton";
import { format, formatDistanceToNow } from "date-fns";
import { Undo2 } from "lucide-react";
import { toast } from "sonner";

export function RecentCheckouts() {
  const t = useTranslations("checkOut");
  const tCommon = useTranslations("common");

  const { data: recentCheckouts, isLoading, refetch } = api.checkOut.getRecent.useQuery({ limit: 10 });

  const undoMutation = api.checkOut.undo.useMutation({
    onSuccess: () => {
      toast.success("Check-out undone successfully");
      refetch();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleUndo = async (checkInRecordId: string) => {
    await undoMutation.mutateAsync({ checkInRecordId });
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!recentCheckouts || recentCheckouts.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Check-Outs</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            No recent check-outs in the last 24 hours
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Check-Outs</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {recentCheckouts.map((checkout) => (
            <div
              key={checkout.id}
              className="flex items-start justify-between rounded-lg border p-3"
            >
              <div className="space-y-1">
                <div className="font-medium">
                  {checkout.child.firstName} {checkout.child.lastName}
                </div>
                <div className="text-sm text-muted-foreground">
                  {checkout.session.name}
                </div>
                <div className="text-xs text-muted-foreground">
                  Checked out {formatDistanceToNow(new Date(checkout.checkOutTime!), { addSuffix: true })}
                  {checkout.pickedUpBy && (
                    <span> • Picked up by: {checkout.pickedUpBy}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {checkout.canUndo ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleUndo(checkout.id)}
                    disabled={undoMutation.isPending}
                  >
                    <Undo2 className="mr-1 h-4 w-4" />
                    {t("undoButton")}
                  </Button>
                ) : (
                  <Badge variant="outline" className="text-xs">
                    Cannot undo
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

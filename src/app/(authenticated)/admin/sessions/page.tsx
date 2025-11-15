"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { SessionModal } from "~/components/admin/session-modal";
import { api } from "~/trpc/react";
import { format } from "date-fns";
import { Play, Square, Pencil, Trash2, Plus } from "lucide-react";
import { toast } from "sonner";

export default function SessionsPage() {
  const t = useTranslations("admin");
  const tCommon = useTranslations("common");

  const [filter, setFilter] = useState<"all" | "active" | "inactive">("all");
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [editingSessionId, setEditingSessionId] = useState<string | undefined>();

  const { data: sessions, isLoading } = api.session.list.useQuery();

  const utils = api.useUtils();

  const activateMutation = api.session.activate.useMutation({
    onSuccess: () => {
      toast.success("Session activated");
      void utils.session.list.invalidate();
      void utils.session.getActive.invalidate();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const deactivateMutation = api.session.deactivate.useMutation({
    onSuccess: () => {
      toast.success("Session deactivated");
      void utils.session.list.invalidate();
      void utils.session.getActive.invalidate();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const deleteMutation = api.session.delete.useMutation({
    onSuccess: () => {
      toast.success("Session deleted");
      void utils.session.list.invalidate();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleActivate = async (sessionId: string) => {
    await activateMutation.mutateAsync({ sessionId });
  };

  const handleDeactivate = async (sessionId: string) => {
    await deactivateMutation.mutateAsync({ sessionId });
  };

  const handleDelete = async (sessionId: string) => {
    if (confirm("Are you sure you want to delete this session? This action cannot be undone.")) {
      await deleteMutation.mutateAsync({ sessionId });
    }
  };

  const handleCreateSession = () => {
    setEditingSessionId(undefined);
    setShowSessionModal(true);
  };

  const handleEditSession = (sessionId: string) => {
    setEditingSessionId(sessionId);
    setShowSessionModal(true);
  };

  const filteredSessions = sessions?.filter((session) => {
    if (filter === "active") return session.isActive;
    if (filter === "inactive") return !session.isActive;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Session Management</h1>
          <p className="text-muted-foreground">
            Manage conference sessions and events
          </p>
        </div>
        <Button onClick={handleCreateSession}>
          <Plus className="mr-2 h-4 w-4" />
          Create Session
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        <Button
          variant={filter === "all" ? "default" : "outline"}
          onClick={() => setFilter("all")}
        >
          All Sessions
        </Button>
        <Button
          variant={filter === "active" ? "default" : "outline"}
          onClick={() => setFilter("active")}
        >
          Active
        </Button>
        <Button
          variant={filter === "inactive" ? "default" : "outline"}
          onClick={() => setFilter("inactive")}
        >
          Inactive
        </Button>
      </div>

      {/* Sessions List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-48" />
                <Skeleton className="h-4 w-32" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredSessions?.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground">No sessions found.</p>
            <Button className="mt-4" onClick={handleCreateSession}>
              <Plus className="mr-2 h-4 w-4" />
              Create Your First Session
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredSessions?.map((session) => (
            <Card key={session.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <CardTitle>{session.name}</CardTitle>
                      <Badge variant={session.isActive ? "default" : "secondary"}>
                        {session.isActive ? "Active" : "Inactive"}
                      </Badge>
                      {session.requiresTicket && (
                        <Badge variant="outline">Requires Ticket</Badge>
                      )}
                    </div>
                    <CardDescription className="mt-1">
                      Event: {session.eventName}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-2 text-sm">
                  <div>
                    <strong>Start:</strong>{" "}
                    {format(new Date(session.startTime), "PPp")}
                  </div>
                  <div>
                    <strong>End:</strong>{" "}
                    {format(new Date(session.endTime), "PPp")}
                  </div>
                  <div>
                    <strong>Current Attendance:</strong>{" "}
                    {session._count?.checkInRecords ?? 0} checked in
                  </div>
                </div>

                <div className="flex gap-2">
                  {session.isActive ? (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeactivate(session.id)}
                      disabled={deactivateMutation.isPending}
                    >
                      <Square className="mr-2 h-4 w-4" />
                      End Session
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleActivate(session.id)}
                      disabled={activateMutation.isPending}
                    >
                      <Play className="mr-2 h-4 w-4" />
                      Activate
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEditSession(session.id)}
                  >
                    <Pencil className="mr-2 h-4 w-4" />
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(session.id)}
                    disabled={deleteMutation.isPending}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <SessionModal
        open={showSessionModal}
        onOpenChange={setShowSessionModal}
        sessionId={editingSessionId}
      />
    </div>
  );
}

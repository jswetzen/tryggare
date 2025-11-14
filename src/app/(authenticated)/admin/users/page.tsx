"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "~/trpc/react";
import { format } from "date-fns";
import { UserX, UserCheck, Plus } from "lucide-react";
import { toast } from "sonner";

export default function UsersPage() {
  const { data: sessionData } = useSession();
  const currentUserId = sessionData?.user?.id;

  const [filter, setFilter] = useState<"all" | "active" | "inactive">("active");

  const { data: users, isLoading } = api.adminUser.list.useQuery();

  const utils = api.useUtils();

  const deactivateMutation = api.adminUser.deactivate.useMutation({
    onSuccess: () => {
      toast.success("User deactivated");
      void utils.adminUser.list.invalidate();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const reactivateMutation = api.adminUser.reactivate.useMutation({
    onSuccess: () => {
      toast.success("User reactivated");
      void utils.adminUser.list.invalidate();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleDeactivate = async (userId: string) => {
    if (userId === currentUserId) {
      toast.error("You cannot deactivate yourself");
      return;
    }

    if (confirm("Are you sure you want to deactivate this user? They will not be able to log in.")) {
      await deactivateMutation.mutateAsync({ userId });
    }
  };

  const handleReactivate = async (userId: string) => {
    await reactivateMutation.mutateAsync({ userId });
  };

  const filteredUsers = users?.filter((user) => {
    if (filter === "active") return user.isActive;
    if (filter === "inactive") return !user.isActive;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
          <p className="text-muted-foreground">
            Manage admin users and their access
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          Create User
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2">
        <Button
          variant={filter === "all" ? "default" : "outline"}
          onClick={() => setFilter("all")}
        >
          All Users
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

      {/* Users List */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredUsers?.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="text-muted-foreground">No users found.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredUsers?.map((user) => {
            const isCurrentUser = user.id === currentUserId;

            return (
              <Card key={user.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle>{user.name}</CardTitle>
                      <CardDescription>@{user.username}</CardDescription>
                    </div>
                    <div className="flex flex-col gap-1">
                      <Badge variant={user.isActive ? "default" : "secondary"}>
                        {user.isActive ? "Active" : "Inactive"}
                      </Badge>
                      {isCurrentUser && (
                        <Badge variant="outline">You</Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {user.lastLoginAt && (
                    <div className="text-sm text-muted-foreground">
                      Last login: {format(new Date(user.lastLoginAt), "PPp")}
                    </div>
                  )}

                  <div className="flex gap-2">
                    {user.isActive ? (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => handleDeactivate(user.id)}
                        disabled={isCurrentUser || deactivateMutation.isPending}
                      >
                        <UserX className="mr-2 h-4 w-4" />
                        Deactivate
                      </Button>
                    ) : (
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full"
                        onClick={() => handleReactivate(user.id)}
                        disabled={reactivateMutation.isPending}
                      >
                        <UserCheck className="mr-2 h-4 w-4" />
                        Reactivate
                      </Button>
                    )}
                  </div>

                  {isCurrentUser && (
                    <p className="text-xs text-muted-foreground">
                      You cannot modify your own account status
                    </p>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

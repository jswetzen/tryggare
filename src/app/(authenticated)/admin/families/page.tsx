"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "~/trpc/react";
import { format } from "date-fns";
import { Search, Eye, Trash2, Users } from "lucide-react";
import { toast } from "sonner";
import Link from "next/link";

export default function FamiliesPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");

  const { data: searchResults, isLoading: isSearching } = api.family.search.useQuery(
    { query: debouncedQuery, limit: 50 },
    { enabled: debouncedQuery.length >= 2 }
  );

  const { data: allFamilies, isLoading: isLoadingAll } = api.family.list.useQuery(
    { limit: 50, offset: 0 },
    { enabled: !debouncedQuery }
  );

  const utils = api.useUtils();

  const deleteMutation = api.family.delete.useMutation({
    onSuccess: () => {
      toast.success("Family deleted");
      void utils.family.search.invalidate();
      void utils.family.list.invalidate();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleDelete = async (familyId: string, familyName: string) => {
    if (
      confirm(
        `Are you sure you want to delete the ${familyName} family? This will delete all associated parents and children. This action cannot be undone.`
      )
    ) {
      await deleteMutation.mutateAsync({ familyId });
    }
  };

  // Debounce search input
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const families = debouncedQuery ? searchResults : allFamilies?.families;
  const isLoading = debouncedQuery ? isSearching : isLoadingAll;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Family Management</h1>
          <p className="text-muted-foreground">
            Search, view, and manage family records
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <Card>
        <CardHeader>
          <CardTitle>Search Families</CardTitle>
          <CardDescription>
            Search by family name, parent name, phone number, or email
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search families..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* Families List */}
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
      ) : !families || families.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Users className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              {searchQuery ? "No families found matching your search." : "No families in the system yet."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {families.map((family) => {
            const primaryParent = family.parents[0];
            const familyName = primaryParent?.name || "Unknown Family";

            return (
              <Card key={family.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle>{familyName}</CardTitle>
                      <CardDescription>
                        {family.parents.length} parent{family.parents.length !== 1 ? "s" : ""} •{" "}
                        {family.children.length} child{family.children.length !== 1 ? "ren" : ""}
                      </CardDescription>
                    </div>
                    {family.lastParticipationDate && (
                      <Badge variant="outline">
                        Last visit: {format(new Date(family.lastParticipationDate), "PP")}
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Parents */}
                  <div>
                    <h4 className="text-sm font-medium mb-2">Parents:</h4>
                    <div className="space-y-1 text-sm text-muted-foreground">
                      {family.parents.map((parent) => (
                        <div key={parent.id}>
                          {parent.name} ({parent.relationshipType})
                          {parent.phone && ` • ${parent.phone}`}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Children */}
                  <div>
                    <h4 className="text-sm font-medium mb-2">Children:</h4>
                    <div className="flex flex-wrap gap-2">
                      {family.children.map((child) => {
                        const age = Math.floor(
                          (Date.now() - new Date(child.birthdate).getTime()) / 31536000000
                        );
                        return (
                          <Badge key={child.id} variant="secondary">
                            {child.firstName} {child.lastName} ({age}y)
                          </Badge>
                        );
                      })}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      asChild
                    >
                      <Link href={`/admin/families/${family.id}`}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Details
                      </Link>
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDelete(family.id, familyName)}
                      disabled={deleteMutation.isPending}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}

          {/* Pagination info */}
          {!debouncedQuery && allFamilies && (
            <div className="text-center text-sm text-muted-foreground">
              Showing {families.length} of {allFamilies.total} families
            </div>
          )}
        </div>
      )}
    </div>
  );
}

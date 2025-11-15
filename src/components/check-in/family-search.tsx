"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";
import { Search, Plus } from "lucide-react";
import { api } from "~/trpc/react";

interface FamilySearchProps {
  onSelectFamily: (familyId: string) => void;
  selectedFamilyId?: string;
  onAddFamily?: () => void;
}

export function FamilySearch({ onSelectFamily, selectedFamilyId, onAddFamily }: FamilySearchProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const t = useTranslations("checkIn");

  const { data: families, isLoading } = api.family.search.useQuery(
    { query: searchQuery, limit: 10 },
    { enabled: searchQuery.length >= 2 }
  );

  return (
    <div className="space-y-4">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          placeholder={t("searchPlaceholder")}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {searchQuery.length >= 2 && (
        <div className="rounded-lg border bg-card">
          {isLoading ? (
            <div className="p-4 text-sm text-muted-foreground">
              {t("searching")}
            </div>
          ) : families && families.length > 0 ? (
            <div className="divide-y">
              {families.map((family) => (
                <button
                  key={family.id}
                  onClick={() => onSelectFamily(family.id)}
                  className={`w-full p-4 text-left transition-colors hover:bg-accent ${
                    selectedFamilyId === family.id ? "bg-accent" : ""
                  }`}
                >
                  <div className="space-y-1">
                    <div className="font-medium">
                      {family.children.map((c) => `${c.firstName} ${c.lastName}`).join(", ")}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {family.parents.map((p) => p.name).join(", ")}
                      {family.parents[0]?.phone && (
                        <span className="ml-2">• {family.parents[0].phone}</span>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="space-y-3 p-4">
              <div className="text-sm text-muted-foreground">
                {t("noResults")}
              </div>
              {onAddFamily && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onAddFamily}
                  className="w-full"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  {t("addNewFamily")}
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FamilySearch } from "~/components/check-in/family-search";
import { CheckedInChildrenView } from "~/components/check-out/checked-in-children-view";
import { RecentCheckouts } from "~/components/check-out/recent-checkouts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "~/trpc/react";
import { toast } from "sonner";

export default function CheckOutPage() {
  const t = useTranslations("checkOut");
  const tCommon = useTranslations("common");

  const [selectedFamilyId, setSelectedFamilyId] = useState<string | undefined>();
  const [selectedChildren, setSelectedChildren] = useState<string[]>([]);
  const [pickedUpBy, setPickedUpBy] = useState("");

  const checkOutMutation = api.checkOut.perform.useMutation({
    onSuccess: (data) => {
      toast.success(t("successMessage", { count: data.count }));
      setSelectedChildren([]);
      setPickedUpBy("");
      setSelectedFamilyId(undefined);
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const utils = api.useUtils();

  const handleToggleChild = (childId: string) => {
    setSelectedChildren((prev) =>
      prev.includes(childId)
        ? prev.filter((id) => id !== childId)
        : [...prev, childId]
    );
  };

  const handleCheckOut = async () => {
    if (selectedChildren.length === 0) {
      toast.error("Please select at least one child");
      return;
    }

    await checkOutMutation.mutateAsync({
      childIds: selectedChildren,
      pickedUpBy: pickedUpBy || undefined,
    });

    // Refresh data
    await utils.checkIn.getCurrentCheckIns.invalidate();
    await utils.checkOut.getRecent.invalidate();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left Column: Search and Family View */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Search Family</CardTitle>
              <CardDescription>
                Search for family to check out children
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FamilySearch
                onSelectFamily={setSelectedFamilyId}
                selectedFamilyId={selectedFamilyId}
              />
            </CardContent>
          </Card>

          {selectedFamilyId && (
            <CheckedInChildrenView
              familyId={selectedFamilyId}
              selectedChildren={selectedChildren}
              onToggleChild={handleToggleChild}
            />
          )}
        </div>

        {/* Right Column: Check-Out Form and Recent Checkouts */}
        <div className="space-y-6">
          {selectedChildren.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{t("checkOutButton")}</CardTitle>
                <CardDescription>
                  {selectedChildren.length} {selectedChildren.length === 1 ? "child" : "children"} selected
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="pickedUpBy">{t("pickedUpBy")}</Label>
                  <Input
                    id="pickedUpBy"
                    type="text"
                    placeholder={t("pickedUpByPlaceholder")}
                    value={pickedUpBy}
                    onChange={(e) => setPickedUpBy(e.target.value)}
                  />
                </div>
                <Button
                  onClick={handleCheckOut}
                  disabled={checkOutMutation.isPending}
                  className="w-full"
                  size="lg"
                >
                  {checkOutMutation.isPending ? tCommon("loading") : t("checkOutButton")}
                </Button>
              </CardContent>
            </Card>
          )}

          <RecentCheckouts />
        </div>
      </div>
    </div>
  );
}

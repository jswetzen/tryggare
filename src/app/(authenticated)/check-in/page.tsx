"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { FamilySearch } from "~/components/check-in/family-search";
import { FamilyView } from "~/components/check-in/family-view";
import { SessionSelector } from "~/components/check-in/session-selector";
import { AddFamilyModal } from "~/components/check-in/add-family-modal";
import { Button } from "@/components/ui/button";
import { api } from "~/trpc/react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Printer } from "lucide-react";
import { QRLabels } from "~/components/check-in/qr-labels";

export default function CheckInPage() {
  const t = useTranslations("checkIn");
  const tCommon = useTranslations("common");

  const [selectedFamilyId, setSelectedFamilyId] = useState<string | undefined>();
  const [selectedSessionId, setSelectedSessionId] = useState<string | undefined>();
  const [selectedChildren, setSelectedChildren] = useState<string[]>([]);
  const [showSuccess, setShowSuccess] = useState(false);
  const [checkInResults, setCheckInResults] = useState<any>(null);
  const [showAddFamilyModal, setShowAddFamilyModal] = useState(false);

  const checkInMutation = api.checkIn.perform.useMutation({
    onSuccess: (data) => {
      setCheckInResults(data);
      setShowSuccess(true);
      setSelectedChildren([]);
      toast.success(t("successMessage", { count: data.count }));
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

  const handleCheckIn = async () => {
    if (!selectedSessionId || selectedChildren.length === 0) {
      toast.error("Please select a session and at least one child");
      return;
    }

    await checkInMutation.mutateAsync({
      sessionId: selectedSessionId,
      childIds: selectedChildren,
    });

    // Refresh data
    await utils.checkIn.getCurrentCheckIns.invalidate();
  };

  const [showQRLabels, setShowQRLabels] = useState(false);

  const handlePrintLabels = () => {
    setShowQRLabels(true);
  };

  const handleNewCheckIn = () => {
    setShowSuccess(false);
    setCheckInResults(null);
    setSelectedFamilyId(undefined);
    setSelectedChildren([]);
    setShowQRLabels(false);
  };

  const handleFamilyCreated = (familyId: string) => {
    setSelectedFamilyId(familyId);
    setShowAddFamilyModal(false);
  };

  if (showSuccess && checkInResults) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("title")}</h1>
        </div>

        <Card className="border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950">
          <CardHeader>
            <CardTitle className="text-green-700 dark:text-green-400">
              {t("checkInComplete")}
            </CardTitle>
            <CardDescription>
              {t("successMessage", { count: checkInResults.count })}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              {checkInResults.checkIns.map((checkIn: any) => (
                <div key={checkIn.childId} className="text-sm">
                  ✓ {checkIn.childName}
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <Button onClick={handlePrintLabels} variant="secondary">
                <Printer className="mr-2 h-4 w-4" />
                {t("printLabels")}
              </Button>
              <Button onClick={handleNewCheckIn}>
                {t("checkInButton")} {tCommon("next")}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* QR Code Labels */}
        {showQRLabels && (
          <QRLabels
            labels={checkInResults.checkIns.map((checkIn: any) => ({
              childId: checkIn.childId,
              childName: checkIn.childName,
              qrToken: checkIn.qrToken,
            }))}
          />
        )}
      </div>
    );
  }

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
              <CardTitle>{t("searchPlaceholder")}</CardTitle>
            </CardHeader>
            <CardContent>
              <FamilySearch
                onSelectFamily={setSelectedFamilyId}
                selectedFamilyId={selectedFamilyId}
                onAddFamily={() => setShowAddFamilyModal(true)}
              />
            </CardContent>
          </Card>

          <AddFamilyModal
            open={showAddFamilyModal}
            onOpenChange={setShowAddFamilyModal}
            onFamilyCreated={handleFamilyCreated}
          />

          {selectedFamilyId && (
            <FamilyView
              familyId={selectedFamilyId}
              sessionId={selectedSessionId}
              selectedChildren={selectedChildren}
              onToggleChild={handleToggleChild}
            />
          )}
        </div>

        {/* Right Column: Session Selector and Actions */}
        <div className="space-y-6">
          <SessionSelector
            selectedSessionId={selectedSessionId}
            onSelectSession={setSelectedSessionId}
          />

          {selectedChildren.length > 0 && selectedSessionId && (
            <Card>
              <CardHeader>
                <CardTitle>{t("checkInButton")}</CardTitle>
                <CardDescription>
                  {selectedChildren.length} {selectedChildren.length === 1 ? "child" : "children"} selected
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  onClick={handleCheckIn}
                  disabled={checkInMutation.isPending}
                  className="w-full"
                  size="lg"
                >
                  {checkInMutation.isPending ? tCommon("loading") : t("checkInButton")}
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

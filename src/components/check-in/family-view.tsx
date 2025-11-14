"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { useTranslations } from "next-intl";
import { api } from "~/trpc/react";
import { Skeleton } from "@/components/ui/skeleton";

interface FamilyViewProps {
  familyId: string;
  sessionId?: string;
  selectedChildren: string[];
  onToggleChild: (childId: string) => void;
}

function calculateAge(birthdate: Date): number {
  const today = new Date();
  const birth = new Date(birthdate);
  let age = today.getFullYear() - birth.getFullYear();
  const monthDiff = today.getMonth() - birth.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
    age--;
  }
  return age;
}

export function FamilyView({ familyId, sessionId, selectedChildren, onToggleChild }: FamilyViewProps) {
  const t = useTranslations("checkIn");
  const tFamily = useTranslations("family");

  const { data: family, isLoading } = api.family.getById.useQuery({ id: familyId });

  // Get current check-ins to show status
  const { data: currentCheckIns } = api.checkIn.getCurrentCheckIns.useQuery({});

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!family) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{tFamily("familyDetails")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Parents */}
        <div>
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">
            {tFamily("parents")}
          </h3>
          <div className="space-y-2">
            {family.parents.map((parent) => (
              <div key={parent.id} className="text-sm">
                <div className="font-medium">{parent.name}</div>
                <div className="text-muted-foreground">
                  {parent.phone && <span>{parent.phone}</span>}
                  {parent.email && parent.phone && <span> • </span>}
                  {parent.email && <span>{parent.email}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Children */}
        <div>
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">
            {tFamily("children")}
          </h3>
          <div className="space-y-3">
            {family.children.map((child) => {
              const isCheckedIn = currentCheckIns?.some(
                (checkIn) => checkIn.childId === child.id
              );
              const currentCheckIn = currentCheckIns?.find(
                (checkIn) => checkIn.childId === child.id
              );
              const isSelected = selectedChildren.includes(child.id);
              const canSelect = !isCheckedIn;

              return (
                <div
                  key={child.id}
                  className={`flex items-start space-x-3 rounded-lg border p-4 ${
                    isCheckedIn ? "bg-muted/50" : "bg-card"
                  }`}
                >
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => onToggleChild(child.id)}
                    disabled={!canSelect}
                    className="mt-1"
                  />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">
                        {child.firstName} {child.lastName}
                      </div>
                      {isCheckedIn && (
                        <Badge variant="secondary">
                          {t("checkedIn")}
                        </Badge>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {tFamily("age")}: {calculateAge(child.birthdate)} years
                    </div>
                    {child.allergies && (
                      <div className="text-sm text-destructive">
                        {tFamily("allergies")}: {child.allergies}
                      </div>
                    )}
                    {child.notes && (
                      <div className="text-sm text-muted-foreground">
                        {child.notes}
                      </div>
                    )}
                    {isCheckedIn && currentCheckIn && (
                      <div className="text-sm text-muted-foreground">
                        {t("currentSession")}: {currentCheckIn.session.name}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

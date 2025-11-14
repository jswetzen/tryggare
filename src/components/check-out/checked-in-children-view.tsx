"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { useTranslations } from "next-intl";
import { api } from "~/trpc/react";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";

interface CheckedInChildrenViewProps {
  familyId: string;
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

export function CheckedInChildrenView({
  familyId,
  selectedChildren,
  onToggleChild
}: CheckedInChildrenViewProps) {
  const t = useTranslations("checkOut");
  const tFamily = useTranslations("family");

  const { data: family, isLoading: familyLoading } = api.family.getById.useQuery({ id: familyId });
  const { data: currentCheckIns, isLoading: checkInsLoading } = api.checkIn.getCurrentCheckIns.useQuery({});

  if (familyLoading || checkInsLoading) {
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

  // Filter to only show children from this family who are currently checked in
  const checkedInChildren = family.children.filter((child) =>
    currentCheckIns?.some((checkIn) => checkIn.childId === child.id)
  );

  if (checkedInChildren.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{tFamily("familyDetails")}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            {t("noChildrenCheckedIn")}
          </div>
        </CardContent>
      </Card>
    );
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

        {/* Checked-In Children */}
        <div>
          <h3 className="mb-2 text-sm font-medium text-muted-foreground">
            {tFamily("children")} ({checkedInChildren.length} checked in)
          </h3>
          <div className="space-y-3">
            {checkedInChildren.map((child) => {
              const checkIn = currentCheckIns?.find((ci) => ci.childId === child.id);
              const isSelected = selectedChildren.includes(child.id);

              return (
                <div
                  key={child.id}
                  className="flex items-start space-x-3 rounded-lg border bg-card p-4"
                >
                  <Checkbox
                    checked={isSelected}
                    onCheckedChange={() => onToggleChild(child.id)}
                    className="mt-1"
                  />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">
                        {child.firstName} {child.lastName}
                      </div>
                      <Badge variant="secondary">Checked In</Badge>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {tFamily("age")}: {calculateAge(child.birthdate)} years
                    </div>
                    {child.allergies && (
                      <div className="text-sm text-destructive">
                        {tFamily("allergies")}: {child.allergies}
                      </div>
                    )}
                    {checkIn && (
                      <div className="text-sm text-muted-foreground">
                        Session: {checkIn.session.name} • Checked in at{" "}
                        {format(new Date(checkIn.checkInTime), "h:mm a")}
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

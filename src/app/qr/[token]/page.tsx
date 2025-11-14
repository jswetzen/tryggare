"use client";

import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "~/trpc/react";
import { format } from "date-fns";
import { Phone, Mail, User, Calendar, AlertCircle } from "lucide-react";

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

export default function QRCodePage() {
  const params = useParams();
  const token = params.token as string;

  const { data: child, isLoading, error } = api.child.getByQrTokenPublic.useQuery(
    { qrToken: token },
    { enabled: !!token }
  );

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-2xl p-4">
        <Card>
          <CardHeader>
            <Skeleton className="h-8 w-48" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !child) {
    return (
      <div className="container mx-auto max-w-2xl p-4">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              QR Code Not Found
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">
              This QR code is not valid or the child record could not be found. Please check with conference staff.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentCheckIn = child.checkInRecords[0];
  const isCheckedIn = !!currentCheckIn;

  return (
    <div className="container mx-auto max-w-2xl space-y-6 p-4">
      {/* Child Information */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-2xl">
              {child.firstName} {child.lastName}
            </CardTitle>
            {isCheckedIn ? (
              <Badge variant="default" className="text-lg">
                Checked In
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-lg">
                Not Checked In
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Basic Info */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">
                <strong>Age:</strong> {calculateAge(child.birthdate)} years
              </span>
            </div>
            <div className="flex items-center gap-2">
              <User className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">
                <strong>Born:</strong> {format(new Date(child.birthdate), "PP")}
              </span>
            </div>
          </div>

          {/* Allergies */}
          {child.allergies && (
            <div className="rounded-lg border-2 border-destructive bg-destructive/10 p-4">
              <div className="flex items-start gap-2">
                <AlertCircle className="mt-0.5 h-5 w-5 text-destructive" />
                <div>
                  <div className="font-semibold text-destructive">Allergies</div>
                  <div className="text-sm">{child.allergies}</div>
                </div>
              </div>
            </div>
          )}

          {/* Notes */}
          {child.notes && (
            <div className="rounded-lg border bg-muted p-4">
              <div className="font-semibold">Notes</div>
              <div className="text-sm text-muted-foreground">{child.notes}</div>
            </div>
          )}

          {/* Current Check-In Status */}
          {isCheckedIn && currentCheckIn && (
            <div className="rounded-lg border-2 border-primary bg-primary/10 p-4">
              <div className="font-semibold">Current Session</div>
              <div className="mt-2 space-y-1 text-sm">
                <div><strong>Session:</strong> {currentCheckIn.session.name}</div>
                <div><strong>Checked in at:</strong> {format(new Date(currentCheckIn.checkInTime), "PPp")}</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Parent Contact Information */}
      <Card>
        <CardHeader>
          <CardTitle>Parent/Guardian Contact</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {child.family.parents.map((parent) => (
              <div key={parent.id} className="rounded-lg border p-4">
                <div className="mb-2 font-medium">{parent.name}</div>
                <div className="space-y-2 text-sm text-muted-foreground">
                  {parent.phone && (
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4" />
                      <a href={`tel:${parent.phone}`} className="hover:underline">
                        {parent.phone}
                      </a>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <span>{parent.relationshipType}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="text-center text-sm text-muted-foreground">
        <p>This is a secure QR code for {child.firstName} {child.lastName}</p>
        <p className="mt-1">For staff use only • Do not share</p>
      </div>
    </div>
  );
}

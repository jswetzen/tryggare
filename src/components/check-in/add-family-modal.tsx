"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api } from "~/trpc/react";
import { toast } from "sonner";
import { CalendarIcon, Loader2 } from "lucide-react";
import { Calendar } from "@/components/ui/calendar";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { format } from "date-fns";

interface AddFamilyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onFamilyCreated?: (familyId: string) => void;
}

interface ParentFormData {
  name: string;
  phone: string;
  email: string;
  relationshipType: string;
}

interface ChildFormData {
  firstName: string;
  lastName: string;
  birthdate: Date | undefined;
  allergies: string;
  notes: string;
}

export function AddFamilyModal({
  open,
  onOpenChange,
  onFamilyCreated,
}: AddFamilyModalProps) {
  const t = useTranslations("checkIn");
  const tCommon = useTranslations("common");

  const [parent, setParent] = useState<ParentFormData>({
    name: "",
    phone: "",
    email: "",
    relationshipType: "parent",
  });

  const [child, setChild] = useState<ChildFormData>({
    firstName: "",
    lastName: "",
    birthdate: undefined,
    allergies: "",
    notes: "",
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const createMutation = api.family.create.useMutation({
    onSuccess: (data) => {
      toast.success(t("familyAddedSuccess"));
      onFamilyCreated?.(data.id);
      handleClose();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleClose = () => {
    setParent({
      name: "",
      phone: "",
      email: "",
      relationshipType: "parent",
    });
    setChild({
      firstName: "",
      lastName: "",
      birthdate: undefined,
      allergies: "",
      notes: "",
    });
    setErrors({});
    onOpenChange(false);
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!parent.name.trim()) {
      newErrors.parentName = t("parentNameRequired");
    }
    if (!parent.phone.trim()) {
      newErrors.parentPhone = t("parentPhoneRequired");
    }
    if (parent.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(parent.email)) {
      newErrors.parentEmail = t("invalidEmail");
    }
    if (!child.firstName.trim()) {
      newErrors.childFirstName = t("childFirstNameRequired");
    }
    if (!child.lastName.trim()) {
      newErrors.childLastName = t("childLastNameRequired");
    }
    if (!child.birthdate) {
      newErrors.childBirthdate = t("childBirthdateRequired");
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    await createMutation.mutateAsync({
      parents: [
        {
          name: parent.name.trim(),
          phone: parent.phone.trim(),
          email: parent.email.trim() || undefined,
          relationshipType: parent.relationshipType,
        },
      ],
      children: [
        {
          firstName: child.firstName.trim(),
          lastName: child.lastName.trim(),
          birthdate: child.birthdate!,
          allergies: child.allergies.trim() || undefined,
          notes: child.notes.trim() || undefined,
        },
      ],
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{t("addNewFamily")}</DialogTitle>
          <DialogDescription>{t("addFamilyDescription")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Parent Information */}
          <div className="space-y-4">
            <h3 className="font-semibold">{t("parentInformation")}</h3>

            <div className="space-y-2">
              <Label htmlFor="parent-name">
                {t("parentName")} <span className="text-destructive">*</span>
              </Label>
              <Input
                id="parent-name"
                value={parent.name}
                onChange={(e) =>
                  setParent({ ...parent, name: e.target.value })
                }
                placeholder={t("parentNamePlaceholder")}
              />
              {errors.parentName && (
                <p className="text-sm text-destructive">{errors.parentName}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="parent-phone">
                {t("parentPhone")} <span className="text-destructive">*</span>
              </Label>
              <Input
                id="parent-phone"
                type="tel"
                value={parent.phone}
                onChange={(e) =>
                  setParent({ ...parent, phone: e.target.value })
                }
                placeholder={t("parentPhonePlaceholder")}
              />
              {errors.parentPhone && (
                <p className="text-sm text-destructive">{errors.parentPhone}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="parent-email">{t("parentEmail")}</Label>
              <Input
                id="parent-email"
                type="email"
                value={parent.email}
                onChange={(e) =>
                  setParent({ ...parent, email: e.target.value })
                }
                placeholder={t("parentEmailPlaceholder")}
              />
              {errors.parentEmail && (
                <p className="text-sm text-destructive">{errors.parentEmail}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="relationship-type">
                {t("relationshipType")} <span className="text-destructive">*</span>
              </Label>
              <Select
                value={parent.relationshipType}
                onValueChange={(value) =>
                  setParent({ ...parent, relationshipType: value })
                }
              >
                <SelectTrigger id="relationship-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="parent">{t("parent")}</SelectItem>
                  <SelectItem value="guardian">{t("guardian")}</SelectItem>
                  <SelectItem value="other">{t("other")}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Child Information */}
          <div className="space-y-4">
            <h3 className="font-semibold">{t("childInformation")}</h3>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="child-first-name">
                  {t("childFirstName")} <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="child-first-name"
                  value={child.firstName}
                  onChange={(e) =>
                    setChild({ ...child, firstName: e.target.value })
                  }
                  placeholder={t("childFirstNamePlaceholder")}
                />
                {errors.childFirstName && (
                  <p className="text-sm text-destructive">
                    {errors.childFirstName}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="child-last-name">
                  {t("childLastName")} <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="child-last-name"
                  value={child.lastName}
                  onChange={(e) =>
                    setChild({ ...child, lastName: e.target.value })
                  }
                  placeholder={t("childLastNamePlaceholder")}
                />
                {errors.childLastName && (
                  <p className="text-sm text-destructive">
                    {errors.childLastName}
                  </p>
                )}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="child-birthdate">
                {t("childBirthdate")} <span className="text-destructive">*</span>
              </Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    id="child-birthdate"
                    variant="outline"
                    className="w-full justify-start text-left font-normal"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {child.birthdate ? (
                      format(child.birthdate, "PPP")
                    ) : (
                      <span className="text-muted-foreground">
                        {t("pickDate")}
                      </span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={child.birthdate}
                    onSelect={(date) => setChild({ ...child, birthdate: date })}
                    disabled={(date) =>
                      date > new Date() || date < new Date("1900-01-01")
                    }
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              {errors.childBirthdate && (
                <p className="text-sm text-destructive">
                  {errors.childBirthdate}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="child-allergies">{t("childAllergies")}</Label>
              <Textarea
                id="child-allergies"
                value={child.allergies}
                onChange={(e) =>
                  setChild({ ...child, allergies: e.target.value })
                }
                placeholder={t("childAllergiesPlaceholder")}
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="child-notes">{t("childNotes")}</Label>
              <Textarea
                id="child-notes"
                value={child.notes}
                onChange={(e) => setChild({ ...child, notes: e.target.value })}
                placeholder={t("childNotesPlaceholder")}
                rows={2}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            {tCommon("cancel")}
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {tCommon("loading")}
              </>
            ) : (
              t("addFamily")
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

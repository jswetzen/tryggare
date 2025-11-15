"use client";

import { useState, useEffect } from "react";
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
import { Checkbox } from "@/components/ui/checkbox";
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

interface SessionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  sessionId?: string; // If provided, edit mode; otherwise create mode
}

export function SessionModal({
  open,
  onOpenChange,
  sessionId,
}: SessionModalProps) {
  const t = useTranslations("admin.sessions");
  const tCommon = useTranslations("common");

  const [formData, setFormData] = useState({
    name: "",
    eventName: "",
    startDate: undefined as Date | undefined,
    startTime: "09:00",
    endDate: undefined as Date | undefined,
    endTime: "17:00",
    requiresTicket: false,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const { data: existingSession, isLoading: isLoadingSession } =
    api.session.getById.useQuery(
      { id: sessionId! },
      { enabled: !!sessionId }
    );

  const utils = api.useUtils();

  // Load existing session data in edit mode
  useEffect(() => {
    if (existingSession) {
      const startTime = new Date(existingSession.startTime);
      const endTime = new Date(existingSession.endTime);

      setFormData({
        name: existingSession.name,
        eventName: existingSession.event.name,
        startDate: startTime,
        startTime: format(startTime, "HH:mm"),
        endDate: endTime,
        endTime: format(endTime, "HH:mm"),
        requiresTicket: existingSession.requiresTicket,
      });
    }
  }, [existingSession]);

  const createEventMutation = api.event.create.useMutation();

  const createMutation = api.session.create.useMutation({
    onSuccess: () => {
      toast.success(t("sessionCreated"));
      utils.session.list.invalidate();
      handleClose();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const updateMutation = api.session.update.useMutation({
    onSuccess: () => {
      toast.success(t("sessionUpdated"));
      utils.session.list.invalidate();
      utils.session.getById.invalidate({ id: sessionId! });
      handleClose();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleClose = () => {
    setFormData({
      name: "",
      eventName: "",
      startDate: undefined,
      startTime: "09:00",
      endDate: undefined,
      endTime: "17:00",
      requiresTicket: false,
    });
    setErrors({});
    onOpenChange(false);
  };

  const combineDateTime = (date: Date, time: string): Date => {
    const [hours, minutes] = time.split(":").map(Number);
    const combined = new Date(date);
    combined.setHours(hours!, minutes!, 0, 0);
    return combined;
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = t("nameRequired");
    }
    if (!sessionId && !formData.eventName.trim()) {
      newErrors.eventName = t("eventNameRequired");
    }
    if (!formData.startDate) {
      newErrors.startDate = t("startDateRequired");
    }
    if (!formData.endDate) {
      newErrors.endDate = t("endDateRequired");
    }

    if (formData.startDate && formData.endDate) {
      const startDateTime = combineDateTime(formData.startDate, formData.startTime);
      const endDateTime = combineDateTime(formData.endDate, formData.endTime);

      if (endDateTime <= startDateTime) {
        newErrors.endDate = t("endTimeAfterStart");
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    const startDateTime = combineDateTime(formData.startDate!, formData.startTime);
    const endDateTime = combineDateTime(formData.endDate!, formData.endTime);

    if (sessionId) {
      // Update existing session
      await updateMutation.mutateAsync({
        id: sessionId,
        name: formData.name.trim(),
        startTime: startDateTime,
        endTime: endDateTime,
        requiresTicket: formData.requiresTicket,
      });
    } else {
      // Create new session
      // First create an event with the same date range as the session
      try {
        const event = await createEventMutation.mutateAsync({
          name: formData.eventName.trim(),
          startDate: formData.startDate!,
          endDate: formData.endDate!,
        });

        // Then create the session linked to the event
        await createMutation.mutateAsync({
          name: formData.name.trim(),
          startTime: startDateTime,
          endTime: endDateTime,
          requiresTicket: formData.requiresTicket,
          eventId: event.id,
        });
      } catch (error) {
        // Error already handled by mutation's onError
        console.error("Failed to create session:", error);
      }
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending || isLoadingSession || createEventMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {sessionId ? t("editSession") : t("createSession")}
          </DialogTitle>
          <DialogDescription>
            {sessionId
              ? t("editSessionDescription")
              : t("createSessionDescription")}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Session Name */}
          <div className="space-y-2">
            <Label htmlFor="session-name">
              {t("sessionName")} <span className="text-destructive">*</span>
            </Label>
            <Input
              id="session-name"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              placeholder={t("sessionNamePlaceholder")}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name}</p>
            )}
          </div>

          {/* Event Name (only in create mode) */}
          {!sessionId && (
            <div className="space-y-2">
              <Label htmlFor="event-name">
                {t("eventName")} <span className="text-destructive">*</span>
              </Label>
              <Input
                id="event-name"
                value={formData.eventName}
                onChange={(e) =>
                  setFormData({ ...formData, eventName: e.target.value })
                }
                placeholder={t("eventNamePlaceholder")}
              />
              {errors.eventName && (
                <p className="text-sm text-destructive">{errors.eventName}</p>
              )}
            </div>
          )}

          {/* Start Date and Time */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="start-date">
                {t("startDate")} <span className="text-destructive">*</span>
              </Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    id="start-date"
                    variant="outline"
                    className="w-full justify-start text-left font-normal"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {formData.startDate ? (
                      format(formData.startDate, "PPP")
                    ) : (
                      <span className="text-muted-foreground">
                        {tCommon("pickDate")}
                      </span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={formData.startDate}
                    onSelect={(date) =>
                      setFormData({ ...formData, startDate: date })
                    }
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              {errors.startDate && (
                <p className="text-sm text-destructive">{errors.startDate}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="start-time">
                {t("startTime")} <span className="text-destructive">*</span>
              </Label>
              <Input
                id="start-time"
                type="time"
                value={formData.startTime}
                onChange={(e) =>
                  setFormData({ ...formData, startTime: e.target.value })
                }
              />
            </div>
          </div>

          {/* End Date and Time */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="end-date">
                {t("endDate")} <span className="text-destructive">*</span>
              </Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    id="end-date"
                    variant="outline"
                    className="w-full justify-start text-left font-normal"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {formData.endDate ? (
                      format(formData.endDate, "PPP")
                    ) : (
                      <span className="text-muted-foreground">
                        {tCommon("pickDate")}
                      </span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={formData.endDate}
                    onSelect={(date) =>
                      setFormData({ ...formData, endDate: date })
                    }
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              {errors.endDate && (
                <p className="text-sm text-destructive">{errors.endDate}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="end-time">
                {t("endTime")} <span className="text-destructive">*</span>
              </Label>
              <Input
                id="end-time"
                type="time"
                value={formData.endTime}
                onChange={(e) =>
                  setFormData({ ...formData, endTime: e.target.value })
                }
              />
            </div>
          </div>

          {/* Requires Ticket */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="requires-ticket"
              checked={formData.requiresTicket}
              onCheckedChange={(checked) =>
                setFormData({ ...formData, requiresTicket: checked as boolean })
              }
            />
            <Label htmlFor="requires-ticket" className="cursor-pointer">
              {t("requiresTicket")}
            </Label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            {tCommon("cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {tCommon("loading")}
              </>
            ) : sessionId ? (
              tCommon("save")
            ) : (
              t("createSession")
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

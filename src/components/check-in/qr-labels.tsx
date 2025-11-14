"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useTranslations } from "next-intl";
import { QRCodeSVG } from "qrcode.react";
import { Printer } from "lucide-react";

interface QRLabel {
  childId: string;
  childName: string;
  qrToken: string;
}

interface QRLabelsProps {
  labels: QRLabel[];
  onPrint?: () => void;
}

export function QRLabels({ labels, onPrint }: QRLabelsProps) {
  const t = useTranslations("checkIn");

  const handlePrint = () => {
    window.print();
    onPrint?.();
  };

  return (
    <div>
      {/* Screen version */}
      <div className="space-y-4 print:hidden">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">{t("printLabels")}</h2>
          <Button onClick={handlePrint}>
            <Printer className="mr-2 h-4 w-4" />
            {t("printLabels")}
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {labels.map((label) => (
            <Card key={label.childId}>
              <CardHeader>
                <CardTitle className="text-base">{label.childName}</CardTitle>
              </CardHeader>
              <CardContent className="flex justify-center">
                <QRCodeSVG
                  value={`${process.env.NEXT_PUBLIC_APP_URL || window.location.origin}/qr/${label.qrToken}`}
                  size={200}
                  level="M"
                  includeMargin={true}
                />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Print version */}
      <div className="hidden print:block">
        <style jsx global>{`
          @media print {
            @page {
              size: 4in 2in;
              margin: 0.1in;
            }
            body {
              margin: 0;
              padding: 0;
            }
          }
        `}</style>

        {labels.map((label) => (
          <div
            key={label.childId}
            className="flex h-[2in] w-[4in] flex-col items-center justify-center break-after-page border-2 border-dashed border-gray-400 p-2"
          >
            <div className="mb-2 text-center text-lg font-bold">{label.childName}</div>
            <QRCodeSVG
              value={`${process.env.NEXT_PUBLIC_APP_URL || window.location.origin}/qr/${label.qrToken}`}
              size={150}
              level="M"
              includeMargin={false}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

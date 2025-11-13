"use client";

import * as React from "react";
import { Languages } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { locales, localeNames, type Locale } from "~/i18n/config";

export function LocaleSwitcher() {
  const [currentLocale, setCurrentLocale] = React.useState<Locale>("en");

  React.useEffect(() => {
    // Get current locale from cookie
    const localeCookie = document.cookie
      .split("; ")
      .find((row) => row.startsWith("NEXT_LOCALE="));

    if (localeCookie) {
      const locale = localeCookie.split("=")[1] as Locale;
      if (locales.includes(locale)) {
        setCurrentLocale(locale);
      }
    }
  }, []);

  const switchLocale = (locale: Locale) => {
    // Set cookie
    document.cookie = `NEXT_LOCALE=${locale}; path=/; max-age=31536000`; // 1 year
    setCurrentLocale(locale);

    // Reload page to apply new locale
    window.location.reload();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" title="Change Language">
          <Languages className="h-[1.2rem] w-[1.2rem]" />
          <span className="sr-only">Switch language</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {locales.map((locale) => (
          <DropdownMenuItem
            key={locale}
            onClick={() => switchLocale(locale)}
            className={currentLocale === locale ? "bg-accent" : ""}
          >
            {localeNames[locale]}
            {currentLocale === locale && " ✓"}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

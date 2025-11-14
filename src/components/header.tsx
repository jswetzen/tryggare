"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Menu } from "lucide-react";
import { signOut, useSession } from "next-auth/react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "~/components/theme-toggle";
import { LocaleSwitcher } from "~/components/locale-switcher";
import { cn } from "~/lib/utils";

export function Header() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const t = useTranslations("nav");
  const tCommon = useTranslations("common");

  const navigation = [
    { name: t("dashboard"), href: "/" },
    { name: t("checkIn"), href: "/check-in" },
    { name: t("checkOut"), href: "/check-out" },
    { name: t("admin"), href: "/admin" },
  ];

  const handleLogout = () => {
    void signOut({ callbackUrl: "/login" });
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center space-x-2">
            <span className="font-bold">{tCommon("appName")}</span>
          </Link>

          <nav className="hidden items-center gap-4 md:flex">
            {navigation.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "text-sm font-medium transition-colors hover:text-primary",
                  pathname === item.href
                    ? "text-foreground"
                    : "text-muted-foreground"
                )}
              >
                {item.name}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-2">
          {session?.user && (
            <span className="hidden text-sm text-muted-foreground md:inline-block">
              {session.user.name}
            </span>
          )}
          <LocaleSwitcher />
          <ThemeToggle />
          <Button
            variant="ghost"
            size="icon"
            onClick={handleLogout}
            title={t("logout")}
          >
            <LogOut className="h-[1.2rem] w-[1.2rem]" />
            <span className="sr-only">{t("logout")}</span>
          </Button>
        </div>
      </div>
    </header>
  );
}

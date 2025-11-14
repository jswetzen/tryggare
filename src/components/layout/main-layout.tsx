"use client";

import { useSession, signOut } from "next-auth/react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { LogOut, Menu, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { useTranslations } from "next-intl";

const navigationItems = [
  { name: "dashboard", href: "/", icon: "📊" },
  { name: "checkIn", href: "/check-in", icon: "✅" },
  { name: "checkOut", href: "/check-out", icon: "👋" },
  { name: "admin", href: "/admin", icon: "⚙️" },
];

export function MainLayout({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();
  const pathname = usePathname();
  const t = useTranslations("nav");
  const tCommon = useTranslations("common");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await signOut({ callbackUrl: "/login" });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between px-4">
          {/* Logo and App Name */}
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center space-x-2">
              <span className="text-2xl font-bold">{tCommon("appName")}</span>
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-1">
              {navigationItems.map((item) => {
                const isActive = pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    }`}
                  >
                    <span className="mr-1">{item.icon}</span>
                    {t(item.name)}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Right side actions */}
          <div className="flex items-center gap-2">
            {/* User info and logout */}
            {session?.user && (
              <div className="hidden sm:flex items-center gap-2 mr-2">
                <span className="text-sm text-muted-foreground">
                  {session.user.name}
                </span>
              </div>
            )}

            {/* Theme toggle */}
            <ThemeToggle />

            {/* Language switcher */}
            <LocaleSwitcher />

            {/* Logout button */}
            {session && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleLogout}
                title={t("logout")}
              >
                <LogOut className="h-5 w-5" />
                <span className="sr-only">{t("logout")}</span>
              </Button>
            )}

            {/* Mobile menu button */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
              <span className="sr-only">Toggle menu</span>
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t">
            <nav className="container px-4 py-4 space-y-1">
              {navigationItems.map((item) => {
                const isActive = pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center px-3 py-2 rounded-md text-base font-medium transition-colors ${
                      isActive
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    }`}
                  >
                    <span className="mr-2">{item.icon}</span>
                    {t(item.name)}
                  </Link>
                );
              })}
              {session?.user && (
                <div className="pt-4 mt-4 border-t">
                  <div className="text-sm text-muted-foreground mb-2">
                    {t("loggedInAs")}: {session.user.name}
                  </div>
                </div>
              )}
            </nav>
          </div>
        )}
      </header>

      {/* Main content */}
      <main className="container px-4 py-6">
        {children}
      </main>
    </div>
  );
}

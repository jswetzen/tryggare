import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "~/lib/auth";

export default async function Home() {
  // Check if user is authenticated
  const session = await auth();

  // If authenticated, redirect to dashboard
  if (session) {
    redirect("/dashboard");
  }

  // Show landing page for unauthenticated users
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-blue-600 to-blue-900 text-white">
      <div className="container flex flex-col items-center justify-center gap-12 px-4 py-16">
        <h1 className="text-5xl font-extrabold tracking-tight sm:text-[5rem]">
          Conference Child Management System
        </h1>

        <p className="text-xl text-center max-w-2xl">
          Secure check-in and check-out system for managing children at conference events
        </p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:gap-8">
          <Link
            className="flex max-w-xs flex-col gap-4 rounded-xl bg-white/10 p-4 hover:bg-white/20 transition-all"
            href="/login"
          >
            <h3 className="text-2xl font-bold">Admin Login →</h3>
            <div className="text-lg">
              Access the admin dashboard to manage families, children, and check-ins
            </div>
          </Link>

          <Link
            className="flex max-w-xs flex-col gap-4 rounded-xl bg-white/10 p-4 hover:bg-white/20 transition-all"
            href="/kiosk"
          >
            <h3 className="text-2xl font-bold">Check-In Kiosk →</h3>
            <div className="text-lg">
              Parent-facing kiosk for checking children in and out of events
            </div>
          </Link>
        </div>
      </div>
    </main>
  );
}

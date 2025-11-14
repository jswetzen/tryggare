import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { auth } from "~/lib/auth";
import { Header } from "~/components/header";
import { SessionProvider } from "~/components/session-provider";

export default async function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  let session;

  try {
    session = await auth();
  } catch (error) {
    // If there's a JWT error (e.g., invalid secret, corrupted token),
    // clear the session cookies and redirect to login
    console.error("Auth error in authenticated layout:", error);

    const cookieStore = await cookies();
    // Clear both possible session cookie names
    cookieStore.delete("next-auth.session-token");
    cookieStore.delete("__Secure-next-auth.session-token");

    redirect("/login");
  }

  if (!session) {
    redirect("/login");
  }

  return (
    <SessionProvider session={session}>
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="flex-1">
          <div className="container py-6">{children}</div>
        </main>
      </div>
    </SessionProvider>
  );
}

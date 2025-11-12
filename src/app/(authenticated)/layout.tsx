import { redirect } from "next/navigation";
import { auth } from "~/lib/auth";
import { Header } from "~/components/header";

export default async function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  if (!session) {
    redirect("/login");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <div className="container py-6">{children}</div>
      </main>
    </div>
  );
}

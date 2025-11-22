import NextAuth, { type DefaultSession } from "next-auth";
import Credentials from "next-auth/providers/credentials";
import { db } from "~/server/db";

// Extend the built-in session types
declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      username: string;
      name: string;
    } & DefaultSession["user"];
  }

  interface User {
    id: string;
    username: string;
    name: string;
    isActive: boolean;
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  secret: process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET,
  session: {
    strategy: "jwt",
    maxAge: 8 * 60 * 60, // 8 hours in seconds
  },
  pages: {
    signIn: "/login",
  },
  providers: [
    Credentials({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) {
          return null;
        }

        // Find the admin user by username
        const user = await db.adminUser.findUnique({
          where: {
            username: credentials.username as string,
          },
        });

        // Check if user exists, is active, and password matches
        if (!user || !user.isActive) {
          return null;
        }

        // Import bcrypt only when needed (keeps it out of Edge middleware bundle)
        const { compare } = await import("bcryptjs");

        // DEBUG: Log password comparison details
        console.log('[AUTH] Login attempt for user:', credentials.username);
        console.log('[AUTH] Password length:', (credentials.password as string).length);
        console.log('[AUTH] Stored hash:', user.passwordHash);
        console.log('[AUTH] Hash length:', user.passwordHash.length);

        const passwordMatch = await compare(
          credentials.password as string,
          user.passwordHash
        );

        console.log('[AUTH] Password match result:', passwordMatch);

        if (!passwordMatch) {
          console.log('[AUTH] Login failed: password mismatch');
          return null;
        }

        console.log('[AUTH] Login successful for user:', credentials.username);

        // Update last login timestamp
        await db.adminUser.update({
          where: { id: user.id },
          data: { lastLogin: new Date() },
        });

        return {
          id: user.id,
          username: user.username,
          name: user.name,
          email: null, // AdminUser doesn't have email
          isActive: user.isActive,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      // Add user data to token on sign in
      if (user) {
        token.id = user.id;
        token.username = user.username;
        token.name = user.name;
      }
      return token;
    },
    async session({ session, token }) {
      // Add user data from token to session
      if (token && session.user) {
        session.user.id = token.id as string;
        session.user.username = token.username as string;
        session.user.name = token.name as string;
      }
      return session;
    },
  },
  cookies: {
    sessionToken: {
      name: "next-auth.session-token",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
});

/**
 * Helper function to get the current authenticated user
 * Returns null if not authenticated
 */
export async function getCurrentUser() {
  const session = await auth();
  return session?.user ?? null;
}

/**
 * Helper function to require authentication
 * Throws an error if not authenticated
 */
export async function requireAuth() {
  const user = await getCurrentUser();
  if (!user) {
    throw new Error("Unauthorized");
  }
  return user;
}

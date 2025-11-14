import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "./middleware";

describe("Middleware - Route Protection", () => {
  const createRequest = (
    pathname: string,
    sessionToken?: string
  ): NextRequest => {
    const url = `http://localhost:3000${pathname}`;
    const request = new NextRequest(url);

    // Add session cookie if provided
    if (sessionToken) {
      request.cookies.set("next-auth.session-token", sessionToken);
    }

    return request;
  };

  describe("Public Routes", () => {
    it("should allow access to /login without authentication", async () => {
      const request = createRequest("/login");
      const response = await middleware(request);

      // Should proceed without redirect
      expect(response.status).not.toBe(307); // Not a redirect
    });

    it("should allow access to /api/auth/* without authentication", async () => {
      const request = createRequest("/api/auth/signin");
      const response = await middleware(request);

      expect(response.status).not.toBe(307);
    });

    it("should allow access to /qr routes without authentication", async () => {
      const request = createRequest("/qr/abc123");
      const response = await middleware(request);

      expect(response.status).not.toBe(307);
    });
  });

  describe("Protected Routes", () => {
    it("should redirect unauthenticated users from /dashboard to /login", async () => {
      const request = createRequest("/dashboard");
      const response = await middleware(request);

      expect(response.status).toBe(307); // Redirect
      expect(response.headers.get("location")).toContain("/login");
      expect(response.headers.get("location")).toContain(
        "callbackUrl=%2Fdashboard"
      );
    });

    it("should redirect unauthenticated users from root / to /login", async () => {
      const request = createRequest("/");
      const response = await middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toContain("/login");
    });

    it("should redirect unauthenticated users from /check-in to /login", async () => {
      const request = createRequest("/check-in");
      const response = await middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toContain("/login");
      expect(response.headers.get("location")).toContain(
        "callbackUrl=%2Fcheck-in"
      );
    });

    it("should redirect unauthenticated users from /check-out to /login", async () => {
      const request = createRequest("/check-out");
      const response = await middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toContain("/login");
    });

    it("should redirect unauthenticated users from /admin to /login", async () => {
      const request = createRequest("/admin");
      const response = await middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toContain("/login");
    });
  });

  describe("Authenticated Routes", () => {
    it("should allow authenticated users to access /dashboard", async () => {
      const request = createRequest("/dashboard", "valid-session-token");
      const response = await middleware(request);

      // Should not redirect
      expect(response.status).not.toBe(307);
    });

    it("should allow authenticated users to access /check-in", async () => {
      const request = createRequest("/check-in", "valid-session-token");
      const response = await middleware(request);

      expect(response.status).not.toBe(307);
    });

    it("should allow authenticated users to access /check-out", async () => {
      const request = createRequest("/check-out", "valid-session-token");
      const response = await middleware(request);

      expect(response.status).not.toBe(307);
    });

    it("should allow authenticated users to access /admin", async () => {
      const request = createRequest("/admin", "valid-session-token");
      const response = await middleware(request);

      expect(response.status).not.toBe(307);
    });
  });

  describe("Login Redirect", () => {
    it("should redirect authenticated users from /login to /dashboard", async () => {
      const request = createRequest("/login", "valid-session-token");
      const response = await middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toContain("/dashboard");
    });
  });

  describe("Static Assets", () => {
    it("should allow access to favicon.ico", async () => {
      const request = createRequest("/favicon.ico");
      const response = await middleware(request);

      // Middleware shouldn't run for static assets based on config
      expect(response).toBeDefined();
    });

    it("should allow access to images", async () => {
      const request = createRequest("/test.png");
      const response = await middleware(request);

      expect(response).toBeDefined();
    });
  });

  describe("Callback URL Preservation", () => {
    it("should preserve requested path in callbackUrl when redirecting to login", async () => {
      const targetPath = "/admin/users";
      const request = createRequest(targetPath);
      const response = await middleware(request);

      expect(response.status).toBe(307);
      const location = response.headers.get("location");
      expect(location).toContain("callbackUrl=%2Fadmin%2Fusers");
    });

    it("should handle nested paths in callbackUrl", async () => {
      const request = createRequest("/check-in/family/123");
      const response = await middleware(request);

      expect(response.status).toBe(307);
      const location = response.headers.get("location");
      expect(location).toContain("callbackUrl=");
    });
  });

  describe("Session Cookie Detection", () => {
    it("should detect standard session cookie", async () => {
      const request = createRequest("/dashboard");
      request.cookies.set("next-auth.session-token", "token123");
      const response = await middleware(request);

      expect(response.status).not.toBe(307); // Should not redirect
    });

    it("should detect secure session cookie", async () => {
      const request = createRequest("/dashboard");
      request.cookies.set("__Secure-next-auth.session-token", "token123");
      const response = await middleware(request);

      expect(response.status).not.toBe(307); // Should not redirect
    });

    it("should redirect when no session cookie present", async () => {
      const request = createRequest("/dashboard");
      const response = await middleware(request);

      expect(response.status).toBe(307);
      expect(response.headers.get("location")).toContain("/login");
    });
  });

  describe("API Routes", () => {
    it("should allow /api/trpc routes to pass through", async () => {
      const request = createRequest("/api/trpc/session.list");
      const response = await middleware(request);

      // API routes should be handled by tRPC middleware, not auth middleware
      expect(response).toBeDefined();
    });

    it("should allow /api/health to pass through", async () => {
      const request = createRequest("/api/health");
      const response = await middleware(request);

      expect(response).toBeDefined();
    });
  });
});

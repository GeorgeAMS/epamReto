import { redirect } from "@tanstack/react-router";
import { getAuthToken } from "@/lib/auth";

export function requireAuth() {
  if (typeof window === "undefined") return;
  if (!getAuthToken()) {
    throw redirect({ to: "/login" });
  }
}

export function requireGuest() {
  if (typeof window === "undefined") return;
  if (getAuthToken()) {
    throw redirect({ to: "/" });
  }
}


import { NextRequest, NextResponse } from "next/server";
import { authBackendUrl, readBackendResponse } from "@/lib/auth-api";
import { setAccessCookie } from "@/lib/session";

export async function GET(request: NextRequest) {
  const accessToken = request.cookies.get("access_token")?.value;
  const refreshToken = request.cookies.get("refresh_token")?.value;
  if (!accessToken && !refreshToken) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  if (accessToken) {
    return NextResponse.json({ token: accessToken });
  }

  const refreshResponse = await fetch(`${authBackendUrl}/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: "no-store",
  });
  const payload = (await readBackendResponse(refreshResponse)) as { access_token?: string };
  if (!refreshResponse.ok || !payload.access_token) {
    return NextResponse.json({ detail: "Not authenticated" }, { status: 401 });
  }

  const response = NextResponse.json({ token: payload.access_token });
  setAccessCookie(response, payload.access_token);
  return response;
}
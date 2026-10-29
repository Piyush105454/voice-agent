// Optional basic auth for the whole dashboard (user "guru", password DASHBOARD_PASSWORD).
import { NextRequest, NextResponse } from "next/server";

export function middleware(req: NextRequest) {
  const pass = process.env.DASHBOARD_PASSWORD;
  if (!pass) return NextResponse.next();
  const auth = req.headers.get("authorization") || "";
  const [scheme, value] = auth.split(" ");
  if (scheme === "Basic" && value) {
    const [user, pw] = atob(value).split(":");
    if (user === "guru" && pw === pass) return NextResponse.next();
  }
  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Guru Line"' },
  });
}

export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };

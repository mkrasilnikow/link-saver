import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE = "ls_auth";

// Public paths that must stay accessible without auth
const PUBLIC_PATHS = ["/login", "/api/auth", "/api/webhook", "/api/export"];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  const token = req.cookies.get(AUTH_COOKIE)?.value;
  const secret = process.env.AUTH_SECRET;

  if (!secret || token !== secret) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

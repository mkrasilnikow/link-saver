import { NextRequest, NextResponse } from "next/server";

const AUTH_COOKIE = "ls_auth";

export async function POST(req: NextRequest) {
  const { password } = await req.json();
  const secret = process.env.AUTH_SECRET;
  const correctPassword = process.env.AUTH_PASSWORD;

  if (!secret || !correctPassword) {
    return NextResponse.json({ error: "AUTH_SECRET or AUTH_PASSWORD not configured" }, { status: 500 });
  }

  if (password !== correctPassword) {
    return NextResponse.json({ error: "Неверный пароль" }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set(AUTH_COOKIE, secret, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  return res;
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.delete(AUTH_COOKIE);
  return res;
}

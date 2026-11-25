import { NextRequest, NextResponse } from "next/server";

const adminSessionCookie = process.env.ADMIN_SESSION_COOKIE_NAME?.trim() || "workbit_admin_session";

export function proxy(request: NextRequest) {
  if (request.cookies.has(adminSessionCookie)) {
    return NextResponse.redirect(new URL("/admin", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard", "/dashboard/:path*"],
};

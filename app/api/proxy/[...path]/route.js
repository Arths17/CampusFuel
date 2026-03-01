import { NextResponse } from "next/server";

const BACKEND = (
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");

async function proxy(request, { params }) {
  const { path } = await params;
  const pathStr = Array.isArray(path) ? path.join("/") : path;
  const url = new URL(request.url);
  const target = `${BACKEND}/api/${pathStr}${url.search}`;

  // Forward request headers, add ngrok bypass
  const headers = new Headers(request.headers);
  headers.set("ngrok-skip-browser-warning", "true");
  headers.delete("host");

  let body = undefined;
  const method = request.method;
  if (!["GET", "HEAD"].includes(method)) {
    body = await request.arrayBuffer();
  }

  try {
    const res = await fetch(target, {
      method,
      headers,
      body: body ? body : undefined,
      // @ts-ignore
      duplex: "half",
    });

    const resHeaders = new Headers(res.headers);
    resHeaders.delete("transfer-encoding");

    return new NextResponse(res.body, {
      status: res.status,
      headers: resHeaders,
    });
  } catch (err) {
    console.error(`Proxy error → ${target}:`, err);
    return NextResponse.json(
      { success: false, error: "Backend unreachable" },
      { status: 502 }
    );
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;

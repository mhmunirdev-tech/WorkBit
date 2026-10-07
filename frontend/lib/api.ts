const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? (
  process.env.NODE_ENV === "production" ? "/api/v1" : "http://localhost:8000/api/v1"
);

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function statusMessage(status: number): string {
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You do not have permission to view this information.";
  if (status === 404) return "This information is no longer available.";
  if (status === 409) return "This request conflicts with the current account state.";
  if (status === 422) return "Some information was not accepted. Please review it and try again.";
  if (status === 429) return "Too many requests. Please wait a moment and try again.";
  if (status >= 500) return "The service is temporarily unavailable. Please try again shortly.";
  return "The request could not be completed.";
}

function redirectToLogin(): void {
  if (typeof window === "undefined" || window.location.pathname === "/login") return;
  const returnTo = `${window.location.pathname}${window.location.search}`;
  if (!returnTo.startsWith("/") || returnTo.startsWith("//")) return;
  const query = new URLSearchParams({ returnTo });
  window.location.replace(`/login?${query.toString()}`);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15_000);

  try {
    const response = await fetch(`${apiUrl}${path}`, {
      ...init,
      signal: init.signal ?? controller.signal,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...init.headers,
      },
    });

    if (!response.ok) {
      let message = statusMessage(response.status);
      let code: string | undefined;
      try {
        const body: unknown = await response.json();
        if (body && typeof body === "object") {
          const error = (body as { error?: { code?: unknown; message?: unknown } }).error;
          if (typeof error?.message === "string") message = error.message;
          if (typeof error?.code === "string") code = error.code;
        }
      } catch {
        // Keep the status-specific message when an error response has no JSON body.
      }

      if (response.status === 401) redirectToLogin();
      throw new ApiError(message, response.status, code);
    }

    if (response.status === 204) return undefined as T;

    try {
      return (await response.json()) as T;
    } catch {
      throw new ApiError("The service returned an invalid response.", response.status);
    }
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError("The request timed out. Please try again.", 408);
    }
    if (error instanceof TypeError) {
      throw new ApiError("Unable to reach WorkBit. Check your connection and try again.", 0);
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

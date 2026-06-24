import type { ApiError } from "./types";

const BASE = "/api";

class ApiClientError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiClientError";
    this.status = status;
    this.detail = detail;
  }
}

function getCsrfToken(): string | null {
  const meta = document.querySelector<HTMLMetaElement>(
    'meta[name="csrf-token"]',
  );
  return meta?.content ?? null;
}

/** Fetch the backend homepage to establish CSRF token in session. */
async function bootstrapCsrfToken(): Promise<string | null> {
  try {
    const resp = await fetch("/", { credentials: "same-origin" });
    if (!resp.ok) return null;
    const html = await resp.text();
    const match = html.match(
      /<meta\s+name="csrf-token"\s+content="([^"]*)"/i,
    );
    if (match?.[1]) {
      const token = match[1];
      const meta = document.createElement("meta");
      meta.name = "csrf-token";
      meta.content = token;
      document.head.appendChild(meta);
      return token;
    }
    return null;
  } catch {
    return null;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const url = path.startsWith("/") ? `${BASE}${path}` : `${BASE}/${path}`;
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  // Attach CSRF token for state-changing requests
  if (method !== "GET" && method !== "HEAD") {
    const csrf = getCsrfToken();
    if (csrf) {
      headers["X-CSRFToken"] = csrf;
    }
  }

  const res = await fetch(url, {
    method,
    headers,
    credentials: "same-origin",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 403) {
    const text = await res.text();
    if (text.includes("CSRF")) {
      // Bootstrap CSRF token and retry once
      const token = await bootstrapCsrfToken();
      if (token) {
        headers["X-CSRFToken"] = token;
        const retry = await fetch(url, {
          method,
          headers,
          credentials: "same-origin",
          body: body !== undefined ? JSON.stringify(body) : undefined,
        });
        if (!retry.ok) {
          const err = (await retry.json().catch(() => ({
            detail: retry.statusText,
            status_code: retry.status,
          }))) as ApiError;
          throw new ApiClientError(retry.status, err.detail);
        }
        return (await retry.json()) as T;
      }
    }
  }

  if (!res.ok) {
    const err = (await res.json().catch(() => ({
      detail: res.statusText,
      status_code: res.status,
    }))) as ApiError;
    throw new ApiClientError(res.status, err.detail);
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as T;

  return (await res.json()) as T;
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>("GET", path);
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("POST", path, body);
  },

  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PATCH", path, body);
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PUT", path, body);
  },

  delete<T>(path: string): Promise<T> {
    return request<T>("DELETE", path);
  },

  bootstrapCsrfToken,
};

export { ApiClientError };

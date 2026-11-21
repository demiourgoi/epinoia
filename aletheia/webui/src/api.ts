export type ChangeKind = "created" | "deleted" | "modified";

export interface FileView {
  path: string;
  kind: ChangeKind;
  changed: boolean;
}

export interface ReviewFile extends FileView {
  baseline: string | null;
  current: string | null;
  diff: string;
}

export interface ReviewPayload {
  url: string;
  files: ReviewFile[];
}

export type Paths = { paths: string[] };

async function jsonOrThrow<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { error?: string };
    throw new Error(body.error ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchReview(): Promise<ReviewPayload> {
  return fetch("/api/review").then((r) => jsonOrThrow<ReviewPayload>(r));
}

export function addToBaseline(paths: string[]): Promise<Record<string, unknown>> {
  return request("/api/baseline/files", "POST", { paths });
}

export function removeFromBaseline(paths: string[]): Promise<Record<string, unknown>> {
  return request("/api/baseline/files", "DELETE", { paths });
}

export function rollback(paths: string[]): Promise<Record<string, unknown>> {
  return request("/api/rollback", "POST", { paths });
}

export function saveContent(path: string, content: string): Promise<Record<string, unknown>> {
  return request("/api/content", "POST", { path, content });
}

async function request(url: string, method: string, body: object): Promise<Record<string, unknown>> {
  const response = await fetch(url, {
    method,
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  return jsonOrThrow<Record<string, unknown>>(response);
}

export type FileStatus = "pending" | "edited" | "approved" | "rejected";
export type ChangeKind = "created" | "deleted" | "modified";

export interface FileSummary {
  index: number;
  path: string;
  kind: ChangeKind;
  status: FileStatus;
  reverted: boolean;
}

export interface FileReview extends FileSummary {
  baseline: string | null;
  current: string | null;
  diff: string;
}

export interface SessionPayload {
  session_id: string;
  status: "pending" | "all_approved" | "all_rejected" | "mixed";
  files: FileReview[];
}

export async function fetchSession(sessionId: string): Promise<SessionPayload> {
  const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`);
  if (!response.ok) {
    throw new Error((await response.json()).error ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as SessionPayload;
}

export async function decideFile(
  sessionId: string,
  index: number,
  action: "approve" | "reject" | "save_edit",
  content?: string,
): Promise<SessionPayload> {
  return postJson(`/api/sessions/${encodeURIComponent(sessionId)}/files/${index}/decision`, {
    action,
    content,
  });
}

export async function decideAll(
  sessionId: string,
  action: "approve" | "reject",
): Promise<SessionPayload> {
  return postJson(`/api/sessions/${encodeURIComponent(sessionId)}/decision`, { action });
}

async function postJson(url: string, body: object): Promise<SessionPayload> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error((await response.json()).error ?? `HTTP ${response.status}`);
  }
  return (await response.json()) as SessionPayload;
}

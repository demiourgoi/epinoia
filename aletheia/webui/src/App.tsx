import { useCallback, useEffect, useState } from "react";
import {
  SessionPayload,
  decideAll,
  decideFile,
  fetchSession,
  FileReview,
} from "./api";
import { DiffPane } from "./DiffPane";

function sessionFromUrl(): string {
  const match = window.location.pathname.match(/^\/s\/(.+)$/);
  return match ? decodeURIComponent(match[1]) : "";
}

const statusLabels: Record<string, string> = {
  pending: "Pending",
  edited: "Edited",
  approved: "Approved",
  rejected: "Rejected (reverted on disk)",
};

export function App() {
  const sessionId = sessionFromUrl();
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(0);
  const [editedDoc, setEditedDoc] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const payload = await fetchSession(sessionId);
      setSession(payload);
      setError("");
    } catch (cause) {
      setError(String(cause instanceof Error ? cause.message : cause));
    }
  }, [sessionId]);

  useEffect(() => {
    if (sessionId) void refresh();
  }, [sessionId, refresh]);

  if (!sessionId) {
    return (
      <main className="page">
        <h1>Aletheia</h1>
        <p>Open the review URL your agent shared (it looks like /s/&lt;session&gt;).</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page">
        <h1>Aletheia</h1>
        <p className="error">{error}</p>
      </main>
    );
  }

  if (!session) return <main className="page">Loading…</main>;

  const file: FileReview | undefined = session.files[selected];
  const decided = session.files.length > 0 && session.files.every((f) => f.status === "approved" || f.status === "rejected");

  const act = (action: "approve" | "reject" | "save_edit", content?: string) => {
    if (!file || busy) return;
    setBusy(true);
    decideFile(sessionId, file.index, action, content)
      .then(() => {
        setEditedDoc(null);
        return refresh();
      })
      .catch((cause: Error) => setError(cause.message))
      .finally(() => setBusy(false));
  };

  const actAll = (action: "approve" | "reject") => {
    if (busy) return;
    setBusy(true);
    decideAll(sessionId, action)
      .then(refresh)
      .catch((cause: Error) => setError(cause.message))
      .finally(() => setBusy(false));
  };

  return (
    <main className="page" data-testid="session">
      <header>
        <h1>Aletheia — review changes</h1>
        <span className={`status status-${session.status}`}>{session.status}</span>
        <button disabled={busy} onClick={() => void actAll("approve")}>Approve all</button>
        <button disabled={busy} className="danger" onClick={() => void actAll("reject")}>
          Reject all
        </button>
      </header>
      <p>
        Approve keeps the file on disk as shown. Edit the right pane and "Save
        edit" to tweak it before approving. Reject rolls the file back to its
        pre-agent content on disk. {""}
        {decided && "All files have been decided."}
      </p>
      <div className="layout">
        <nav className="files">
          <ul>
            {session.files.map((entry, index) => (
              <li
                key={entry.index}
                className={`${index === selected ? "selected" : ""} s-${entry.status}`}
                onClick={() => {
                  setSelected(index);
                  setEditedDoc(null);
                }}
              >
                <span className="path" title={entry.path}>
                  {entry.path}
                </span>
                <span className="badge">{statusLabels[entry.status] ?? entry.status}</span>
              </li>
            ))}
          </ul>
        </nav>
        {file && (
          <section className="detail">
            <div className="detail-actions">
              <button disabled={busy} onClick={() => act("approve")}>Approve</button>
              <button
                disabled={busy}
                className="danger"
                onClick={() => act("reject")}
              >
                Reject
              </button>
              <button
                disabled={busy || editedDoc === null}
                onClick={() => editedDoc !== null && act("save_edit", editedDoc)}
              >
                Save edit
              </button>
            </div>
            <DiffPane
              path={file.path}
              baseline={file.baseline}
              current={file.current}
              onEdit={setEditedDoc}
            />
          </section>
        )}
      </div>
    </main>
  );
}

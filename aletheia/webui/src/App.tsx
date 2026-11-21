import { useCallback, useEffect, useState } from "react";
import {
  ReviewPayload,
  removeFromBaseline,
  rollback,
  saveContent,
  fetchReview,
} from "./api";
import { DiffPane } from "./DiffPane";

const kindLabels: Record<string, string> = {
  created: "Created",
  deleted: "Deleted",
  modified: "Modified",
};

export function App() {
  const [review, setReview] = useState<ReviewPayload | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(0);
  const [editedDoc, setEditedDoc] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const payload = await fetchReview();
      setReview(payload);
      setError("");
    } catch (cause) {
      setError(String(cause instanceof Error ? cause.message : cause));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const act = async (action: () => Promise<Record<string, unknown>>) => {
    if (busy) return;
    setBusy(true);
    try {
      await action();
      setEditedDoc(null);
      await refresh();
    } catch (cause) {
      setError(String(cause instanceof Error ? cause.message : cause));
    } finally {
      setBusy(false);
    }
  };

  const file = review?.files[selected];
  const allPaths = review ? review.files.map((f) => f.path) : [];

  return (
    <main className="page">
      <header>
        <h1>Aletheia — review changes</h1>
        <span className="status">
          {review ? `${review.files.length} file${review.files.length === 1 ? "" : "s"} under review` : "…"}
        </span>
        <button disabled={busy} onClick={() => void refresh()}>Refresh</button>
        <button
          disabled={busy || allPaths.length === 0}
          onClick={() => void act(() => removeFromBaseline(allPaths))}
        >
          Approve all
        </button>
        <button
          className="danger"
          disabled={busy || allPaths.length === 0}
          onClick={() => void act(() => rollback(allPaths))}
        >
          Reject all
        </button>
      </header>
      <p>
        Approve adopts the file as it is on disk; Reject restores its
        pre-agent content on disk. Both end the file's review. The right
        pane is editable: tweak the proposal and "Save edit" writes your
        version to the working directory.
      </p>
      {error && <p className="error">{error}</p>}
      {review && review.files.length === 0 && (
        <p className="empty">
          Nothing is under review. The agent records files into the
          baseline before editing them — the list here refreshes live.
        </p>
      )}
      <div className="layout">
        <nav className="files">
          <ul>
            {(review?.files ?? []).map((entry, index) => (
              <li
                key={entry.path}
                className={index === selected ? "selected" : ""}
                onClick={() => {
                  setSelected(index);
                  setEditedDoc(null);
                }}
              >
                <span className="path" title={entry.path}>
                  {entry.path}
                </span>
                <span className="badge">
                  {kindLabels[entry.kind] ?? entry.kind}
                  {entry.changed ? "" : " · unchanged"}
                </span>
              </li>
            ))}
          </ul>
        </nav>
        {file && (
          <section className="detail">
            <div className="detail-actions">
              <button disabled={busy} onClick={() => void act(() => removeFromBaseline([file.path]))}>
                Approve
              </button>
              <button className="danger" disabled={busy} onClick={() => void act(() => rollback([file.path]))}>
                Reject
              </button>
              <button
                disabled={busy || editedDoc === null}
                onClick={() =>
                  editedDoc !== null && void act(() => saveContent(file.path, editedDoc))
                }
              >
                Save edit
              </button>
              {editedDoc !== null && <span className="pending-edit">unsaved edit</span>}
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

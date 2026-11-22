import { useCallback, useEffect, useRef, useState } from "react";
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
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [renderTick, setRenderTick] = useState(0);
  const [busy, setBusy] = useState(false);
  const diskAtLastRender = useRef<Record<string, string | null>>({});

  const refresh = useCallback(async () => {
    try {
      const payload = await fetchReview();
      setReview(payload);
      setError("");
      // Keep unsaved edits alive across refreshes: only remount the diff
      // pane when the selected file actually changed on disk, so a live
      // agent edit does not silently drop what the user typed. Drafts for
      // files that left review (approve/reject) are pruned too.
      setDrafts((current) => {
        const alive = new Set(payload.files.map((entry) => entry.path));
        const stale = Object.keys(current).filter((path) => !alive.has(path));
        if (stale.length === 0) return current;
        const next = { ...current };
        for (const path of stale) delete next[path];
        return next;
      });
      const current = payload.files[selected];
      if (current) {
        const before = diskAtLastRender.current[current.path];
        if (before !== undefined && before !== current.current) {
          setRenderTick((tick) => tick + 1);
        }
        diskAtLastRender.current[current.path] = current.current;
      }
    } catch (cause) {
      setError(String(cause instanceof Error ? cause.message : cause));
    }
  }, [selected]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const act = async (
    action: () => Promise<Record<string, unknown>>,
    donePath?: string,
  ) => {
    if (busy) return;
    setBusy(true);
    try {
      await action();
      if (donePath) {
        setDrafts((current) => {
          const next = { ...current };
          delete next[donePath];
          return next;
        });
      }
      await refresh();
    } catch (cause) {
      setError(String(cause instanceof Error ? cause.message : cause));
    } finally {
      setBusy(false);
    }
  };

  const file = review?.files[selected];
  const draft = file ? drafts[file.path] : undefined;
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
                onClick={() => setSelected(index)}
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
                disabled={busy || draft === undefined}
                onClick={() =>
                  void act(() => saveContent(file.path, draft as string), file.path)
                }
              >
                Save edit
              </button>
              {draft !== undefined && <span className="pending-edit">unsaved edit</span>}
            </div>
            <DiffPane
              key={`${file.path}:${renderTick}`}
              baseline={file.baseline}
              current={draft ?? file.current}
              onEdit={(doc: string) =>
                setDrafts((current) => ({ ...current, [file.path]: doc }))
              }
            />
          </section>
        )}
      </div>
    </main>
  );
}

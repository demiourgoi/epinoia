import { useEffect, useRef } from "react";
import { EditorState } from "@codemirror/state";
import { EditorView } from "@codemirror/view";
import { MergeView } from "@codemirror/merge";

interface DiffPaneProps {
  baseline: string | null;
  current: string | null;
  onEdit?: (doc: string) => void;
}

/** Side-by-side editable diff: pane A is the baseline, pane B the proposal. */
export function DiffPane({ baseline, current, onEdit }: DiffPaneProps) {
  const container = useRef<HTMLDivElement>(null);
  const onEditRef = useRef(onEdit);

  onEditRef.current = onEdit;

  // Mount-only build: App remounts this component (key includes a render
  // tick) when the selected file changes or its on-disk content changed,
  // so keystrokes never rebuild the editor and drop the cursor or unsaved
  // edits.
  useEffect(() => {
    if (!container.current) return;
    const merge = new MergeView({
      a: {
        doc: baseline ?? "",
        extensions: [EditorState.readOnly.of(true), EditorView.editable.of(false)],
      },
      b: {
        doc: current ?? "",
        extensions: [
          EditorView.updateListener.of((update) => {
            if (update.docChanged) onEditRef.current?.(update.state.doc.toString());
          }),
        ],
      },
      highlightChanges: true,
      gutter: true,
      parent: container.current,
    });
    return () => merge.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <div className="diff" ref={container} />;
}

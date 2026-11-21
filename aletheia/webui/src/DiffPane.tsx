import { useEffect, useRef, useState } from "react";
import { EditorState } from "@codemirror/state";
import { EditorView, highlightActiveLine } from "@codemirror/view";
import { LanguageDescription, LanguageSupport } from "@codemirror/language";
import { languages } from "@codemirror/language-data";
import { MergeView } from "@codemirror/merge";

interface DiffPaneProps {
  path: string;
  baseline: string | null;
  current: string | null;
  onEdit?: (doc: string) => void;
}

/** Side-by-side editable diff: pane A is the baseline, pane B the proposal. */
export function DiffPane({ path, baseline, current, onEdit }: DiffPaneProps) {
  const container = useRef<HTMLDivElement>(null);
  const onEditRef = useRef(onEdit);
  const [language, setLanguage] = useState<LanguageSupport | null>(null);

  onEditRef.current = onEdit;

  // Load the language by filename (Java, Python, TypeScript, ...).
  useEffect(() => {
    setLanguage(null);
    const description = LanguageDescription.matchFilename(languages, path);
    if (!description) return;
    let cancelled = false;
    void description.load().then((support: LanguageSupport) => {
      if (!cancelled) setLanguage(support);
    });
    return () => {
      cancelled = true;
    };
  }, [path]);

  useEffect(() => {
    if (!container.current) return;
    const languageExtension = language ? [language] : [];
    const merge = new MergeView({
      a: {
        doc: baseline ?? "",
        extensions: [EditorState.readOnly.of(true), EditorView.editable.of(false), languageExtension],
      },
      b: {
        doc: current ?? "",
        extensions: [
          languageExtension,
          highlightActiveLine(),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) onEditRef.current?.(update.state.doc.toString());
          }),
        ],
      },
      highlightChanges: true,
      gutter: true,
      parent: container.current,
    });
    // Rebuilds only on language load; document switches and live refreshes
    // remount this component (key includes a render tick from App), so
    // keystrokes never rebuild the editor and drop the cursor or unsaved
    // edits.
    return () => merge.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [language]);

  return <div className="diff" ref={container} />;
}

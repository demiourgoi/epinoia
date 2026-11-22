# Research: web diff editors and syntax highlighting options

Sources:
- [web-tree-sitter](https://www.npmjs.com/package/web-tree-sitter) and its
  [README](https://github.com/tree-sitter/tree-sitter/blob/master/lib/binding_web/README.md)
- [CodeMirror 6 merge view](https://codemirror.net/examples/merge/)
- [@codemirror/language-data](https://www.npmjs.com/package/@codemirror/language-data)
- [@uiw/react-codemirror](https://www.npmjs.com/package/@uiw/react-codemirror)

## Option matrix

| Approach | Diff view | Editing | Language coverage | Packaging cost | Correctness risk |
| --- | --- | --- | --- | --- | --- |
| Tree-sitter WASM (`web-tree-sitter` + grammar `.wasm` + `highlights.scm`) | must be built by hand (diff + custom highlight pipeline) | separate editor still needed | huge, but each grammar must be shipped/fetched | high: wasm per grammar, query files, custom CM glue | glue is ours; unmaintained |
| Monaco | built-in diff editor, Monarch/TextMate grammars | good | good | heavy bundle, VS Code-ish | no tree-sitter; large |
| CodeMirror 6 + `@codemirror/merge` + `@codemirror/language-data` | official `MergeView`: side-by-side, chunk highlighting, editable right pane | built-in (that's CM's core) | covers Java, Python, JS/TS, C/C++, Go, Rust, etc. via Lezer/legacy modes, auto by file name | one dependency set, lazy mode loading | proven playground-grade stack |

## Decision

CodeMirror 6 wins for a v1 whose core value is *review/edit/reject a diff*:

- `@codemirror/merge` gives the Zed-like editable side-by-side diff with
  approve-style green/red chunk highlighting for free.
- `@codemirror/language-data` resolves a language from the filename and
  lazy-loads its mode — meets "most popular programming languages" with zero
  per-language maintenance.
- Vite + React + TypeScript: tiny config, fast builds, static output that
  drops into the Python package.

Tree-sitter remains the documented upgrade path: swap the language facet
provider for a `web-tree-sitter`-backed highlight source; nothing else in the
app depends on the language implementation.

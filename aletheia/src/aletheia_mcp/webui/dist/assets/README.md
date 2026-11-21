# What these files are

Every file in this directory is **generated build output**, produced by
running Vite over the TypeScript sources of the review web UI
(`aletheia/webui/` — `make webui` runs `npm ci && npm run build`). Nothing
here is hand-written or copied from another repository: regenerating the
build reproduces equivalent files (only the content-hash suffixes in the
names change when the input changes).

- `index-*.js` — the application entry chunk (React app: review page,
  CodeMirror merge view, live-refetch logic) written for Aletheia.
- `<language>-*.js` (~110 files, e.g. `clike`, `python`, `rust`,
  `commonlisp`) — one **lazy-loaded syntax chunk per programming language**,
  emitted because the app uses `@codemirror/language-data`, which indexes
  ~130 grammars and only loads the one matching the reviewed file's name.
  Opening a review of a Java and a Python file downloads only `clike` +
  `python` plus the shared chunks, not the whole pack.
- `dist-*.js` — Vite's shared dependency chunks (CodeMirror core, Lezer,
  the `@uiw/react-codemirror` glue, React). The `dist` prefix is Vite's
  module-name-based label, not provenance.
- `index-*.css` — the compiled stylesheet of the app.
- The hash suffixes (e.g. `-B4CMkyY2`) are Vite content hashes.

These chunks embed minified code from MIT-licensed third-party libraries;
per the MIT license, their copyright notices are preserved in
`../LICENSE` (also shipped inside the published wheel) and recorded in the
repository's `THIRD-PARTY-NOTICES.md`:

| Library | Upstream | Copyright |
| --- | --- | --- |
| `@codemirror/*`, `@lezer/*` (incl. legacy-modes) | https://codemirror.net / https://lezer.codemirror.net | Copyright (C) 2018-2022 by Marijn Haverbeke <marijn@haverbeke.berlin> and others |
| `react`, `react-dom` | https://react.dev | Copyright (c) Facebook, Inc. and its affiliates. |
| `@uiw/react-codemirror` | https://github.com/uiwjs/react-codemirror | MIT per its package (author: kenny wang <wowohoo@qq.com>) |

Build tooling (which does not ship in the output): Vite (MIT),
`@vitejs/plugin-react` (MIT), TypeScript (Apache-2.0).

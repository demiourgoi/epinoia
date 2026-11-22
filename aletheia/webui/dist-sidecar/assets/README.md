# What these files are

Every file in this directory is **generated build output**, produced by
running Vite over the TypeScript sources of the review web UI
(`aletheia/webui/` — `make webui` runs `npm ci && npm run build`). Nothing
here is hand-written or copied from another repository: regenerating the
build reproduces equivalent files (only the content-hash suffixes in the
names change when the input changes).

There are only two files:

- `index-*.js` — the single application chunk: the React review page
  (file list, approve/reject/save-edit actions) plus CodeMirror 6's
  merge view that renders the side-by-side diff with changed-chunk
  highlighting.
- `index-*.css` — the compiled stylesheet (including the compaction
  overrides for CodeMirror's gutters and content padding).

Earlier revisions emitted ~120 chunks because `@codemirror/language-data`
lazy-loaded one grammar per language; language-dependent syntax
highlighting was dropped from the MVP (see the PDD design revision 3) and
with it the whole per-language chunk set.

These files embed minified code from MIT-licensed third-party libraries;
per the MIT license, their copyright notices are preserved in `../LICENSE`
(also shipped inside the published wheel) and recorded in the repository's
`THIRD-PARTY-NOTICES.md`:

| Library | Upstream | Copyright |
| --- | --- | --- |
| `@codemirror/merge`, `@codemirror/state`, `@codemirror/view` | https://codemirror.net | Copyright (C) 2018-2022 by Marijn Haverbeke <marijn@haverbeke.berlin> and others |
| `react`, `react-dom` | https://react.dev | Copyright (c) Facebook, Inc. and its affiliates. |

Build tooling (which does not ship in the output): Vite (MIT),
`@vitejs/plugin-react` (MIT), TypeScript (Apache-2.0).

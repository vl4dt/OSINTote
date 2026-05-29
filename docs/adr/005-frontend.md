# ADR-005: Frontend Architecture

**Status**: Accepted
**Date**: 2026-05-28

## Context

OSINTote needs a Web UI for managing targets, running tasks, and viewing results. We needed to choose a framework and architecture.

## Decision

Use **SvelteKit 2.x** with **Svelte 5 runes mode** and **Tailwind CSS 4** for a dark-themed, 3-panel OSINT interface.

### Architecture

```
frontend/
├── src/
│   ├── lib/
│   │   ├── api/mock.ts          # Mock API service
│   │   ├── types.ts             # TypeScript type definitions
│   │   └── lazyRoutes.ts        # Dynamic route loading
│   ├── routes/
│   │   ├── +layout.svelte       # 3-panel shell (sidebar + main + details)
│   │   ├── +page.svelte         # Redirect to dashboard
│   │   ├── dashboard/+page.svelte
│   │   ├── targets/+page.svelte
│   │   ├── tasks/+page.svelte
│   │   └── results/+page.svelte
│   └── app.css                  # Tailwind directives
├── static/
└── tailwind.config.js
```

### Theme

GitHub Dark-inspired OSINT aesthetic:
- Backgrounds: `#0d1117`, `#161b22`, `#21262d`
- Borders: `#30363d`
- Text: `#c9d1d9`, `#8b949e`
- Accent: `#58a6ff` (blue), `#f85149` (red), `#3fb950` (green)
- Monospace: Fira Mono for technical data

## Alternatives Considered

- **React + Vite**: More popular, but Svelte's compiler optimizations give better performance
- **Vue + Nuxt**: Similar to Svelte, but Svelte 5 runes provide a cleaner reactive model
- **Pure HTML + Alpine.js**: Simpler, but not suitable for a complex interactive dashboard

## Consequences

- **Positive**: Fast initial load (Svelte compiles away framework overhead), reactive runes model is intuitive, Tailwind 4 reduces CSS complexity
- **Negative**: Svelte ecosystem is smaller than React's
- **Mitigation**: Core functionality is framework-agnostic; the API backend is RESTful and can be consumed by any frontend

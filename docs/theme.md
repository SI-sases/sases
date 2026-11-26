# Theme

SASES supports light, dark and auto themes using the existing design tokens in
`static/css/variables.css`.

## UI entry

The theme selector is inside the existing **capability capsule settings** menu:

```text
消息输入框上方 ⋯ → 主题
```

No new page or separate settings screen is added.

## Options

```text
auto   follow the operating system
light  light tokens
dark   dark token overrides
```

## Storage

```text
localStorage: sases_theme
html[data-theme="light|dark"]
```

## Scope

- Only token values change; layout and components are unchanged.
- Plugins should use `--color-*`, `--bg-*`, `--text-*` tokens instead of
  literal colors.
- A page refresh is not required after switching.

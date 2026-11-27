"""CLI entry point for the local main AGI (shadow mode in P0)."""
from .runtime import main

if __name__ == "__main__":
    raise SystemExit(main())

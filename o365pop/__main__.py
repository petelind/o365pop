"""Allow ``python -m o365pop`` to run the operator CLI."""

from o365pop.cli import main

if __name__ == "__main__":
    raise SystemExit(main())

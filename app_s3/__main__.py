"""Punto de entrada de la aplicación."""

from app_s3.bootstrap import run


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()

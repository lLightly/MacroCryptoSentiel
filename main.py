from __future__ import annotations

from src.services.updater import update_all_data


def main() -> None:
    update_all_data()
    print("✓ All data updated.")


if __name__ == "__main__":
    main()
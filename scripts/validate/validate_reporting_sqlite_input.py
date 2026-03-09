#!/usr/bin/env python3
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: validate_reporting_sqlite_input.py <db.sqlite> <as_of_date>')
        return 1
    db_path = Path(sys.argv[1])
    as_of_date = sys.argv[2]
    if not db_path.exists():
        print(f'validation failed: sqlite file not found: {db_path}')
        return 2
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='trades'")
        if cursor.fetchone() is None:
            print('validation failed: trades table missing')
            return 3
        closed_count = conn.execute(
            "SELECT COUNT(*) FROM trades WHERE is_open = 0 AND close_date >= ? AND close_date <= ?",
            (f'{as_of_date}T00:00:00+00:00', f'{as_of_date}T23:59:59+00:00')
        ).fetchone()[0]
        open_count = conn.execute("SELECT COUNT(*) FROM trades WHERE is_open = 1").fetchone()[0]
    finally:
        conn.close()
    print(f'[OK] sqlite reporting input valid: closed={closed_count}, open={open_count}, date={as_of_date}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

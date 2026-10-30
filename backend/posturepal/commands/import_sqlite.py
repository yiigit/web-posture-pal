"""One-way, non-destructive import into an empty MySQL application database."""
import argparse
import sqlite3
from pathlib import Path
from contextlib import closing
from sqlalchemy import select, func
from posturepal.shared.infrastructure.database import Database, schema


def import_sqlite(source, destination):
    if destination.engine.dialect.name!='mysql':
        raise ValueError('The destination must be MySQL')
    source=Path(source).resolve()
    if not source.is_file():
        raise ValueError('SQLite source file does not exist')
    logical=[table for table in schema.sorted_tables if table.name!='application_locks']
    # Read-only, single snapshot; no source tables or credentials are logged.
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as old:
        old.row_factory=sqlite3.Row
        old.execute('BEGIN')
        available={row[0] for row in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        with destination.connection() as db:
            db.lock()
            if any(db.connection.scalar(select(func.count()).select_from(table)) for table in logical):
                raise ValueError('Destination contains application data; import requires an empty database')
            count=0
            for table in logical:
                if table.name not in available:
                    continue
                cursor=old.execute('SELECT * FROM "'+table.name+'"')
                while rows:=cursor.fetchmany(250):
                    payload=[{key:row[key] for key in table.columns.keys() if key in row.keys()} for row in rows]
                    db.connection.execute(table.insert(),payload)
                    count+=len(payload)
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    args=parser.parse_args()
    try:
        count=import_sqlite(args.source,Database.configured())
    except ValueError as error:
        raise SystemExit(str(error)) from None
    print(f'Imported {count} records. Source was left unchanged.')


if __name__=='__main__':
    main()

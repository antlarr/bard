#!/usr/bin/python3
# This is a script to copy the contents of all tables
# from one database to another
from bard.db.core import metadata
from sqlalchemy import create_engine
# from sqlalchemy.schema import CreateTable
# import re
import sqlalchemy.dialects
import sys
import sqlalchemy_utils


def processCreateTable(table_name, table):
    if table.schema:
        old_schema_table_name = f'old.{table.schema}_{table.name}'
    else:
        old_schema_table_name = f'old.{table.name}'
    schema = table.schema if table.schema else 'public'

    print(f'CREATE FOREIGN TABLE {old_schema_table_name} (')
    lines = []
    for col in table.columns:
        if isinstance(col.type, sqlalchemy_utils.types.uuid.UUIDType):
            coltype = 'TEXT'
        else:
            coltype = col.type.compile(
                sqlalchemy.dialects.postgresql.dialect())

        lines.append(f'       {col.name} {coltype}')
    print(',\n'.join(lines) + ') SERVER foreign_server '
          f'OPTIONS(schema_name \'{schema}\', '
          f'table_name \'{table.name}\');\n')

    if table_name in ['album_release', 'artists_mb', 'artist_credits_mb']:
        print(f'ALTER TABLE {table_name} DISABLE TRIGGER ALL;')
        last_command = f'ALTER TABLE {table_name} ENABLE TRIGGER ALL;'
    else:
        last_command = None

    col_names = []
    sel_col_names = []
    for col in table.columns:
        col_names.append(col.name)
        if isinstance(col.type, sqlalchemy_utils.types.uuid.UUIDType):
            sel_col_names.append(f'uuid({col.name})')
        else:
            sel_col_names.append(col.name)

    values = ",\n  ".join(col_names)
    sel_cols = ",\n  ".join(sel_col_names)

    print(f'\nINSERT INTO {table_name} ({values}) '
          f'SELECT {sel_cols} from {old_schema_table_name};\n')

    print(f'DROP FOREIGN TABLE {old_schema_table_name};\n')

    return last_command


def migrate_sequences_status(engine):
    sql = ('select schemaname, sequencename, last_value '
           'from pg_catalog.pg_sequences where last_value is not null')

    result = engine.execute(sql)
    for row in result.fetchall():
        seq = f'{row["schemaname"]}.{row["sequencename"]}'
        txt = f'SELECT setval(\'{seq}\', {row["last_value"]});'
        print(txt)


try:
    dbname = sys.argv[1]
    user = sys.argv[2]
except IndexError:
    print('Usage: migrate_database.py <dbname> <user> [password]')
    sys.exit(1)

try:
    password = sys.argv[3]
except IndexError:
    password = input('Enter database password:')

print('CREATE SCHEMA old;')
print('CREATE EXTENSION postgres_fdw;')
print(f'''CREATE SERVER foreign_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (dbname '{dbname}');''')

print(f'''CREATE USER MAPPING FOR bard
    SERVER foreign_server
    OPTIONS (user '{user}', password '{password}');''')

uri = f'postgresql://{user}:{password}@/{dbname}'

last_commands = []
for name, table in metadata.tables.items():
    last_commands.append(processCreateTable(name, table))

for cmd in last_commands:
    if not cmd:
        continue
    print(cmd)

print('\n')

engine = create_engine(f'postgresql://{user}:{password}@/{dbname}')
migrate_sequences_status(engine)

#!/usr/bin/python3
import re
import json
import os.path


def find_matching_parenthesis(text, pos):
    level = 0
    pos = text.find('(', pos)
    if pos == -1:
        return (-1, -1)
    begin_pos = pos
    while pos < len(text):
        if text[pos] == '(':
            level += 1
        elif text[pos] == ')':
            level -= 1
            if level == 0:
                return (begin_pos, pos)
        pos += 1
    return (begin_pos, -1)


def convert_type(t):
    t = t.lower()
    types = [('integer', 'int'),
             ('uuid', 'str'),
             ('varchar', 'str'),
             ('text', 'str'),
             ('char', 'str'),
             ('serial', 'int'),
             ('timestamp', 'datetime'),
             ('smallint', 'int'),
             ('int', 'int'),
             ('boolean', 'bool')]

    for old, new in types:
        if t.startswith(old):
            return new

    print('Type not found for', t, '. Assuming str')
    return 'str'


def extract_column_names(text):
    begin, end = find_matching_parenthesis(text, 0)
    while end != -1:
        text = text[:begin] + text[end + 1:]
        begin, end = find_matching_parenthesis(text, begin)
    keywords = ['check', 'constraint']

    columns = []
    for statement in text.split(','):
        if statement.split()[0] in keywords:
            continue
        s = statement.split()
        colname = s[0]
        coltype = convert_type(s[1])
        columns.append((colname, coltype))

#    columns = [statement.split()[0] for statement in text.split(',')
#               if statement.split()[0] not in keywords]

    return columns


contents = open('CreateTables.sql', 'r').read().lower()
print(contents[:300])
contents = re.sub(r'--.*\n', '\n', contents)
print(contents[:300])

pos = 0
tables = {}
while pos < len(contents):
    begin = contents.find('create table', pos)
    if begin == -1:
        break
    begin_pos, end_pos = find_matching_parenthesis(contents, begin)
    if end_pos == -1:
        break
    table_name = contents[begin + len('create table'):begin_pos].strip()
    columns = extract_column_names(contents[begin_pos + 1:end_pos])
    tables[table_name] = columns
    pos = end_pos + 1

directory = os.path.expanduser('~/.local/share/bard')
filename = os.path.join(directory, 'musicbrainz_schema_importer_names')
with open(filename, 'w') as f:
    f.write(json.dumps(tables, sort_keys=True, indent=4))

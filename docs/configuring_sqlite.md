# How to configure bard to use a sqlite database

By default, you don't have to do anything to use sqlite but if you want to set it up explicitly, you can set the following config options:

```
    "database": "sqlite",
    "database_path": "~/.local/share/bard/music.db",
```

You can set the `database_path` config option to the file to be used for the default schema. Bard will then create it and two
other files as well: One with a `-mb` suffix for the musicbrainz schema and another with an `-analysis` suffix
for the analysis schema (which contains information extracted with the `process-songs` command).

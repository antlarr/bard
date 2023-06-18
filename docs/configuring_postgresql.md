# Install postgresql server

On SUSE/openSUSE systems, you can run:

```
sudo zypper in postgresql-server
```

# Create postgresql user and database

Start a shell as user postgres, since the next commands (createuser and createdb) have to be run as that user (not as root or as your user):

```
sudo su postgres
```

Create a bard user in postgresql (it will request the password) by executing:

```
createuser --pwprompt --createdb --superuser bard
```

Then create the database for user bard:

```
createdb -O bard -U bard bard
```

If the above command fails with an error message like:

```
   createdb: could not connect to database template1: FATAL:  Peer authentication failed for user "bard"
```

You might need to add the following line as the first uncommented line of /var/lib/pgsql/data/pg_hba.conf
and then restart postgresql and rerun the createdb command:

```
    local   all             all                                     md5
```

If you prefer/need to create the user from a sql prompt, you can use:

```
CREATE USER bard WITH PASSWORD 'bard' CREATEDB SUPERUSER CREATEROLE;
CREATE DATABASE bard WITH OWNER bard ENCODING 'UTF8';
```

# Configuring bard to use a postgresql database

Set the following config options in Bard's config file to use postgresql:

```
    "database": "postgresql",
    "database_name" : "bard",
    "database_user" : "bard",
    "database_password" : "yourpassword",
```

The next time you use bard it will create the database schemas automatically.


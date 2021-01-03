# How to configure backups

Bard can help you do backups of your music collection. Doing a backup means copying all files under your `music_paths` directories to a remote computer that can be accessed using ssh.

Bard will keep track of differences between files in your local (main) collection and on the backup.

It's recommended to use ssh-agent to store your ssh key so you don't have to enter your password for every directory that is backed up.

In the most basic usage example, you have your local system (let's assume the hostname is euterpe) and a remote system (with hostname mnemosine). If music_paths is configured like:
```
    "music_paths": [
        "/home/username/Music/unorganized",
        "/home/username/Music/organized"
        "/home/username/Music/unorganized2"
       ]
```

Then you can configure the backup with:

```
    "backups" : {
        "mnemosine" : {
            "" : "remoteuser@mnemosine:/mnt/backup/music/"
        }
    }
```

When you perform the backup, bard will copy the contents of `/home/username/Music/unorganized` from `euterpe` to the directory `/mnt/backup/music/home_username_Music_unorganized` in `mnemosine` and `/home/username/Music/organized` to `/mnt/backup/music/home_username_Music_organized`.

You can also specify different destinations to different source directories with something like:

```
    "backups" : {
        "mnemosine" : {
            "" : "remoteuser@mnemosine:/mnt/backup/music/",
            "/home/username/Music/unorganized2" : "remoteuser@mnemosine:/mnt/backup2/some_other_folder/"
        }
    }
```

In this case the default destination for backups is under `/mnt/backup/music/` but `/home/username/Music/unorganized2` will be backed up to `/mnt/backup2/some_other_folder/home_username_Music_unorganized2`.

# How to perform backups

Just run `bard backup <backupname>`. For example, in the examples above, you would run `bard backup mnemosine`.

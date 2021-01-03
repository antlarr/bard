# Contents

This directory contains the bard plugin and a recommended file naming script
for Picard. It is recommended to install both to organize your music collection
with Picard if you want to use 100% of Bard features. This is specially needed
if you want to use the web user interface of Bard, which only shows music
correctly organized with Picard. Otherwise, you will only be able to use the
command line interface.

# The file naming script

This is the recommended file naming script to be used with Bard. Bard has many
needs as to how to organize your music and this script takes care of all of that.
Also, the script is very customizable and allows you to specify a lot of parameters
(by using specific tags in your song files) so you decide many aspects of the
final path used to save files.

## Installation of the file naming script

Open the `Options` dialog in Picard and go to the `File Naming` section.
Check the `Move files when saving` and the `Rename files when saving` options.
Enter a `Destination directory` that is *exclusive* for music correctly organized,
saved with Picard and containing MusicBrainz tags. Enter this directory in the
`musicbrainz_tagged_music_paths` config option in the Bard configuration
(`~/.config/bard`).

Open the file_naming_format.txt file with a text editor select all the contents
and Copy it to the clipboard. Then go back to Picard and in the `Name files like this`
section, paste the whole contents of the file.

## Usage of the file naming script by default

By default the songs are saved by default in this format below the `Destination directory` for regular releases:

Artist name/year - release name [FORMAT]/track number - track name

Where FORMAT contains the file format (MP3, FLAC, etc.). In the case of MP3 files, the bitrate is also specified
and in the case of FLAC files, 44100Hz, 16bits and stereo is considered normal so if the files have different
properties they're specified but if they're CD quality, then only FLAC is used.

If the release was released in a different year than the original, then the release year is added to the `album suffix`:

Artist name/original year - release name [release year,FORMAT]/track number - track name

If the release has more than one medium, then this format is used:

Artist name/original year - release name [release year,FORMAT]/CD1 - Medium subtitle/track number - track name
Artist name/original year - release name [release year,FORMAT]/CD2 - Medium subtitle/track number - track name

If the medium is a Vinyl, then LP1/LP2 is used instead.

If the release group has an special type (like Compilation, Live, Soundtrack, Single, EP ..) then the following format is used:
 
Artist name/compilation/original year - release name [release year,FORMAT]/track number - track name
Artist name/live/original year - release name [release year,FORMAT]/track number - track name
Artist name/soundtracks/original year - release name [release year,FORMAT]/track number - track name
Artist name/singles/original year - release name [release year,FORMAT]/track number - track name
Artist name/ep/original year - release name [release year,FORMAT]/track number - track name

Or if it has more than one type, then they're added one after another (`.../compilation/soundtracks/...` , `.../singles/promotion/...`, etc.)

In the case of a release having a `Various artists` album artist, then it's handled as a special case and another level
is used with the albumgenre tag or if it doesn't exist, the first genre of the songs (it's very important that for these releases,
all tracks have the same first genre! otherwise, the tracks will be saved on different folders):

Various Artists/Rock/original year - release name [release year,FORMAT]/track number - track name
Various Artists/Rock/original year - another release name [release year,FORMAT]/track number - track name
Various Artists/Jazz/original year - yet another release name [release year,FORMAT]/track number - track name

## Customizing the destination of a release

There are some tags that can be set in all songs of a release to customize the name of the folder where the release is saved to. These tags appear in
a comment at the beginning of the file naming script as a quick reference:

* albumgenre: Force this value to be used as genre for Various Artists' genre path (instead of the individual songs' genres)
* comment_bitrate: When using useformat==2, force this value instead of the bitrate read from the files. By default, an album of MP3 files will have a format suffix of `MP3,320kbps` for example, but in some cases, different songs may have different bitrates, so they would be saved in different folders (for example, some in a folder with `MP3,256kbps` and others in `MP3,320kbps`). By setting comment_bitrate to `256,320` in all songs of a release, all will be saved to `MP3,256,320kbps`. Also, when VBR is detected, `MP3,VBR` is used. In that case, setting comment_bitrate to `VBR:150-200` will make `MP3,VBR:150-200kbps` to be used.
* usebarcode: 0|1 : If set to 1, adds the release barcode to the album suffix.
* userecordingcomment: 0|1|2 : With 1, adds the recording dissambiguation text to the filename suffix. With 2, adds the comment tag to the filename suffix.
* useformat: 0|1|2 : With 1, adds format to the album suffix (this is the default). With 2, also adds bitrate, sample rate, channels, etc.
* uselabel: 0|1|2 : Adds the label names to the album suffix. With 2, also adds catalog number. Also, setting uselabel to 2 is considered as specifying that this album is exactly the same one referenced by MusicBrainz, so we assume usemedia is 1 then (unless it's a CD or it's explicitly set to 0).
* usemedia: 0|1 : Adds media information, CD|LP|etc., to the album suffix
* _bard_albumartist_folder: text : Set by the bard plugin. If set, it's used as albumartist.
* usenormalizedalbumartist: 0|1 : Use _aaeStdAlbumArtists instead of albumartist . Note the preference order is: forcealbumartist (if set), _aaeStdAlbumArtists (if usenormalizedalbumartist is set), _bard_albumartist_folder, albumartist, artist.
* usereleasecomment: 0|1|2|3 : With 1, adds the release dissambiguation text to the album suffix. With 2, adds the comment tag to the album suffix. With 3, use the release group comment.
* usereleasecountry: 0|1 : Adds the release country to the album suffix
* usereleasegroup: 0|1 : Adds the release group as as intermediary directory to group releases inside inner folders. In this case, the path used will be of the type of

Artist name/original year - release group name/release year - release name [FORMAT]/Otrack number - track name
Artist name/original year - release group name/release year - release name [FORMAT]/track number - track name

It's highly recommended that if you set usereleasegroup for a release, then you also set it to all releases in the same release group.

* usetotaltracks: 0|1 : Adds the number of tracks -- counting all discs -- to the album suffix.
* usetotaldisctracks: 0|1 : Adds the number of tracks in the current disc to the album suffix -- only use it in releases with one disc.
* usepersonalalbum: 0|1 : The album is a personal collection of non-album tracks that must be placed at _albumartist_/others/_year_ - _forcealbum_/ . Check the note on personal albums below.
* musicbrainzverified: 0|1 : If 1, it means the musicbrainz matching was verified manually.

* forcemedia: text : Force usemedia to use this text as media value
* forcealbum: text : Force this as album name (in case you prefer to use a name different from the official one). Also personal mixes and personal albums use this as album value instead of the album tag
* forcealbumartist: text: Force to use this value for the albumartist directory name
* forceartistinfilename: 0|1 : Force writing the artist to the filename as if multiartist was set
* forcecomplete: 0|1 : Force the album to be considered complete even if not all tracks have files, so no \"incomplete\" text is added to the directory.
* forceformat: text : Force format text
* usepersonalmix: 0|1 : The album is a personal mix that must be placed at Various Artists/Mixes . Check the note on personal mixes below.

## Personal albums

A personal album is an album that doesn't exist in MusicBrainz. It's used if you want to store some songs from an artist together as an album. I use this to create "albums" with the contents of books with sheet music by an artist.

For personal albums, the forcealbum tag MUST be set (it's used as the album name) and all songs MUST have the same date. Also, it's important to check that the discnumber/discsubtitle tags have sensible values (most probably, not set for any song but you can set it manually to create a personal album with several mediums).

## Personal mixes

A personal mix is equivalent of a mixtape with recordings that you want to store together as an album (and being personal, it doesn't exist as a MusicBrainz release). To create a personal mix, first save your songs either on regular releases or as non-album tracks. Then copy all songs you want to put in the mix to a folder and edit the tags of all songs in Picard:
* Set the usepersonalmix tag to 1.
* Set the album, albumsort and forcealbum tags to the name of the personal mix
* Set the albumartist tag to `Various Artists`
* Set the totaldiscs, discnumber, discsubtitle to reasonable values for your mix (usually 1, 1, and empty/removed respectively)
* Set the totaltracks and tracknumber tags to reasonable values for your mix.
* Remove the MusicBrainz Release Artist Id, Release Group Id and Release Id tags as those are not relevant to a personal mix.


# The Bard Picard plugin

The bard picard plugin does mainly two things. It adds some internal tags
to files that can be used by the bard file naming script to give better names
to your songs and organize your music collection better.

The tags added by the bard plugin are:
* _bard_albumartist_folder: This is the name bard recommends to use for the artist folder.
This tries to generate different directory names for different artists even if they have
the same name. This works by generating an `.artist_mbid` file in artist folders that
identifies the folder with MusicBrainz's artist UUID. So if you have a folder used for
an artist songs and then try to save music from a different artist who has the same name,
the plugin will notice that a folder for that name already exists and is used for a different
artist and will propose a folder name that contains the artist disambiguation text.
Also, the tag gives preference to names in latin scripts, so folders are easily read/written.

* _bard_album_mediaformat: This contains the media format of the release
(things like: `12" Vinyl`, `2xCD` or `3xCD+Bluray`). This is used by the
file naming script to write information about the release when it's verified.

As previously mentioned, the plugin creates hidden files so bard can see where music is.
The files created are:

* `.artist_mbid`: It's always created to identify a folder with an artist UUID. Also,
bard uses this so if a folder contains an `artist.jpg` image file and an `.artist_mbid` file,
 the image is used for that artist.

* `.releasegroup_mbid`: By default the file naming script doesn't generate a release group
folder level (all regular releases are saved inside the artist folder, `compilation` releases
inside a `compilation` folder in the artist directory, etc.). But when the `usereleasegroupinpath`
tag is set on a release, a releasegroup path level is added and the bard plugin creates
a `.releasegroup_mbid` file in it to identify it with the corresponding Musicbrainz's UUID.

## Installation (method 1)

Open the `Options` dialog in Picard. Go to the `Plugins` section and click on the `Install plugin...` button.
Browse to this directory and select the bard.py file to install it.

## Installation (method 2)
Copy or move the bard.py file from this directory to your  Picard plugins directory (usually `~/.config/MusicBrainz/Picard/plugins/`).


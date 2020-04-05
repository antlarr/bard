var current_song_id = 0;
var current_playlist_song_info = null;


function openComponent(page, data=null, push_to_history=true, callback=null)
{
    if (push_to_history)
        window.history.pushState({page: 'openComponent', component: page, data:data}, "", "/");
    $.ajax({
        url: "/component/" + page,
        data: data,
        success: function( result ) {
            $( "#container" ).html( result );
            if (callback) callback();
        },
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
    // $( "#container" ).html("<p>Login!</p>");
}

/**
 * Formatting songs and playlists
 */
function finalizeFormatArtist(jq, artist_credit)
{
    ac = $('<span/>');
    artist_credit.forEach((credit,i) => {
        $('<a/>', {
            on: {
               click: function() { openArtist(credit['artist_id']); }
            },
            text: credit['name'],
            appendTo: ac
        });

        ac.append(credit.join_phrase);
    });
    jq.empty();
    jq.append(ac);
}

function formatArtist(jq, song, playlistInfo)
{
    jq.html(song['artist_name']);
    $.ajax({
        url: "/api/v1/artist_credit/info",
        data: {id: song['artist_credit_id']},
        success: function( data, textStatus, jqXHR) {
            finalizeFormatArtist(jq, data);
        },
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}


function formatSongName(jq, song, playlistSongInfo)
{
   console.log(song);
   jq.html('<a>' + song['name'] + '</a>');
   jq.on('click', { songID: song['song_id'],
                    playlistSongInfo: playlistSongInfo},
          function(ev) {
              bard.playSongFromPlaylist(ev.data.songID, ev.data.playlistSongInfo);
          });

}

function formatRelease(jq, song, playlistSongInfo)
{
   console.log(song);
   jq.html('<a>' + song['release_name'] + '</a>');
   jq.on('click', { songID: song['song_id'],
                    albumID: song['album_id'],
                    playlistSongInfo: playlistSongInfo},
          function(ev) {
                openAlbum(ev.data.albumID);
          });

}

function formatDurationValue(duration)
{
   var hours = Math.floor(duration / 3600);
   duration = duration % 3600;
   var minutes = Math.floor(duration / 60);
   if (hours > 0 && minutes < 10) {
     minutes = '0' + minutes
   }
   duration = Math.floor(duration % 60);
   if (duration < 10) {
     duration = '0' + duration
   }
   var formatted = minutes + ':' + duration;
   if (hours > 0)
   {
     formatted = hours + ':' + formatted;
   }
   return formatted;
}


function formatDuration(jq, song, playlistInfo)
{
   jq.html(formatDurationValue(song['duration']));
}

const columns_base = [['#', ['position', 'track_position']],
           ['Name', formatSongName],
           ['Artist', formatArtist],
           ['Length', formatDuration ]];

function append_rows_to_table_of_songs(songs, table, uniquesuffix='0', playlistInfo=null, release_column=false, add_header_row=true)
{
    var i, j, col;

    var columns = [...columns_base];
    if (release_column) {
        columns.splice(2, 0, ['Release', formatRelease])
    }

    if (add_header_row) {
        var r = "";
        columns.forEach((col,i) => {
            r+= '<th>' + col[0] + '</th>';
        });
        var trh = $("<tr/>").append(r);
        table.append(trh);
    }

    songs.forEach((song,i) => {
        var songid = 'song-'+i+'-'+uniquesuffix;
        var tmpPlaylistInfo = $.extend({index: i, track_position: song['track_position']},playlistInfo);
        console.log(song);
        var tr = $("<tr/>");
        if (song['song_id'] == null)
        {
            tr.addClass('unavailableSong');
        };
        columns.forEach((col,j) => {
            //console.log(col);
            var td = $("<td/>", { appendTo: tr})
            if (typeof(col[1]) =="function")
            {
                col[1](td, song, tmpPlaylistInfo);
            }
            else if (typeof(col[1]) == "object")
            {
               columns_to_check = col[1];
               for (var k=0 ; k < columns_to_check.length; k++)
               {
                   if (song.hasOwnProperty(columns_to_check[k]))
                   {
                       td.html(song[columns_to_check[k]]);
                       break;
                   };
               };
            }
            else
            {
                td.html(song[col[1]]);
            }
        });

        console.log('out of songs loop');
        table.append(tr);

        setDraggable(tr, {'application/x-bard': JSON.stringify({'songID': song['song_id']})});
    });

    return table;
}

function add_table_of_songs(songs, appendToObj, uniquesuffix='0', playlistInfo=null, release_column=false, add_header_row=true)
{
    table = $("<table/>", { appendTo: appendToObj });
    return append_rows_to_table_of_songs(songs, table, uniquesuffix, playlistInfo, release_column, add_header_row);
}

/**
 * Formatting songs and playlists (end)
 */

function openAbout(push_to_history=true)
{
    if (push_to_history)
        window.history.pushState({page: 'openAbout'}, "", "/");
    $( "#container" ).html("<p>About Bard</p>");
}

function dateTupleToString(tuple)
{
    var r = tuple[0] || null;
    if (r && tuple[1])
    {
        r += "-" + tuple[1];
        if (tuple[2])
            r += "-" + tuple[2];
    };
    return r;
}

function dateTuplesRangeToString(begin, end)
{
    begin_date = dateTupleToString(begin);
    end_date = dateTupleToString(end);
    if (begin_date && end_date)
        return begin_date + " – " + end_date;
    if (begin_date)
        return begin_date + " –";
    if (end_date)
        return "– " + end_date;
    return null;
}

function setCurrentSongInfo(id, metadata)
{
    if (id == current_song_id)
    {
        $( "#current-song-title" ).html(metadata.title);
        $( "#current-song-artist" ).html(metadata.artist);
    }
}

function openAlbum( id )
{
    openComponent('album', {id: id});
}

function openArtist( id )
{
    openComponent('artist', {id: id});
}


function submitLogin()
{
    username=$("#username").val();
    password=$("#password").val();

    $.ajax({
      url: "/login",
      method: "post",
      data: {
        username: username,
        password: password
      },
      success: function( result ) {
          openComponent('search');
      },
      error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
      }
    });
}


window.onpopstate = function( event ) {
    switch (event.state['page'])
    {
       case 'openComponent':
            openComponent(event.state['component'], event.state['data'], false, null);
            break;
       case 'openAbout':
            openAbout(false);
            break;
       case 'performSearch':
            openComponent('home', null, push_to_history=false, callback= function() {
               $("#searchBar").val(event.state['query']);
               performSearch(false);
             });
            break;
    }
}


function Bard()
{
    $( "#nav-home" ).on( "click", function( event ) {
        openComponent('home');
        event.preventDefault();
    });

    $( "#nav-artists" ).on( "click", function( event ) {
        openComponent('artists');
        event.preventDefault();
    });

    $( "#nav-albums" ).on( "click", function( event ) {
        openComponent('albums');
        event.preventDefault();
    });

    $( "#nav-genres" ).on( "click", function( event ) {
        openComponent('genres');
        event.preventDefault();
    });

    fillPlaylists();
    //document.requestFullScreen();
    this.base = window.location.protocol + '//' + window.location.host;

    $.when(
        $.getScript("/static/js/player-controls.js"),
        $.getScript("/static/js/webplayer.js").fail(function(jqxhr, settings, exception) { alert('error' + exception); }),
        $.Deferred(function( deferred ){
            $( deferred.resolve );
        })
    ).done(function(){
        this.player = new WebPlayer();
        this.controls = new PlayerControls();
        this.controls.player = this.player;
        this.player.ui = this.controls;
        console.log('loaded ' + this.player + this.controls );
    }.bind(this));

    this.playSongFromPlaylist = function(songID, playlistSongInfo)
    {
        console.log(playlistSongInfo);
        /*if (playlistSongInfo.hasOwnProperty('albumID')) {
            alert('1play song ' + songID +
                  ' from playlist ' + playlistSongInfo['albumID'] +
                  '/' + playlistSongInfo['mediumNumber'] +
                  ' index ' + playlistSongInfo['track_position']);
        } else {
            alert('2play song ' + songID +
                  ' from playlist ' + playlistSongInfo['playlistID'] +
                  ' index ' + playlistSongInfo['index']);
        }*/
        current_playlist_song_info = playlistSongInfo;
        this.playSong(songID);
    }

    this.playSong = function(id)
    {
        current_song_id = id;
        $( "#current-song-cover" ).attr("src", this.base + "/api/v1/coverart/song/" + id)
        var metadata = get_song_metadata( id, setCurrentSongInfo );
        if (metadata)
        {
            setCurrentSongInfo(id, metadata);
        }
        $( "#player" ).attr("src", this.base + "/api/v1/audio/song/" + id)
        bard.controls.setEnable(true);
    }

    this.requestPrevSong = function()
    {
    };

    this.requestNextSong = function()
    {
        console.log('next_song');
        $.ajax({
          type: "POST",
          url: "/api/v1/playlist/current/next_song",
          data: current_playlist_song_info,
          success: function( result ) {
              console.log(result);
              console.log(result.songID);
              bard.playSongFromPlaylist(result.songID, result.playlistSongInfo);
          }
        });
    }
};


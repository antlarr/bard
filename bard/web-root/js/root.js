var current_song_id = 0;

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

function formatArtist(jq, song)
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

function formatSongName(jq, song)
{
   jq.html('<a>' + song['name'] + '</a>');
   jq.on('click', { songID: song['song_id'] }, function(ev) { playSong(ev.data.songID); });
}

function formatDuration(jq, song)
{
   var duration = song['duration']
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
   formatted = minutes + ':' + duration;
   if (hours > 0)
   {
     formatted = hours + ':' + formatted;
   }
   jq.html(formatted);
}

columns = [['#', ['position', 'track_position']],
           ['Name', formatSongName],
           ['Artist', formatArtist],
           ['Length', formatDuration ]];

function add_table_of_songs(songs, appendToObj, uniquesuffix='0')
{
    table = $("<table/>", { appendTo: appendToObj });
    var i, j, col;

    var r = "";
    columns.forEach((col,i) => {
        r+= '<th>' + col[0] + '</th>';
    });
    var trh = $("<tr/>").append(r);
    table.append(trh);

    songs.forEach((song,i) => {
        var songid = 'song-'+i+'-'+uniquesuffix;
        console.log(song);
        var tr = $("<tr/>");
        columns.forEach((col,j) => {
            console.log(col);
            var td = $("<td/>", { appendTo: tr})
            if (typeof(col[1]) =="function")
            {
                col[1](td, song);
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

function performSearch(push_to_history=true)
{
    searchText=$("#searchBar").val();
    if (push_to_history)
        window.history.pushState({page: 'performSearch', query: searchText}, "", "/");
    $.ajax({
      url: "/api/v1/search",
      data: {
        query: searchText
      },
      success: function( result ) {
        r="";
        for (i=0 ; i< result.length; i++)
        {
            r+="<br><a onclick=\"playSong(" + result[i].id + ")\">" + result[i].path + "</a>";
        };
        $( "#searchResult" ).html( r );
        set_song_metadata_cache( result );
      }
    });
}

function setCurrentSongInfo(id, metadata)
{
    if (id == current_song_id)
    {
        $( "#current-song-title" ).html(metadata.title);
        $( "#current-song-artist" ).html(metadata.artist);
    }
}

function openArtist( id )
{
    openComponent('artist', {id: id});
}

function playSong(id)
{
    current_song_id = id;
    base=window.location.protocol + '//' + window.location.host;
    $( "#current-song-cover" ).attr("src", base + "/api/v1/coverart/song/" + id)
    var metadata = get_song_metadata( id, setCurrentSongInfo );
    if (metadata)
    {
        setCurrentSongInfo(id, metadata);
    }
    $( "#player" ).attr("src", base + "/api/v1/audio/song/" + id)
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


function initBardConstructor()
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
};

var bard = new Object();

bard.initBard = initBardConstructor

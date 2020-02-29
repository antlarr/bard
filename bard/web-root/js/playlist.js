function playlistInfoReceived( result )
{
   $( "#playlistInfo" ).html( "<p>" + result.name + "</p>" );
}


function playlistTracksReceived( result )
{
//    var x = table_from_songs(result, 'playlist');
//    var r = x[0];
//    var songs = x[1];

/*    var r = "<div><ul>"
    var tracks = result;
    var i=0;

    for (j=0; j < tracks.length; j++)
    {
        var songid = 'song-'+i+'-'+j;
        r +="<li><a id=\""+ songid + "\" onclick=\"playSong(" + tracks[j].song_id + ")\">" + tracks[j].name + "</a> (" + tracks[j].artist_name +") </li>";
    }
    r += "</ul></div>"
*/

    jq_table = add_table_of_songs(result, $( "#playlistTracks" ));
    jq_table.addClass('playlist');

//    songs.forEach((x,i) => {
//        setDraggable($( "#" + x[0] ), x[1]);
//    });
}


function requestPlaylistInfo(id)
{
    $.ajax({
        url: "/api/v1/playlist/info",
        data: {id: id},
        success: playlistInfoReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function requestPlaylistTracks(id)
{
    $.ajax({
        url: "/api/v1/playlist/tracks",
        data: {id: id},
        success: playlistTracksReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function fillPlaylistPage(id)
{
    requestPlaylistInfo(id);
    requestPlaylistTracks(id);
}

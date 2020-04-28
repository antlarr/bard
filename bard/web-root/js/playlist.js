function playlistInfoReceived( result )
{
   $( "#playlistInfo" ).html( "<p>" + result.name + "</p>" );
}


function playlistTracksReceived( result, playlist_id )
{
    console.log(result);
    var playlistInfo = {
        playlist_type: 'user',
        playlist_id: playlist_id
    };
    jq_table = add_table_of_songs(result, $( "#playlistTracks" ), 0, playlistInfo );
    jq_table.addClass('playlist');
}


function requestPlaylistInfo(playlist_id)
{
    $.ajax({
        url: "/api/v1/playlist/info",
        data: {id: playlist_id},
        success: playlistInfoReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function requestPlaylistTracks(playlist_id)
{
    $.ajax({
        url: "/api/v1/playlist/tracks",
        data: {id: playlist_id},
        success: function(result) { playlistTracksReceived(result, playlist_id); },
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function fillPlaylistPage(playlist_id)
{
    requestPlaylistInfo(playlist_id);
    requestPlaylistTracks(playlist_id);
}

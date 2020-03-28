function playlistInfoReceived( result )
{
   $( "#playlistInfo" ).html( "<p>" + result.name + "</p>" );
}


function playlistTracksReceived( result, playlistID )
{
    console.log(result);
    var playlistInfo = {
        playlistID: playlistID
    };
    jq_table = add_table_of_songs(result, $( "#playlistTracks" ), 0, playlistInfo );
    jq_table.addClass('playlist');
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
        success: function(result) { playlistTracksReceived(result, id); },
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

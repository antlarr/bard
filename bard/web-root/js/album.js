function albumInfoReceived( result )
{
    var r="";
    $( "#artistInfo" ).html( "<p>" + result.name + "</p>" );
    for (i=0 ; i<result.aliases.length; i++)
    {
        r+="<li>" + result.aliases[i].name + " (" + result.aliases[i].locale + ")</li>";
    }
    $( "#artistAliases" ).html( "<ul>" + r + "</ul>" );
}

function mediumSignature(medium)
{
    var suffix = "";
    if (medium.name)
        suffix = " : " + medium.name;
    return medium.format + " " + medium.number + suffix;
}

function add_medium(medium, appendToObj, playlistInfo)
{
    var medium_div = $("<div/>", { class: "medium", appendTo: appendToObj });
    $("<span/>", { class: "mediumSignature",
                   text: mediumSignature(medium),
                   appendTo: medium_div
    });

    add_table_of_songs(medium.tracks, medium_div, medium.number, playlistInfo);
    return medium_div;
}
function albumTracksReceived( result, album_id )
{
    for (i=0 ; i < result.length; i++)
    {
        var playlistInfo = {
            playlist_type: 'album',
            album_id: album_id,
            medium_number: result[i].number
        };
        add_medium(result[i], $("#albumTracks"), playlistInfo);
    };
}

function requestAlbumInfo(id)
{
    $.ajax({
        url: "/api/v1/album/info",
        data: {id: id},
        success: albumInfoReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function requestAlbumTracks(id)
{
    $.ajax({
        url: "/api/v1/album/tracks",
        data: {id: id},
        success: function(result) { albumTracksReceived(result, id); },
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function fillAlbumPage(id)
{
    requestAlbumTracks(id);
}

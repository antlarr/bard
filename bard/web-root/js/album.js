function albumInfoReceived( result )
{
    var r="";

    /*for (i=0 ; i< result.length; i++)
    {
        r+="<li><a onclick=\"openArtist('" + result[i].mbid + "')\"><img src=\"artist.jpg\"><p class=\"name\">" + result[i].locale_name + "</p></a></li>";
    };
    $( "#artistsList" ).append( r );
    artistsOffset += result.length;
    */
    $( "#artistInfo" ).html( "<p>" + result.name + "</p>" );
    r = ""
    for (i=0 ; i<result.aliases.length; i++)
    {
        r+="<li>" + result.aliases[i].name + " (" + result.aliases[i].locale + ")</li>";
    }
    $( "#artistAliases" ).html( "<ul>" + r + "</ul>" );
}

function mediumSignature(medium)
{
    suffix = "";
    if (medium.name)
        suffix = " : " + medium.name;
    return "Medium " + medium.number + suffix;
}

function albumTracksReceived( result )
{
    var r="";

    for (i=0 ; i < result.length; i++)
    {
        medium = "<div class=\"medium\">" + mediumSignature(result[i]);
        tracks = result[i].tracks;
        medium += "<ul>"
        for (j=0; j < tracks.length; j++)
        {
            medium +="<li><a onclick=\"playSong(" + tracks[j].song_id + ")\">" + tracks[j].name + "</a> (" + tracks[j].artist_name +") </li>";
        }
        medium += "</ul></div>"
        r+=medium;
    };
    $( "#albumTracks" ).html( "<ul>"+r+"</ul>" );
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
        success: albumTracksReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function fillAlbumPage(id)
{
    //requestReleaseGroupInfo(id);
    requestAlbumTracks(id);
    /*$('#artistsContent').on('scroll', function() {
        if($(this).scrollTop() + $(this).innerHeight() >= $(this)[0].scrollHeight) {
            requestArtists(artistsOffset, page_size);
        }
    });*/
}

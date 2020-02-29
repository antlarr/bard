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
    var suffix = "";
    if (medium.name)
        suffix = " : " + medium.name;
    return medium.format + " " + medium.number + suffix;
}

function add_medium(medium, appendToObj)
{
    var medium_div = $("<div/>", { class: "medium", appendTo: appendToObj });
    $("<span/>", { class: "mediumSignature",
                   text: mediumSignature(medium),
                   appendTo: medium_div
    });
   
    add_table_of_songs(medium.tracks, medium_div, medium.number);
    return medium_div;
}
function albumTracksReceived( result )
{
    for (i=0 ; i < result.length; i++)
    {
        add_medium(result[i], $("#albumTracks"));
    };
}

function albumTracksReceived_old( result )
{
    //jq_table = add_table_of_songs(result, $( "#albumTracks" ));
    //jq_table.addClass('album');
    //return
    var r="";

    var songs = []
    for (i=0 ; i < result.length; i++)
    {
        var medium = "<div class=\"medium\">" + mediumSignature(result[i]);
        var tracks = result[i].tracks;
        medium += "<ul>"
        for (j=0; j < tracks.length; j++)
        {
            var songid = 'song-'+i+'-'+j;
            medium +="<li><a id=\""+ songid + "\" onclick=\"playSong(" + tracks[j].song_id + ")\">" + tracks[j].name + "</a> (" + tracks[j].artist_name +") </li>";
            songs.push([songid,{'application/x-bard': JSON.stringify({'songID': tracks[j].song_id})}]);
        }
        medium += "</ul></div>"
        r+=medium;
    };
    $( "#albumTracks" ).html( "<ul>"+r+"</ul>" );

    songs.forEach((x,i) => {
        setDraggable($( "#" + x[0] ), x[1]);
    });
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


function releaseGroupInfoReceived( result )
{
    bard.setTitle(result.name, 'Release Group');

    $( "#releaseGroupInfo" ).html( "<p>" + result.name + "</p>" );
    $( "#releaseGroupArtists" ).html( "<p>" + result.artist_name + "</p>" );
}

function releasesReceived( result )
{
    var r="";

    for (i=0 ; i< result.length; i++)
    {
        audio_prop = "";
        for (j=0; j<result[i].audio_properties.length; j++)
            audio_prop += result[i].audio_properties[j].string;
        r+="<li><a onclick=\"openAlbum('" + result[i].album_id + "')\"><img src=\"/api/v1/release/image?mbid=" + result[i].mbid + "\"><p class=\"name\">" + result[i].name + "</p><p class=\"disambiguation\">" + result[i].album_disambiguation + "</p></a><p class=\"audio_properties\">" + audio_prop + "</p></li>";
    };
    $( "#releasesList" ).html( "<ul>"+r+"</ul>" );
}


function requestReleaseGroupInfo(id)
{
    $.ajax({
        url: "/api/v1/release_group/info",
        data: {id: id},
        success: releaseGroupInfoReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function requestReleasesInReleaseGroup(id)
{
    $.ajax({
        url: "/api/v1/release_group/releases",
        data: {id: id},
        success: releasesReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function fillReleaseGroupPage(id)
{
    requestReleaseGroupInfo(id);
    requestReleasesInReleaseGroup(id);
    /*$('#artistsContent').on('scroll', function() {
        if($(this).scrollTop() + $(this).innerHeight() >= $(this)[0].scrollHeight) {
            requestArtists(artistsOffset, page_size);
        }
    });*/
}

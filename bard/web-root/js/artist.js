function openReleaseGroup( id )
{
    openComponent('release-group', {id: id});
}

function artistMemberRelationsReceived( result )
{
    var r="";
    for (i=0 ; i< result.members.length; i++)
    {
        artist = result.members[i][0];
        date_range = dateTuplesRangeToString(result.members[i][1], result.members[i][2]);
        date_range_str = date_range ? ("<span class=\"date_range\">(" + date_range + ")</span>") : "";
        attrs = result.members[i][3];
        attrs_str = attrs ? ("<span class=\"attributes\">(" + attrs + ")</span>") : "";
        r+="<li><a onclick=\"openArtist('" + artist.id + "')\"><span class=\"artist_name\">^ " + artist.name + "</span></a> " + attrs_str + " " + date_range_str + "</li>";
    };

    for (i=0 ; i< result.memberOf.length; i++)
    {
        artist = result.memberOf[i][0];
        date_range = dateTuplesRangeToString(result.memberOf[i][1], result.memberOf[i][2]);
        date_range_str = date_range ? ("<span class=\"date_range\">(" + date_range + ")</span>") : "";
        attrs = result.memberOf[i][3];
        attrs_str = attrs ? ("<span class=\"attributes\">(" + attrs + ")</span>") : "";
        r+="<li><a onclick=\"openArtist('" + artist.id + "')\"><span class=\"artist_name\">: " + artist.name + "</span></a> " + attrs_str + " " + date_range_str + "</li>";
    };
    $( "#artistMemberRelations" ).html( "<ul>"+r+"</ul>" );
}

function artistInfoReceived( result )
{
    var r="";

    bard.setTitle(result.name, 'Artist');
    $( "#artistInfo" ).html( "<p>" + result.name + "</p>" );
    r = ""
    for (i=0 ; i<result.aliases.length; i++)
    {
        r+="<li>" + result.aliases[i].name + " (" + result.aliases[i].locale + ")</li>";
    }
    $( "#artistAliases" ).html( "<ul>" + r + "</ul>" );
}

function releaseGroupsReceived( result )
{
    var r="";

    for (i=0 ; i< result.length; i++)
    {
        r+="<li><a onclick=\"openReleaseGroup('" + result[i].id + "')\"><img src=\"/api/v1/release_group/image?mbid=" + result[i].mbid + "\"><p class=\"name\">" + result[i].name + "</p></a></li>";
    };
    $( "#artistReleaseGroupsList" ).html( "<ul>"+r+"</ul>" );
}


function requestArtistInfo(id)
{
    $.ajax({
        url: "/api/v1/artist/info",
        data: {id: id},
        success: artistInfoReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function requestArtistReleaseGroups(id)
{
    $.ajax({
        url: "/api/v1/artist/release_groups",
        data: {id: id},
        success: releaseGroupsReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function requestArtistMemberRelations(id)
{
    $.ajax({
        url: "/api/v1/artist/member_relations",
        data: {id: id},
        success: artistMemberRelationsReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}


function fillArtistPage(id)
{
    requestArtistInfo(id);
    requestArtistReleaseGroups(id);
    requestArtistMemberRelations(id);
    /*$('#artistsContent').on('scroll', function() {
        if($(this).scrollTop() + $(this).innerHeight() >= $(this)[0].scrollHeight) {
            requestArtists(artistsOffset, page_size);
        }
    });*/
}

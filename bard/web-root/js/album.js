use_medium_covers = $.Deferred();
generated_mediums = $.Deferred();

function albumInfoReceived( result )
{
    bard.setTitle(result.name, 'Album');

    console.log(result);
    if (result.disambiguation)
        var disambiguation = '  <span class="album-disambiguation">('+ result.disambiguation + ')</span>';
    else
        var disambiguation = '';
    $( "#album-title" ).html( "<p>" + result.name + disambiguation + "</p>" );
    formatAlbumRatings( $( "#album-title" ), result);
    formatArtist($( "#album-artist" ), result.artist_credit_id, result.artist_credit_name);
    var s = [result.status, result.release_group.release_group_type].concat(result.release_group_secondary_types);
    s = s.filter(function (x) { return x; });

    $( "#album-status" ).html( "<p>" + s.join(', ') + "</p>" );
    formatAlbumReleaseEvents($( "#album-release-events" ), result.release_events);
    use_medium_covers.resolve(result.covers_count > 1);
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
    var medium_header = $("<div/>", { class: "medium-header", appendTo: medium_div });
    $("<span/>", { class: "medium-signature",
                   text: mediumSignature(medium),
                   appendTo: medium_header
    });
    var medium_cover_container = $("<div/>", { class: "medium-cover-container", appendTo: medium_header });

    add_table_of_songs(medium.tracks, medium_div, medium.number, playlistInfo);
    return {medium_number: medium.number, jq: medium_div};
}
function albumTracksReceived( result, album_id)
{
    medium_list = [];
    for (i=0 ; i < result.length; i++)
    {
        var playlistInfo = {
            playlist_type: 'album',
            album_id: album_id,
            medium_number: result[i].number
        };
        var m = add_medium(result[i], $("#albumTracks"), playlistInfo);
        medium_list.push(m);
    };
    generated_mediums.resolve(medium_list);
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
    requestAlbumInfo(id);
    requestAlbumTracks(id);


    $("#album-cover").attr("src", bard.base + "/api/v1/album/image?id=" + id);

    $.when (use_medium_covers, generated_mediums).done(
        function (use_medium_covers, generated_mediums)
        {
            if (!use_medium_covers)
                return;
            var imgurl = bard.base + '/api/v1/album/image?id=' + id + '&medium_number='
            generated_mediums.forEach((m,i) => {
                var medium_number = m.medium_number;
                var jq = m.jq.find('.medium-cover-container');
                var medium_cover = $("<img/>", {
                    class: "medium-cover",
                    src: imgurl + medium_number,
                    appendTo: jq });
            });
        }
    );
}

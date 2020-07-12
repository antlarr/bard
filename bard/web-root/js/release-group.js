
function formatAlbumName(jq, album)
{
   jq.addClass('no-padding');
   var imgurl = bard.base + '/api/v1/album/image?id=' + album.album_id;
   if (album.album_disambiguation) {
      var disambiguation = ' <span class="disambiguation">(' + album.album_disambiguation + ')</span>';
   } else {
      var disambiguation = '';
   }
   var albumName = '<div class="horizontal"><img src="' + imgurl + '" class="cover-in-list"><div class="vertical"><span class="releasename"><a>' + album.name + '</a>' + disambiguation + '</span><span class="releaseartist"></span></div>';
   jq.html(albumName);
   if (album.artist_credit_id != album.release_group.artist_credit_id) {
       formatArtist(jq.find('.releaseartist'), album.artist_credit_id, album.artist_credit_name);
   }

   jq.on('click', { album_id: album.album_id },
          function(ev) {
                openAlbum(ev.data.album_id);
          });
}
function formatMediaFormat(jq, album)
{
   jq.html('<span class="media-format">' + album.mediums_desc + '</span>');
}
function formatNumberOfTracks(jq, album)
{
   jq.html(album.tracks_count.join('+'));
}
function formatAlbumFormat(jq, album)
{
   var r = '';
   var hires = false;
   album.audio_properties.forEach((prop) => {
      if (r) r+='<br>';
      r+= '<span class="audio_format">' + prop.format.toUpperCase() + '</span>';
      if (prop.max_bits_per_sample > 16 || prop.max_sample_rate > 48000)
          hires = true;

      if (prop.string)
      {
          r+= '<br><span class="audio_format_properties">' + prop.string + '</span>';
      }
   });

   r = '<div>' + r + '</div>';
   if (hires)
      r = '<img src="/static/images/hires-audio.jpg" class="audio-property-logo">' + r ;

   jq.html('<div class="audio-properties">' + r + '</div>');
}

function formatReleaseEvent(jq, album)
{
   formatAlbumReleaseEvents(jq, album.release_events, false);
}

var album_columns_base = [['Name', formatAlbumName],
           ['Format', formatMediaFormat ],
           ['Tracks', formatNumberOfTracks ],
           ['Format', formatAlbumFormat ],
           ['Released in', formatReleaseEvent ],
           ['Ratings', formatAlbumRatings]];

function append_row_to_table_of_albums(album, table)
{
    var columns = [...album_columns_base];
    var tr = $("<tr/>");
    columns.forEach((col,j) => {
        var td = $("<td/>", { appendTo: tr})
        if (typeof(col[1]) =="function")
        {
            col[1](td, album);
        }
        else if (typeof(col[1]) == "object")
        {
           columns_to_check = col[1];
           for (var k=0 ; k < columns_to_check.length; k++)
           {
               if (album.hasOwnProperty(columns_to_check[k]))
               {
                   td.html(album[columns_to_check[k]]);
                   break;
               };
           };
        }
        else
        {
            td.html(album[col[1]]);
        }
    });

    table.append(tr);
}

function add_table_of_albums(add_header_row=true)
{
    var table = $("<table/>");
    table.addClass('releaselist');
    var i, j, col;

    var columns = [...album_columns_base];

    if (add_header_row) {
        var r = "";
        columns.forEach((col,i) => {
            r+= '<th>' + col[0] + '</th>';
        });
        var trh = $("<tr/>").append(r);
        table.append(trh);
    }

    return table;
}

function releaseGroupInfoReceived( result )
{
    bard.setTitle(result.name, 'Release Group');

    $("#rg-cover").attr("src", bard.base + "/api/v1/release_group/image?mbid=" + result.mbid);
    $( "#rg-title" ).html( "<p>" + result.name + "</p>" );
    formatArtist($( "#rg-artist" ), result.artist_credit_id, result.artist_credit_name);
}

function releasesReceived( releases )
{
    var sections = {};
    var releases_main_section = $( "#releasesList" );
    var table = null;
    releases.forEach((album, i) => {
        var sectionName = album.status;
        if (!sections.hasOwnProperty(sectionName))
        {
            table = add_table_of_albums();
            sections[sectionName] = table;
            section_header = $("<p/>");
            section_header.addClass('rg-section');
            section_header.html(sectionName);
            releases_main_section.append(section_header);
            releases_main_section.append(table);
        }
        else
        {
            table = sections[sectionName];
        }
        append_row_to_table_of_albums(album, table);
    });
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
}

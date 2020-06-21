function openReleaseGroup( id )
{
    openComponent('release-group', {id: id});
}

function formatReleaseGroupName(jq, rg)
{
   jq.addClass('no-padding');
   var imgurl = bard.base + '/api/v1/release_group/image?mbid=' + rg.mbid;
   jq.html('<div class="horizontal"><img src="' + imgurl + '"><span class="releasename"><a>' + rg.name + '</a></span>');
   jq.on('click', { release_group_id: rg.id },
          function(ev) {
                openReleaseGroup(ev.data.release_group_id);
          });
}

function formatArtist_from_releaseGroup(jq, rg)
{
    formatArtist(jq, rg['artist_credit_id'], rg['artist_credit_name']);
}

function formatNumberOfReleases(jq, rg)
{
   jq.html(rg.album_count);
}

const rg_columns_base = [['Name', formatReleaseGroupName],
           ['Artist', formatArtist_from_releaseGroup],
           ['Ratings', formatReleaseGroupRatings],
           ['Year', 'year'],
           ['#', formatNumberOfReleases ]];

function append_row_to_table_of_release_groups(rg, table)
{
    var columns = [...rg_columns_base];
    var tr = $("<tr/>");
    columns.forEach((col,j) => {
        var td = $("<td/>", { appendTo: tr})
        if (typeof(col[1]) =="function")
        {
            col[1](td, rg);
        }
        else if (typeof(col[1]) == "object")
        {
           columns_to_check = col[1];
           for (var k=0 ; k < columns_to_check.length; k++)
           {
               if (song.hasOwnProperty(columns_to_check[k]))
               {
                   td.html(song[columns_to_check[k]]);
                   break;
               };
           };
        }
        else
        {
            td.html(rg[col[1]]);
        }
    });

    table.append(tr);
}

function add_table_of_release_groups(add_header_row=true)
{
    var table = $("<table/>");
    table.addClass('releaselist');
    var i, j, col;

    var columns = [...rg_columns_base];

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
    $( "#artistName" ).html( "<p>" + result.name + "</p>" );
    aliases = []
    for (i=0 ; i<result.aliases.length; i++)
    {
        aliases.push( result.aliases[i].name + " (" + result.aliases[i].locale + ")" );
    }
    $( "#artistAliases" ).html( aliases.join(", ") );
    if (result.has_image) {
        $("#artist-picture").attr("src", "/api/v1/artist/image?id=" + result.id);
    }
}

function releaseGroupsReceived( release_groups )
{
    var sections = {};
    rg_main_section = $("#artistReleaseGroupsList");
    var table = null;
    release_groups.forEach((rg, i) => {
        var sectionNames = [rg.release_group_type].concat(rg.secondary_types);
        var sectionName = sectionNames.join(' + ');
        if (!sections.hasOwnProperty(sectionName))
        {
            table = add_table_of_release_groups();
            sections[sectionName] = table;
            section_header = $("<p/>");
            section_header.addClass('rg-section');
            section_header.html(sectionName);
            rg_main_section.append(section_header);
            rg_main_section.append(table);
        }
        else
        {
            table = sections[sectionName];
        }
        append_row_to_table_of_release_groups(rg, table);
    });
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
}

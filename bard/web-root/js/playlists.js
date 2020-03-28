function openPlaylist( id )
{
    openComponent('playlist', {id: id});
}

function playlist_drop_filter(types)
{
   return types.includes('application/x-bard');
}

function playlist_drop_handler(el, droppedData, dropAreaData)
{
      var data = droppedData["application/x-bard"];
      var dropped = JSON.parse(droppedData['application/x-bard']);
      var songID = dropped['songID'];
      console.log(songID + 'dropped into playlist ' + dropAreaData['playlistID']);
      $.ajax({
        url: "/api/v1/playlist/add_song",
        data: {'playlistID': dropAreaData['playlistID'], 'songID': songID},
        success: function( result ) {
            el.removeClass('shine');
            void el.get(0).offsetWidth;
            el.addClass('shine');
        },
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
      });
}



function playlistsReceived( result )
{
    var r="";
    var playlists = [];
    for (var i=0 ; i< result.length; i++)
    {
        var plid = "playlist-" + i;
        playlists.push(plid);
        r="<li><a id=\"" + plid + "\" onclick=\"openPlaylist('" + result[i].id + "')\" class=\"playlist\">" + result[i].name + "</a></li>";
        $( "#playlistList" ).append( r );
        setDropArea($( "#" + plid ), playlist_drop_filter, playlist_drop_handler, {'playlistID': result[i].id});
    };
}

function requestPlaylists(offset, count)
{
    $.ajax({
        url: "/api/v1/playlist/list",
        success: playlistsReceived,
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
}

function fillPlaylists()
{
    requestPlaylists();
}


function addPlaylist()
{
   name = prompt('Enter the name of the playlist to create');

   if (name)
   {
     $.ajax({
        url: "/api/v1/playlist/new",
        data: {name: name},
        success: function( data, textStatus, jqXHR) {
            fillPlaylists();
        },
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
      });
   };
}

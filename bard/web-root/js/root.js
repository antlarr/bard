var current_song_id = 0;
var current_playlist_song_info = null;

function parse_query(query_string)
{
    var query = {};
    var pairs = (query_string[0] === '?' ? query_string.substr(1) : query_string).split('&');
    for (var i = 0; i < pairs.length; i++)
    {
        var pair = pairs[i].split('=');
        query[decodeURIComponent(pair[0])] = decodeURIComponent(pair[1] || '');
    }
    return query;
}

function path_for_component(page, data)
{
    if (data && data.hasOwnProperty('id'))
    {
        return '/' + page + '?id=' + data['id']
    }
    else if (page == 'search' && data)
    {
        return '/search?query=' + encodeURIComponent(data['query'])+ '&context=' + data['context'];
    }
    else if (page == 'artists' && data)
    {
        return '/artists?letter=' + data['letter'];
    }
    else
    {
        return '/' + page
    }
}

function openComponent(page, data=null, push_to_history=true, callback=null)
{
    if (page[0] == '/')
        page = page.slice(1);

    if (push_to_history)
    {
        var path = path_for_component(page, data);
        window.history.pushState({path: path}, "", path);
    }

    $.ajax({
        url: "/component/" + page,
        data: data
    }).done(
        function( result, textStatus, jqXHR ) {
            bard.setTitle(page[0].toUpperCase() + page.slice(1));
            $( "#container" ).html( result );
            if (callback) callback();
    }).fail(
        function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
    });
}

/**
 * Formatting songs and playlists
 */
function finalizeFormatArtist(jq, artist_credit)
{
    ac = $('<span/>');
    artist_credit.forEach((credit,i) => {
        $('<a/>', {
            on: {
               click: function() { openArtist(credit['artist_id']); }
            },
            text: credit['name'],
            appendTo: ac
        });

        ac.append(credit.join_phrase);
    });
    jq.empty();
    jq.append(ac);
}

function formatArtist(jq, artist_credit_id, artist_name)
{
    bard.metadataManager.get_artist_credit_info(artist_credit_id,
        function(data) {
            finalizeFormatArtist(jq, data);
        },
        function() {
            jq.html(artist_name);
        }
    );
}

function formatArtist_from_song(jq, song, playlist_song_info)
{
    formatArtist(jq, song['artist_credit_id'], song['artist_name']);
}


function formatSongName(jq, song, playlist_song_info)
{
   jq.html('<a>' + song['name'] + '</a>');
   jq.on('click', { song_id: song['song_id'],
                    playlist_song_info: playlist_song_info},
          function(ev) {
              bard.playSongFromPlaylist(ev.data.song_id, ev.data.playlist_song_info);
          });

}

function formatRelease(jq, song, playlist_song_info)
{
   jq.addClass('no-padding');
   var imgurl = bard.base + '/api/v1/album/image?id=' + song['album_id'] + '&medium_number='+ song['medium_number']
   jq.html('<div class="horizontal"><img src="' + imgurl + '"><span class="releasename"><a>' + song['release_name'] + '</a></span>');
   jq.on('click', { song_id: song['song_id'],
                    album_id: song['album_id'],
                    playlist_song_info: playlist_song_info},
          function(ev) {
                openAlbum(ev.data.album_id);
          });

}

function formatDurationValue(duration)
{
   var hours = Math.floor(duration / 3600);
   duration = duration % 3600;
   var minutes = Math.floor(duration / 60);
   if (hours > 0 && minutes < 10) {
     minutes = '0' + minutes
   }
   duration = Math.floor(duration % 60);
   if (duration < 10) {
     duration = '0' + duration
   }
   var formatted = minutes + ':' + duration;
   if (hours > 0)
   {
     formatted = hours + ':' + formatted;
   }
   return formatted;
}


function formatDuration(jq, song, playlistInfo)
{
   jq.html(formatDurationValue(song['duration']));
}

function addStarRatings(jq, rating)
{
   var stars = 0;
   while (rating >= 2)
   {
       jq.append($('<img id="star-' + stars + '" class="ratings" src="/static/images/star-full.png" width="18">'));
       rating -= 2;
       stars++;
   }
   if (rating >= 1)
   {
       jq.append($('<img id="star-' + stars + '" class="ratings" src="/static/images/star-half.png" width="18">'));
       stars++;
   }
   while (stars < 5)
   {
       jq.append($('<img id="star-' + stars + '" class="ratings" src="/static/images/star-empty.png" width="18">'));
       stars++;
   }
}

function formatSongRatings(jq, song, playlistInfo)
{
   var rating = song['rating'];
   var div=$('<div class="ratings"/>');
   if (rating[1] == 'avg')
       div.addClass('avg-ratings')
   else if (rating[1] == null)
       div.addClass('no-ratings')

   addStarRatings(div, rating[0]);
   jq.append(div);
   div.on( "click", { song_id: song['song_id'] }, function( event ) {
        var rect = event.currentTarget.getBoundingClientRect();
        var x = rect.left + (window.pageXOffset || document.documentElement.scrollLeft);
        var percentage = (event.pageX - x)/(event.target.width*5);
        new_rating = Math.round(percentage * 10);
        bard.metadataManager.set_song_ratings(event.data.song_id, new_rating, function(rating)
        {
            var div = $( event.currentTarget )
            div.empty();
            div.removeClass('avg-ratings no-ratings');
            addStarRatings(div, rating);
        });
        event.preventDefault();
   });
}

function formatAlbumRatings(jq, album)
{
   var rating = album['rating'];
   var div=$('<div class="ratings"/>');
   if (rating[1] == 'avg')
       div.addClass('avg-ratings')
   else if (rating[1] == null)
       div.addClass('no-ratings')

   addStarRatings(div, rating[0]);
   jq.append(div);
   div.on( "click", { album_id: album['album_id'] }, function( event ) {
        var rect = event.currentTarget.getBoundingClientRect();
        var x = rect.left + (window.pageXOffset || document.documentElement.scrollLeft);
        var percentage = (event.pageX - x)/(event.target.width*5);
        new_rating = Math.round(percentage * 10);
        bard.metadataManager.set_album_ratings(event.data.album_id, new_rating, function(rating)
        {
            var div = $( event.currentTarget )
            div.empty();
            div.removeClass('avg-ratings no-ratings');
            addStarRatings(div, rating);
        });
        event.preventDefault();
   });
}

function formatReleaseGroupRatings(jq, rg)
{
   var rating = rg['rating'];
   var div=$('<div class="ratings"/>');
   if (rating[1] == 'avg')
       div.addClass('avg-ratings')
   else if (rating[1] == null)
       div.addClass('no-ratings')

   addStarRatings(div, rating[0]);
   jq.append(div);
   div.on( "click", { release_group_id: rg['id'] }, function( event ) {
        var rect = event.currentTarget.getBoundingClientRect();
        var x = rect.left + (window.pageXOffset || document.documentElement.scrollLeft);
        var percentage = (event.pageX - x)/(event.target.width*5);
        new_rating = Math.round(percentage * 10);
        bard.metadataManager.set_release_group_ratings(event.data.release_group_id, new_rating, function(rating)
        {
            var div = $( event.currentTarget )
            div.empty();
            div.removeClass('avg-ratings no-ratings');
            addStarRatings(div, rating);
        });
        event.preventDefault();
   });
}

const columns_base = [['#', ['position', 'track_position']],
           ['Name', formatSongName],
           ['Artist', formatArtist_from_song],
           ['Ratings', formatSongRatings],
           ['Length', formatDuration ]];

function append_rows_to_table_of_songs(songs, table, uniquesuffix='0', playlistInfo=null, release_column=false, add_header_row=true)
{
    var i, j, col;

    var columns = [...columns_base];
    if (release_column) {
        columns.splice(2, 0, ['Release', formatRelease])
    }

    if (add_header_row) {
        var r = "";
        columns.forEach((col,i) => {
            r+= '<th>' + col[0] + '</th>';
        });
        var trh = $("<tr/>").append(r);
        table.append(trh);
    }

    songs.forEach((song,i) => {
        var songid = 'song-'+i+'-'+uniquesuffix;
        var tmpPlaylistInfo = $.extend({index: i, track_position: song['track_position']},playlistInfo);
        var tr = $("<tr/>");
        if (song['song_id'] == null)
        {
            tr.addClass('unavailableSong');
        };
        columns.forEach((col,j) => {
            var td = $("<td/>", { appendTo: tr})
            if (typeof(col[1]) =="function")
            {
                col[1](td, song, tmpPlaylistInfo);
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
                td.html(song[col[1]]);
            }
        });

        table.append(tr);

        setDraggable(tr, {'application/x-bard': JSON.stringify({'songID': song['song_id']})});
    });

    return table;
}

function add_table_of_songs(songs, appendToObj, uniquesuffix='0', playlistInfo=null, release_column=false, add_header_row=true)
{
    var table = $("<table/>", { appendTo: appendToObj });
    return append_rows_to_table_of_songs(songs, table, uniquesuffix, playlistInfo, release_column, add_header_row);
}

/**
 * Formatting songs and playlists (end)
 */

function openAbout(push_to_history=true)
{
    if (push_to_history)
    {
        var path = "/about"
        window.history.pushState({path: path}, "", path);
    }
    $( "#container" ).html("<p>About Bard</p>");
}

function dateTupleToString(tuple)
{
    var r = tuple[0] || null;
    if (r && tuple[1])
    {
        r += "-" + tuple[1];
        if (tuple[2])
            r += "-" + tuple[2];
    };
    return r;
}

function dateTuplesRangeToString(begin, end)
{
    begin_date = dateTupleToString(begin);
    end_date = dateTupleToString(end);
    if (begin_date && end_date)
        return begin_date + " – " + end_date;
    if (begin_date)
        return begin_date + " –";
    if (end_date)
        return "– " + end_date;
    return null;
}

function setCurrentSongInfo(id, metadata)
{
    if (id == current_song_id)
    {
        $( "#current-song-title" ).html(metadata.title);
        $( "#current-song-artist" ).html(metadata.artist);
    }
}

function openAlbum( id )
{
    openComponent('album', {id: id});
}

function openArtist( id )
{
    openComponent('artist', {id: id});
}


function submitLogin()
{
    username=$("#username").val();
    password=$("#password").val();

    $.ajax({
      url: "/login",
      method: "post",
      data: {
        username: username,
        password: password
      },
      success: function( result ) {
          openComponent('search');
      },
      error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
      }
    });
}

function openSearchQuery(search_query, push_to_history=false)
{
    openComponent('search', search_query, push_to_history=push_to_history, callback=function() {
            $("#searchBar").val(search_query['query']);
            searchView.performSearch(false);
        });
}

window.onpopstate = function( event ) {
    if (event.state)
        bard.openPath(event.state['path'], push_to_history=false);
    else
    {
        var path = window.location.pathname + window.location.search;
        bard.openPath(path, push_to_history=false);
    }
}


function Bard()
{
    $( "#nav-search" ).on( "click", function( event ) {
        openComponent('search');
        event.preventDefault();
    });

    $( "#nav-artists" ).on( "click", function( event ) {
        openComponent('artists');
        event.preventDefault();
    });

    $( "#nav-albums" ).on( "click", function( event ) {
        openComponent('albums');
        event.preventDefault();
    });

    $( "#nav-genres" ).on( "click", function( event ) {
        openComponent('genres');
        event.preventDefault();
    });

    $( "#nav-configuration" ).on( "click", function( event ) {
        if ( !$('[data-dialog-name=configuration]').length )
            bard.openDialog('configuration');
        event.preventDefault();
    });

    fillPlaylists();
    this.metadataManager = new MetadataManager();
    //document.requestFullScreen();
    this.base = window.location.protocol + '//' + window.location.host;

    $.when(
        $.getScript("/static/js/player-controls.js"),
        $.getScript("/static/js/webplayer.js").fail(function(jqxhr, settings, exception) { alert('error' + exception); }),
        $.Deferred(function( deferred ){
            $( deferred.resolve );
        })
    ).done(function(){
        this.player = new WebPlayer();
        this.controls = new PlayerControls();
        this.controls.player = this.player;
        this.player.ui = this.controls;
        console.log('loaded ' + this.player + this.controls );
    }.bind(this));

    this.playSongFromPlaylist = function(song_id, playlist_song_info)
    {
        current_playlist_song_info = playlist_song_info;
        this.playSong(song_id);
    }

    this.playSong = function(id)
    {
        current_song_id = id;
        $( "#current-song-cover" ).attr("src", this.base + "/api/v1/coverart/song/" + id)
        var metadata = this.metadataManager.get_song_metadata( id, setCurrentSongInfo );
        $( "#player" ).attr("src", this.base + "/api/v1/audio/song/" + id)
        bard.controls.setEnable(true);
    }

    this.requestPrevSong = function()
    {
    };

    this.requestNextSong = function()
    {
        $.ajax({
          type: "POST",
          url: "/api/v1/playlist/current/next_song",
          data: current_playlist_song_info,
          success: function( result ) {
              bard.playSongFromPlaylist(result.song_id, result);
          }
        });
    }

    this.openPath = function(path, push_to_history=false)
    {
        if (path == '')
        {
            bard.setTitle('');
            return;
        }
        var sep_pos = path.indexOf('?');
        if (sep_pos == -1)
        {
            var page = path;
            var query = null;
        }
        else
        {
            var page = path.slice(0, sep_pos);
            var query = parse_query(path.slice(sep_pos+1));
        }
        if (page[0] == '/' && page.length > 1)
            page = page.slice(1);

        if (page == 'search' && query)
            openSearchQuery(query, push_to_history);
        else
            openComponent(page, query, push_to_history);
    };

    this.setTitle = function(title, context=null)
    {
        if (title)
            document.title = 'Bard - ' + title;
        else
            document.title = 'Bard';

    }

    this.openDialog = function(dialog_name)
    {
        $.ajax({
            url: "/dialog/" + dialog_name
        }).done(
            function( result, textStatus, jqXHR ) {
                var dialog = $('<div/>', {'data-dialog-name': dialog_name});
                $(document.body).append(dialog);
                dialog.dialog({
                    title: dialog_name,
                    width: 500,
                    height: 500,
                });
                dialog.html(result);
                console.log('dialog_name: ' + dialog_name);
                dialog.on('dialogclose', function(event, ui) {
                    console.log(event);
                    console.log(ui);
                    $(event.target).remove();
                });
        }).fail(
            function( jqXHR, textStatus, errorThrown) {
                alert(textStatus + "\n" + errorThrown);
        });
    }

    this.fillSelectOptions = function(object, options, selected_idx)
    {
        object.empty();
        for (var i = 0; i < options.length; i++)
        {
            $('<option/>', {
                selected: i == selected_idx? true: false,
                text: options[i],
                appendTo: object
            });
        }
    }
};


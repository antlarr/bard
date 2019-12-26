var current_song_id = 0;

function openComponent(page, data=null, push_to_history=true, callback=null)
{
    if (push_to_history)
        window.history.pushState({page: 'openComponent', component: page, data:data}, "", "/");
    $.ajax({
        url: "/component/" + page,
        data: data,
        success: function( result ) {
            $( "#container" ).html( result );
            if (callback) callback();
        },
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
    // $( "#container" ).html("<p>Login!</p>");
}

function openAbout(push_to_history=true)
{
    if (push_to_history)
        window.history.pushState({page: 'openAbout'}, "", "/");
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

function performSearch(push_to_history=true)
{
    searchText=$("#searchBar").val();
    if (push_to_history)
        window.history.pushState({page: 'performSearch', query: searchText}, "", "/");
    $.ajax({
      url: "/api/v1/search",
      data: {
        query: searchText
      },
      success: function( result ) {
        r="";
        for (i=0 ; i< result.length; i++)
        {
            r+="<br><a onclick=\"playSong(" + result[i].id + ")\">" + result[i].path + "</a>";
        };
        $( "#searchResult" ).html( r );
        set_song_metadata_cache( result );
      }
    });
}

function setCurrentSongInfo(id, metadata)
{
    if (id == current_song_id)
    {
        $( "#current-song-title" ).html(metadata.title);
        $( "#current-song-artist" ).html(metadata.artist);
    }
}

function playSong(id)
{
    current_song_id = id;
    base=window.location.protocol + '//' + window.location.host;
    $( "#current-song-cover" ).attr("src", base + "/api/v1/coverart/song/" + id)
    var metadata = get_song_metadata( id, setCurrentSongInfo );
    if (metadata)
    {
        setCurrentSongInfo(id, metadata);
    }
    $( "#player" ).attr("src", base + "/api/v1/audio/song/" + id)
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

$( "#nav-home" ).on( "click", function( event ) {
    openComponent('home');
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

window.onpopstate = function( event ) {
    switch (event.state['page'])
    {
       case 'openComponent':
            openComponent(event.state['component'], event.state['data'], false, null);
            break;
       case 'openAbout':
            openAbout(false);
            break;
       case 'performSearch':
            openComponent('home', null, push_to_history=false, callback= function() {
               $("#searchBar").val(event.state['query']);
               performSearch(false);
             });
            break;
    }
}


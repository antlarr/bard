var current_song_id = 0;

function openComponent(page)
{
    $.ajax({
        url: "/component/" + page,
        data: {
            zipcode: 97201
        },
        success: function( result ) {
            $( "#container" ).html( result );
        },
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
    // $( "#container" ).html("<p>Login!</p>");
}

function openAbout()
{
    $( "#container" ).html("<p>About Bard</p>");
}

function performSearch()
{
    searchText=$("#searchBar").val();
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

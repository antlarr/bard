var searchResultOffset = 0;
var page_size = 100;

function songsSearchResultReceived( result )
{
    console.log(result);
    var playlistInfo = {
        query: result.query,
    };
    if (searchResultOffset == 0) {
        jq_table = add_table_of_songs(result.songs, $( "#searchResult" ), 0, playlistInfo, true );
        jq_table.addClass('playlist');
        jq_table.attr('id', 'searchResultTable');
    } else {
        append_rows_to_table_of_songs(result.songs, $( "#searchResultTable" ), 0, playlistInfo, true, false );
    }

    searchResultOffset += result.songs.length;
}

function requestSearchSongs(query, offset, count)
{
    $.ajax({
      url: "/api/v1/song/search",
      data: {
        query: query,
        offset: offset,
        page_size: count
      },
      success: songsSearchResultReceived
    });
}

function performSearch(push_to_history=true)
{
    searchQuery = $("#searchBar").val();
    bard.lastSearchQuery = searchQuery;
    if (push_to_history)
        window.history.pushState({page: 'performSearch', query: searchQuery}, "", "/");
    $.ajax({
      url: "/api/v1/song/search",
      data: {
        query: searchQuery
      },
      success: songsSearchResultReceived
    });
}



function SearchView()
{
    this.search_result_offset = 0;
    this.page_size = 100;

    this.clearResults = function( result )
    {
        $( "#searchResult" ).empty();
        this.search_result_offset = 0;
    }

    this.songsSearchResultReceived = function( result )
    {
        var playlistInfo = {
            playlist_type: 'search',
            search_playlist_id: result.search_playlist_id,
        };
        this.search_playlist_id = result.search_playlist_id;
        this.search_query = result.search_query;

        if (this.search_result_offset == 0) {
            jq_table = add_table_of_songs(result.songs, $( "#searchResult" ), 0, playlistInfo, true );
            jq_table.addClass('playlist');
            jq_table.attr('id', 'searchResultTable');
        } else {
            append_rows_to_table_of_songs(result.songs, $( "#searchResultTable" ), 0, playlistInfo, true, false );
        }

        this.search_result_offset += result.songs.length;
    }

    this.performSearch = function(push_to_history=true)
    {

        search_query = {query: $("#searchBar").val(),
                        context: ''}
        if (push_to_history)
        {
            path = "/search?query=" + encodeURIComponent(search_query['query'])+ "&context=" + search_query['context'];
            window.history.pushState({path: path}, "", path);
        }
        $.ajax({
          url: "/api/v1/song/search",
          data: search_query,
          success: function(result)
            {
                this.clearResults();
                this.songsSearchResultReceived(result);
            }.bind(this)
        });
    }


    this.requestSearchSongs = function(offset, count)
    {
        $.ajax({
          url: "/api/v1/song/search",
          data: {
            search_playlist_id: this.search_playlist_id,
            offset: offset,
            page_size: count
          },
          success: this.songsSearchResultReceived.bind(this)
        });
    };

    this.requestMoreSearchResults = function()
    {
        this.requestSearchSongs(this.search_result_offset, this.page_size);
    };
}

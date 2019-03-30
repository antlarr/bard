var metadata_cache = {};


function get_song_metadata(id, callback)
{
    var r = metadata_cache["id" + id]
    if (r) return r;

    $.ajax({
        url: "/api/v1/metadata/song/" + id,
        success: function( result ) {
            callback(id, result[0]);
        },
        error: function( jqXHR, textStatus, errorThrown) {
            alert(textStatus + "\n" + errorThrown);
        }
    });
    return undefined;
}


function clear_metadata_cache(id)
{
    metadata_cache = {}
}

function set_song_metadata_cache(list)
{
    clear_metadata_cache();
/*    for (i=0 ; i< list.length; i++)
    {
        metadata_cache["id" + list[i].id] = list[i]
    };
    */
}

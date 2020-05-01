/**
 * TODO: Implement a real lru cache
 */
function Cache()
{
    this.data = {},
    this.set = function(id, value) {
        this.data[id] = value;
    };
    this.get = function(id) {
        return this.data[id];
    };
    this.contains = function(id) {
        return this.data.hasOwnProperty(id) && this.data[id] != null;
    }
}

function MetadataManager()
{
    this.song_metadata_cache = new Cache();
    this.song_metadata_callbacks = {};
    this.artist_credits_cache = new Cache();
    this.artist_credits_callbacks = {};

    this.get_song_metadata = function(song_id, callback, pre_callback=null)
    {
        info = this.song_metadata_cache.get(song_id);
        if (info != null)
        {
            callback(song_id, info);
            return;
        }

        if (pre_callback)
            pre_callback();

        callback_list = this.song_metadata_callbacks[song_id];
        if (callback_list != null)
        {
            callback_list.push(callback);
            return;
        }

        this.song_metadata_callbacks[song_id] = [callback]
        $.ajax({
            url: "/api/v1/metadata/song/" + song_id,
            success: function( data, textStatus, jqXHR) {
                meta = bard.metadataManager;
                meta.song_metadata_cache.set(song_id, data);
                meta.song_metadata_callbacks[song_id].forEach(callback => callback(song_id, data));
                delete meta.song_metadata_callbacks[song_id];
            },
            error: function( jqXHR, textStatus, errorThrown) {
                alert(textStatus + "\n" + errorThrown);
            }
        });
    }

    /**
     * If the info for artist_credit_id is available inmediately,
     * callback is called at once.
     * Otherwise, pre_callback is called inmediately and callback
     * is called when the info is available.
     */
    this.get_artist_credit_info = function(artist_credit_id, callback, pre_callback=null)
    {
        info = this.artist_credits_cache.get(artist_credit_id);
        if (info != null)
        {
            callback(info);
            return;
        }

        if (pre_callback)
            pre_callback();

        callback_list = this.artist_credits_callbacks[artist_credit_id];
        if (callback_list != null)
        {
            callback_list.push(callback);
            return;
        }

        this.artist_credits_callbacks[artist_credit_id] = [callback]
        $.ajax({
            url: "/api/v1/artist_credit/info",
            data: {id: artist_credit_id},
            success: function( data, textStatus, jqXHR) {
                meta = bard.metadataManager;
                meta.artist_credits_cache.set(artist_credit_id, data);
                meta.artist_credits_callbacks[artist_credit_id].forEach(callback => callback(data));
                delete meta.artist_credits_callbacks[artist_credit_id];
            },
            error: function( jqXHR, textStatus, errorThrown) {
                alert(textStatus + "\n" + errorThrown);
            }
        });
    }

    this.set_song_ratings = function(song_id, rating, callback)
    {
        $.ajax({
            url: "/api/v1/song/set_ratings",
            data: {id: song_id,
                   rating: rating},
            success: function( data, textStatus, jqXHR) {
                callback(rating);
            },
            error: function( jqXHR, textStatus, errorThrown) {
                alert(textStatus + "\n" + errorThrown);
            }
        });
    }
}

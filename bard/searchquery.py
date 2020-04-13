class SearchQuery:
    def __init__(self):
        """Create a SearchQuery object."""
        self.search_playlist_id = None
        self.query = None
        self.context = None
        self.owner_id = None
        self.offset = None
        self.page_size = None

    @staticmethod
    def from_request(request, owner_id, playlist_manager):
        sq = SearchQuery()
        spid = request.args.get('search_playlist_id', default=None, type=int)
        if spid is not None:
            sq.search_playlist_id = spid
            pl = playlist_manager.get_search_playlist(spid, owner_id)
            if not pl:
                return None
            sq.query = pl.query.query
            sq.context = pl.query.context
        else:
            try:
                sq.query = request.args['query']
            except KeyError:
                return None
            sq.context = request.args.get('context', default='')
        sq.owner_id = owner_id
        sq.offset = request.args.get('offset', default=0, type=int)
        sq.page_size = request.args.get('page_size', default=200, type=int)
        return sq

    def key(self):
        return hash(f'{self.context}:{self.owner_id}:{self.query}')

    def as_dict(self):
        return {'query': self.query,
                'context': self.context}

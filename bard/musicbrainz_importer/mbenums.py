from bard.musicdatabase import DatabaseEnum

musicbrainz_enums = {}
musicbrainz_enums['enum_area_type_values'] = \
    DatabaseEnum('area_type', schema='musicbrainz')
musicbrainz_enums['enum_artist_type_values'] = \
    DatabaseEnum('artist_type', schema='musicbrainz')
musicbrainz_enums['enum_artist_alias_type_values'] = \
    DatabaseEnum('artist_alias_type', schema='musicbrainz')
musicbrainz_enums['enum_release_group_type_values'] = \
    DatabaseEnum('release_group_type', schema='musicbrainz')
musicbrainz_enums['enum_release_status_values'] = \
    DatabaseEnum('release_status', schema='musicbrainz')
musicbrainz_enums['enum_language_values'] = \
    DatabaseEnum('language', schema='musicbrainz')
musicbrainz_enums['enum_gender_values'] = \
    DatabaseEnum('gender', schema='musicbrainz')
musicbrainz_enums['enum_country_values'] = \
    DatabaseEnum('country', schema='musicbrainz')
musicbrainz_enums['enum_medium_format_values'] = \
    DatabaseEnum('medium_format', schema='musicbrainz')
musicbrainz_enums['enum_work_type_values'] = \
    DatabaseEnum('work_type', schema='musicbrainz')
musicbrainz_enums['enum_label_type_values'] = \
    DatabaseEnum('label_type', schema='musicbrainz')
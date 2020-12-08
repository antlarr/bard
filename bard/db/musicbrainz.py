from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy import Integer, Text, Boolean, SmallInteger, String
from sqlalchemy.sql import expression
from sqlalchemy_utils import UUIDType
from bard.db.core import metadata


# Enum types

def create_mbenum_table(type_name):
    return Table(f'enum_{type_name}_values', metadata,
                 Column('id_value', Integer, primary_key=True,
                        autoincrement=True),
                 Column('name', Text),
                 schema='musicbrainz')


EnumAreaTypeValues = create_mbenum_table('area_type')
EnumArtistTypeValues = create_mbenum_table('artist_type')
EnumArtistAliasTypeValues = create_mbenum_table('artist_alias_type')
EnumEventTypeValues = create_mbenum_table('event_type')
EnumRecordingAliasTypeValues = create_mbenum_table('recording_alias_type')
EnumReleaseGroupTypeValues = create_mbenum_table('release_group_type')
EnumReleaseGroupSecondaryTypeValues = \
    create_mbenum_table('release_group_secondary_type')
EnumReleaseStatusValues = create_mbenum_table('release_status')
EnumLanguageValues = create_mbenum_table('language')
EnumGenderValues = create_mbenum_table('gender')
EnumLabelTypeValues = create_mbenum_table('label_type')
EnumMediumFormatValues = create_mbenum_table('medium_format')
EnumWorkTypeValues = create_mbenum_table('work_type')
EnumPlaceTypeValues = create_mbenum_table('place_type')
EnumSeriesTypeValues = create_mbenum_table('series_type')
EnumInstrumentTypeValues = create_mbenum_table('instrument_type')


# MusicBrainz schema (lite) core


Area = \
    Table('area', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('area_type', Integer,
                 ForeignKey(EnumAreaTypeValues.c.id_value,
                            ondelete='CASCADE')),
          schema='musicbrainz')

Event = \
    Table('event', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('event_type', Integer,
                 ForeignKey(EnumEventTypeValues.c.id_value,
                            ondelete='CASCADE')),
          Column('begin_date_year', SmallInteger),
          Column('begin_date_month', SmallInteger),
          Column('begin_date_day', SmallInteger),
          Column('end_date_year', SmallInteger),
          Column('end_date_month', SmallInteger),
          Column('end_date_day', SmallInteger),
          Column('setlist', Text),
          Column('comment', Text),
          schema='musicbrainz')

Place = \
    Table('place', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('disambiguation', Text),
          Column('place_type', Integer,
                 ForeignKey(EnumPlaceTypeValues.c.id_value,
                            ondelete='CASCADE')),
          Column('area_id', Integer,
                 ForeignKey(Area.c.id, ondelete='CASCADE')),
          schema='musicbrainz')

Label = \
    Table('label', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('disambiguation', Text),
          Column('label_type', Integer,
                 ForeignKey(EnumLabelTypeValues.c.id_value,
                            ondelete='CASCADE')),
          Column('area_id', Integer,
                 ForeignKey(Area.c.id, ondelete='CASCADE')),
          Column('begin_date_year', SmallInteger),
          Column('begin_date_month', SmallInteger),
          Column('begin_date_day', SmallInteger),
          Column('end_date_year', SmallInteger),
          Column('end_date_month', SmallInteger),
          Column('end_date_day', SmallInteger),
          schema='musicbrainz')


Artist = \
    Table('artist', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('disambiguation', Text),
          Column('sort_name', Text),
          Column('artist_type', Integer,
                 ForeignKey(EnumArtistTypeValues.c.id_value,
                            ondelete='CASCADE')),
          Column('gender', Integer,
                 ForeignKey(EnumGenderValues.c.id_value,
                            ondelete='CASCADE')),
          Column('area_id', Integer,
                 ForeignKey(Area.c.id,
                            ondelete='CASCADE')),
          schema='musicbrainz')


ArtistCredit = \
    Table('artist_credit', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('name', Text, nullable=False),
          schema='musicbrainz')


ArtistCreditName = \
    Table('artist_credit_name', metadata,
          Column('artist_credit_id', Integer,
                 ForeignKey(ArtistCredit.c.id,
                            ondelete='CASCADE'),
                 index=True),
          Column('artist_id', Integer,
                 ForeignKey(Artist.c.id,
                            ondelete='CASCADE'),
                 index=True),
          Column('position', SmallInteger),
          Column('name', Text),
          Column('join_phrase', Text, server_default=''),
          schema='musicbrainz')


ReleaseGroup = \
    Table('release_group', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('disambiguation', Text),
          Column('release_group_type', Integer,
                 ForeignKey(EnumReleaseGroupTypeValues.c.id_value,
                            ondelete='CASCADE')),
          Column('artist_credit_id', Integer,
                 ForeignKey(ArtistCredit.c.id,
                            ondelete='CASCADE'),
                 index=True),
          schema='musicbrainz')


ReleaseGroupSecondaryTypeJoin = \
    Table('release_group_secondary_type_join', metadata,
          Column('release_group_id', Integer,
                 ForeignKey(ReleaseGroup.c.id,
                            ondelete='CASCADE'),
                 primary_key=True),
          Column('secondary_type', Integer,
                 ForeignKey(EnumReleaseGroupSecondaryTypeValues.c.id_value,
                            ondelete='CASCADE'),
                 nullable=False),
          schema='musicbrainz')

Release = \
    Table('release', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('disambiguation', Text),
          Column('artist_credit_id', Integer,
                 ForeignKey(ArtistCredit.c.id,
                            ondelete='CASCADE'),
                 index=True),
          Column('release_group_id', Integer,
                 ForeignKey(ReleaseGroup.c.id,
                            ondelete='CASCADE'),
                 index=True),
          Column('release_status', Integer,
                 ForeignKey(EnumReleaseStatusValues.c.id_value,
                            ondelete='CASCADE')),
          Column('language', Integer,
                 ForeignKey(EnumLanguageValues.c.id_value,
                            ondelete='CASCADE')),
          Column('barcode', Text),
          schema='musicbrainz')


Recording = \
    Table('recording', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('disambiguation', Text),
          Column('artist_credit_id', Integer,
                 ForeignKey(ArtistCredit.c.id,
                            ondelete='CASCADE'),
                 index=True),
          schema='musicbrainz')


Medium = \
    Table('medium', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('release_id', Integer,
                 ForeignKey(Release.c.id,
                            ondelete='CASCADE'),
                 index=True),
          Column('position', Integer),
          Column('format', Integer,
                 ForeignKey(EnumMediumFormatValues.c.id_value,
                            ondelete='CASCADE')),
          Column('name', Text, nullable=False, server_default=''),
          schema='musicbrainz')


Track = \
    Table('track', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('recording_id', Integer,
                 ForeignKey(Recording.c.id,
                            ondelete='CASCADE'),
                 index=True),
          Column('medium_id', Integer,
                 ForeignKey(Medium.c.id,
                            ondelete='CASCADE'),
                 index=True),
          Column('position', Integer, nullable=False),
          Column('number_text', Text, nullable=False),
          Column('name', Text, nullable=False),

          Column('artist_credit_id', Integer,
                 ForeignKey(ArtistCredit.c.id,
                            ondelete='CASCADE')),
          Column('length', Integer),
          Column('is_data_track', Boolean, server_default=expression.false()),
          schema='musicbrainz')

Work = \
    Table('work', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('disambiguation', Text),
          Column('work_type', Integer,
                 ForeignKey(EnumWorkTypeValues.c.id_value,
                            ondelete='CASCADE')),
          schema='musicbrainz')

Series = \
    Table('series', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('disambiguation', Text),
          Column('series_type', Integer,
                 ForeignKey(EnumSeriesTypeValues.c.id_value,
                            ondelete='CASCADE')),
          schema='musicbrainz')

Instrument = \
    Table('instrument', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('type', Integer,
                 ForeignKey(EnumInstrumentTypeValues.c.id_value,
                            ondelete='CASCADE')),
          schema='musicbrainz')

ReleaseCountry = \
    Table('release_country', metadata,
          Column('release_id', Integer,
                 ForeignKey(Release.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('country_id', Integer,
                 ForeignKey(Area.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, nullable=False),
          Column('date_year', SmallInteger),
          Column('date_month', SmallInteger),
          Column('date_day', SmallInteger),
          schema='musicbrainz')

ReleaseUnknownCountry = \
    Table('release_unknown_country', metadata,
          Column('release_id', Integer,
                 ForeignKey(Release.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('date_year', SmallInteger),
          Column('date_month', SmallInteger),
          Column('date_day', SmallInteger),
          schema='musicbrainz')

ReleaseLabel = \
    Table('release_label', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=False),
          Column('release_id', Integer,
                 ForeignKey(Release.c.id,
                            ondelete='CASCADE'),
                 index=True, nullable=False),
          Column('label_id', Integer,
                 ForeignKey(Label.c.id,
                            ondelete='CASCADE')),
          Column('catalog_number', String(length=255)),
          schema='musicbrainz')


LinkType = \
    Table('link_type', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False,
                 index=True),
          Column('entity_type0', Text, nullable=False),
          Column('entity_type1', Text, nullable=False),
          Column('description', Text),
          Column('link_phrase', Text),
          Column('reverse_link_phrase', Text),
          Column('long_link_phrase', Text),
          Column('entity0_cardinality', Integer),
          Column('entity1_cardinality', Integer),
          schema='musicbrainz')

Link = \
    Table('link', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('link_type_id', Integer,
                 ForeignKey(LinkType.c.id,
                            ondelete='CASCADE'),
                 index=True, nullable=False),
          Column('begin_date_year', SmallInteger),
          Column('begin_date_month', SmallInteger),
          Column('begin_date_day', SmallInteger),
          Column('end_date_year', SmallInteger),
          Column('end_date_month', SmallInteger),
          Column('end_date_day', SmallInteger),
          schema='musicbrainz')

LinkAttributeType = \
    Table('link_attribute_type', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('parent', Integer,
                 ForeignKey("musicbrainz.link_attribute_type.id",
                            ondelete='CASCADE'),
                 index=True),
          Column('root', Integer,
                 ForeignKey("musicbrainz.link_attribute_type.id",
                            ondelete='CASCADE'),
                 index=True, nullable=False),
          Column('child_order', Integer, server_default='0', nullable=False),
          Column('mbid', UUIDType(binary=False), nullable=False,
                 index=True, unique=True),
          Column('name', Text, nullable=False),
          Column('description', Text),
          schema='musicbrainz')

LinkAttribute = \
    Table('link_attribute', metadata,
          Column('link_id', Integer,
                 ForeignKey(Link.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('link_attribute_type_id', Integer,
                 ForeignKey(LinkAttributeType.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          schema='musicbrainz')

LinkAttributeCredit = \
    Table('link_attribute_credit', metadata,
          Column('link_id', Integer,
                 ForeignKey(Link.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('link_attribute_type_id', Integer,
                 ForeignKey(LinkAttributeType.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('credited_as', Text, nullable=False),
          schema='musicbrainz')


# Aliases

ArtistAlias = \
    Table('artist_alias', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('artist_id', Integer,
                 ForeignKey(Artist.c.id,
                            ondelete='CASCADE'),
                 index=True),
          Column('name', Text),
          Column('sort_name', Text),
          Column('locale', Text),
          Column('artist_alias_type', Integer,
                 ForeignKey(EnumArtistAliasTypeValues.c.id_value,
                            ondelete='CASCADE')),
          Column('primary_for_locale', Boolean,
                 server_default=expression.false(), nullable=False),
          schema='musicbrainz')

RecordingAlias = \
    Table('recording_alias', metadata,
          Column('id', Integer, primary_key=True,
                 autoincrement=True),
          Column('recording_id', Integer,
                 ForeignKey(Recording.c.id,
                            ondelete='CASCADE'),
                 index=True),
          Column('name', Text),
          Column('sort_name', Text),
          Column('locale', Text),
          Column('recording_alias_type', Integer,
                 ForeignKey(EnumRecordingAliasTypeValues.c.id_value,
                            ondelete='CASCADE')),
          Column('primary_for_locale', Boolean,
                 server_default=expression.false(), nullable=False),
          schema='musicbrainz')

# Relations


def create_relation_table(entity0, entity1):
    return Table(f'l_{entity0}_{entity1}', metadata,
                 Column('id', Integer, primary_key=True,
                        autoincrement=True),
                 Column('link_id', Integer,
                        ForeignKey(Link.c.id, ondelete='CASCADE'),
                        nullable=False),
                 Column('entity0', Integer,
                        ForeignKey(f'musicbrainz.{entity0}.id',
                                   ondelete='CASCADE'),
                        nullable=False),
                 Column('entity1', Integer,
                        ForeignKey(f'musicbrainz.{entity1}.id',
                                   ondelete='CASCADE'),
                        nullable=False),
                 Column('link_order', Integer),
                 Column('entity0_credit', Text),
                 Column('entity1_credit', Text),
                 schema='musicbrainz')


entities = ['area', 'artist', 'event', 'instrument', 'label', 'place',
            'recording', 'release', 'release_group', 'series', 'work']
remaining_entities = entities[:]

relation_tables = {}

for entity0 in entities:
    for entity1 in remaining_entities:
        relation_tables[(entity0, entity1)] = \
            create_relation_table(entity0, entity1)
    remaining_entities.remove(entity0)

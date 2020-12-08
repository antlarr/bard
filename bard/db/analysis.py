from sqlalchemy import Table, Column, ForeignKey, PrimaryKeyConstraint
from sqlalchemy import Integer, REAL, ARRAY, Text
from bard.db.core import metadata, Songs
from sqlalchemy.types import TypeDecorator
import json


RhythmBeatsLoudnessStats = \
    Table('rhythm__beats_loudness_stats', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('mean', REAL),
          Column('minimum', REAL),
          Column('maximum', REAL),
          Column('stdev', REAL),
          Column('var', REAL),
          Column('median', REAL),
          Column('dmean', REAL),
          Column('dmean2', REAL),
          Column('dvar', REAL),
          Column('dvar2', REAL),
          schema='analysis')


class ArrayOfReals(TypeDecorator):
    impl = ARRAY(REAL)

    def process_bind_param(self, value, dialect):
        if dialect.name == 'sqlite':
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if dialect.name == 'sqlite':
            return json.loads(value)
        return value

    def load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(Text)
        return dialect.type_descriptor(ARRAY(REAL))


LowlevelGFCCMean = \
    Table('lowlevel__gfcc__mean', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('values', ArrayOfReals),
          schema='analysis')


LowlevelMFCCMean = \
    Table('lowlevel__mfcc__mean', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('values', ArrayOfReals),
          schema='analysis')


RhythmBeatsLoudness = \
    Table('rhythm__beats_loudness', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 index=True, nullable=False),
          Column('pos', Integer, nullable=False),
          Column('value', REAL),
          PrimaryKeyConstraint('song_id', 'pos',
                               name='rhythm__beats_loudness_song_id_pos_key'),
          schema='analysis')

RhythmBeatsPosition = \
    Table('rhythm__beats_position', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 index=True, nullable=False),
          Column('pos', Integer, nullable=False),
          Column('value', REAL),
          PrimaryKeyConstraint('song_id', 'pos',
                               name='rhythm__beats_position_song_id_pos_key'),
          schema='analysis')

RhythmBpmHistogram = \
    Table('rhythm__bpm_histogram', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 index=True, nullable=False),
          Column('pos', Integer, nullable=False),
          Column('value', REAL),
          PrimaryKeyConstraint('song_id', 'pos',
                               name='rhythm__bpm_histogram_song_id_pos_key'),
          schema='analysis')

TonalChordsHistogram = \
    Table('tonal__chords_histogram', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 index=True, nullable=False),
          Column('pos', Integer, nullable=False),
          Column('value', REAL),
          PrimaryKeyConstraint('song_id', 'pos',
                               name='tonal__chords_histogram_song_id_pos_key'),
          schema='analysis')

TonalTHPCP = \
    Table('tonal__thpcp', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 index=True, nullable=False),
          Column('pos', Integer, nullable=False),
          Column('value', REAL),
          PrimaryKeyConstraint('song_id', 'pos',
                               name='tonal__thpcp_song_id_pos_key'),
          schema='analysis')

Highlevel = \
    Table('highlevel', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('danceable', REAL),
          Column('gender_female', REAL),
          Column('acoustic', REAL),
          Column('aggressive', REAL),
          Column('electronic', REAL),
          Column('happy', REAL),
          Column('party', REAL),
          Column('relaxed', REAL),
          Column('sad', REAL),
          Column('bright', REAL),
          Column('atonal', REAL),
          Column('instrumental', REAL),
          schema='analysis')

Lowlevel = \
    Table('lowlevel', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('average_loudness', REAL),
          Column('dynamic_complexity', REAL),
          Column('loudness_ebu128_integrated', REAL),
          Column('loudness_ebu128_loudness_range', REAL),
          schema='analysis')

Version = \
    Table('version', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('essentia', Text),
          schema='analysis')

Rhythm = \
    Table('rhythm', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('beats_count', REAL),
          Column('bpm', REAL),
          Column('bpm_histogram_first_peak_bpm', REAL),
          Column('bpm_histogram_first_peak_weight', REAL),
          Column('bpm_histogram_second_peak_bpm', REAL),
          Column('bpm_histogram_second_peak_spread', REAL),
          Column('bpm_histogram_second_peak_weight', REAL),
          Column('danceability', REAL),
          Column('onset_rate', REAL),
          schema='analysis')


Tonal = \
    Table('tonal', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('chords_changes_rate', REAL),
          Column('chords_key', Text),
          Column('chords_number_rate', REAL),
          Column('chords_scale', Text),
          Column('key_edma_key', Text),
          Column('key_edma_scale', Text),
          Column('key_edma_strength', REAL),
          Column('key_krumhansl_key', Text),
          Column('key_krumhansl_scale', Text),
          Column('key_krumhansl_strength', REAL),
          Column('key_temperley_key', Text),
          Column('key_temperley_scale', Text),
          Column('key_temperley_strength', REAL),
          Column('tuning_diatonic_strength', REAL),
          Column('tuning_equal_tempered_deviation', REAL),
          Column('tuning_frequency', REAL),
          Column('tuning_nontempered_energy_ratio', REAL),
          schema='analysis')


HighlevelGenreDortmund = \
    Table('highlevel__genre_dortmund', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('value', Text),
          Column('probability', REAL),
          Column('alternative', REAL),
          Column('blues', REAL),
          Column('electronic', REAL),
          Column('folkcountry', REAL),
          Column('funksoulrnb', REAL),
          Column('jazz', REAL),
          Column('pop', REAL),
          Column('raphiphop', REAL),
          Column('rock', REAL),
          schema='analysis')

HighlevelGenreElectronic = \
    Table('highlevel__genre_electronic', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('value', Text),
          Column('probability', REAL),
          Column('ambient', REAL),
          Column('dnb', REAL),
          Column('house', REAL),
          Column('techno', REAL),
          Column('trance', REAL),
          schema='analysis')

HighlevelGenreRosamerica = \
    Table('highlevel__genre_rosamerica', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('value', Text),
          Column('probability', REAL),
          Column('cla', REAL),
          Column('dan', REAL),
          Column('hip', REAL),
          Column('jaz', REAL),
          Column('pop', REAL),
          Column('rhy', REAL),
          Column('roc', REAL),
          Column('spe', REAL),
          schema='analysis')

HighlevelGenreTzanetakis = \
    Table('highlevel__genre_tzanetakis', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('value', Text),
          Column('probability', REAL),
          Column('blu', REAL),
          Column('cla', REAL),
          Column('cou', REAL),
          Column('dis', REAL),
          Column('hip', REAL),
          Column('jaz', REAL),
          Column('met', REAL),
          Column('pop', REAL),
          Column('reg', REAL),
          Column('roc', REAL),
          schema='analysis')

HighlevelIsmir04Rhythm = \
    Table('highlevel__ismir04_rhythm', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('value', Text),
          Column('probability', REAL),
          Column('chachacha', REAL),
          Column('jive', REAL),
          Column('quickstep', REAL),
          Column('rumba_american', REAL),
          Column('rumba_international', REAL),
          Column('rumba_misc', REAL),
          Column('samba', REAL),
          Column('tango', REAL),
          Column('viennesewaltz', REAL),
          Column('waltz', REAL),
          schema='analysis')

HighlevelMoodsMirez = \
    Table('highlevel__moods_mirex', metadata,
          Column('song_id', Integer,
                 ForeignKey(Songs.c.id,
                            ondelete='CASCADE'),
                 primary_key=True, index=True, nullable=False),
          Column('value', Text),
          Column('probability', REAL),
          Column('cluster1', REAL),
          Column('cluster2', REAL),
          Column('cluster3', REAL),
          Column('cluster4', REAL),
          Column('cluster5', REAL),
          schema='analysis')

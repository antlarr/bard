"""analysis tables

Revision ID: fedc1349bd1a
Revises: 3891d7a39db9
Create Date: 2024-04-28 13:41:18.888988

"""
from alembic import op
import sqlalchemy as sa
import bard.db.analysis as bard_db_analysis


# revision identifiers, used by Alembic.
revision = 'fedc1349bd1a'
down_revision = '3891d7a39db9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA analysis")

    op.create_table('highlevel',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('danceable', sa.REAL(), nullable=True),
    sa.Column('gender_female', sa.REAL(), nullable=True),
    sa.Column('acoustic', sa.REAL(), nullable=True),
    sa.Column('aggressive', sa.REAL(), nullable=True),
    sa.Column('electronic', sa.REAL(), nullable=True),
    sa.Column('happy', sa.REAL(), nullable=True),
    sa.Column('party', sa.REAL(), nullable=True),
    sa.Column('relaxed', sa.REAL(), nullable=True),
    sa.Column('sad', sa.REAL(), nullable=True),
    sa.Column('bright', sa.REAL(), nullable=True),
    sa.Column('atonal', sa.REAL(), nullable=True),
    sa.Column('instrumental', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_highlevel_song_id'), 'highlevel', ['song_id'], unique=False, schema='analysis')
    op.create_table('highlevel__genre_dortmund',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('probability', sa.REAL(), nullable=True),
    sa.Column('alternative', sa.REAL(), nullable=True),
    sa.Column('blues', sa.REAL(), nullable=True),
    sa.Column('electronic', sa.REAL(), nullable=True),
    sa.Column('folkcountry', sa.REAL(), nullable=True),
    sa.Column('funksoulrnb', sa.REAL(), nullable=True),
    sa.Column('jazz', sa.REAL(), nullable=True),
    sa.Column('pop', sa.REAL(), nullable=True),
    sa.Column('raphiphop', sa.REAL(), nullable=True),
    sa.Column('rock', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_highlevel__genre_dortmund_song_id'), 'highlevel__genre_dortmund', ['song_id'], unique=False, schema='analysis')
    op.create_table('highlevel__genre_electronic',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('probability', sa.REAL(), nullable=True),
    sa.Column('ambient', sa.REAL(), nullable=True),
    sa.Column('dnb', sa.REAL(), nullable=True),
    sa.Column('house', sa.REAL(), nullable=True),
    sa.Column('techno', sa.REAL(), nullable=True),
    sa.Column('trance', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_highlevel__genre_electronic_song_id'), 'highlevel__genre_electronic', ['song_id'], unique=False, schema='analysis')
    op.create_table('highlevel__genre_rosamerica',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('probability', sa.REAL(), nullable=True),
    sa.Column('cla', sa.REAL(), nullable=True),
    sa.Column('dan', sa.REAL(), nullable=True),
    sa.Column('hip', sa.REAL(), nullable=True),
    sa.Column('jaz', sa.REAL(), nullable=True),
    sa.Column('pop', sa.REAL(), nullable=True),
    sa.Column('rhy', sa.REAL(), nullable=True),
    sa.Column('roc', sa.REAL(), nullable=True),
    sa.Column('spe', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_highlevel__genre_rosamerica_song_id'), 'highlevel__genre_rosamerica', ['song_id'], unique=False, schema='analysis')
    op.create_table('highlevel__genre_tzanetakis',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('probability', sa.REAL(), nullable=True),
    sa.Column('blu', sa.REAL(), nullable=True),
    sa.Column('cla', sa.REAL(), nullable=True),
    sa.Column('cou', sa.REAL(), nullable=True),
    sa.Column('dis', sa.REAL(), nullable=True),
    sa.Column('hip', sa.REAL(), nullable=True),
    sa.Column('jaz', sa.REAL(), nullable=True),
    sa.Column('met', sa.REAL(), nullable=True),
    sa.Column('pop', sa.REAL(), nullable=True),
    sa.Column('reg', sa.REAL(), nullable=True),
    sa.Column('roc', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_highlevel__genre_tzanetakis_song_id'), 'highlevel__genre_tzanetakis', ['song_id'], unique=False, schema='analysis')
    op.create_table('highlevel__ismir04_rhythm',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('probability', sa.REAL(), nullable=True),
    sa.Column('chachacha', sa.REAL(), nullable=True),
    sa.Column('jive', sa.REAL(), nullable=True),
    sa.Column('quickstep', sa.REAL(), nullable=True),
    sa.Column('rumba_american', sa.REAL(), nullable=True),
    sa.Column('rumba_international', sa.REAL(), nullable=True),
    sa.Column('rumba_misc', sa.REAL(), nullable=True),
    sa.Column('samba', sa.REAL(), nullable=True),
    sa.Column('tango', sa.REAL(), nullable=True),
    sa.Column('viennesewaltz', sa.REAL(), nullable=True),
    sa.Column('waltz', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_highlevel__ismir04_rhythm_song_id'), 'highlevel__ismir04_rhythm', ['song_id'], unique=False, schema='analysis')
    op.create_table('highlevel__moods_mirex',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('value', sa.Text(), nullable=True),
    sa.Column('probability', sa.REAL(), nullable=True),
    sa.Column('cluster1', sa.REAL(), nullable=True),
    sa.Column('cluster2', sa.REAL(), nullable=True),
    sa.Column('cluster3', sa.REAL(), nullable=True),
    sa.Column('cluster4', sa.REAL(), nullable=True),
    sa.Column('cluster5', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_highlevel__moods_mirex_song_id'), 'highlevel__moods_mirex', ['song_id'], unique=False, schema='analysis')
    op.create_table('lowlevel',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('average_loudness', sa.REAL(), nullable=True),
    sa.Column('dynamic_complexity', sa.REAL(), nullable=True),
    sa.Column('loudness_ebu128_integrated', sa.REAL(), nullable=True),
    sa.Column('loudness_ebu128_loudness_range', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_lowlevel_song_id'), 'lowlevel', ['song_id'], unique=False, schema='analysis')
    op.create_table('lowlevel__gfcc__mean',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('values', bard_db_analysis.ArrayOfReals(sa.REAL()), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_lowlevel__gfcc__mean_song_id'), 'lowlevel__gfcc__mean', ['song_id'], unique=False, schema='analysis')
    op.create_table('lowlevel__mfcc__mean',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('values', bard_db_analysis.ArrayOfReals(sa.REAL()), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_lowlevel__mfcc__mean_song_id'), 'lowlevel__mfcc__mean', ['song_id'], unique=False, schema='analysis')
    op.create_table('rhythm',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('beats_count', sa.REAL(), nullable=True),
    sa.Column('bpm', sa.REAL(), nullable=True),
    sa.Column('bpm_histogram_first_peak_bpm', sa.REAL(), nullable=True),
    sa.Column('bpm_histogram_first_peak_weight', sa.REAL(), nullable=True),
    sa.Column('bpm_histogram_second_peak_bpm', sa.REAL(), nullable=True),
    sa.Column('bpm_histogram_second_peak_spread', sa.REAL(), nullable=True),
    sa.Column('bpm_histogram_second_peak_weight', sa.REAL(), nullable=True),
    sa.Column('danceability', sa.REAL(), nullable=True),
    sa.Column('onset_rate', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_rhythm_song_id'), 'rhythm', ['song_id'], unique=False, schema='analysis')
    op.create_table('rhythm__beats_loudness',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('pos', sa.Integer(), nullable=False),
    sa.Column('value', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id', 'pos', name='rhythm__beats_loudness_song_id_pos_key'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_rhythm__beats_loudness_song_id'), 'rhythm__beats_loudness', ['song_id'], unique=False, schema='analysis')
    op.create_table('rhythm__beats_loudness_stats',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('mean', sa.REAL(), nullable=True),
    sa.Column('minimum', sa.REAL(), nullable=True),
    sa.Column('maximum', sa.REAL(), nullable=True),
    sa.Column('stdev', sa.REAL(), nullable=True),
    sa.Column('var', sa.REAL(), nullable=True),
    sa.Column('median', sa.REAL(), nullable=True),
    sa.Column('dmean', sa.REAL(), nullable=True),
    sa.Column('dmean2', sa.REAL(), nullable=True),
    sa.Column('dvar', sa.REAL(), nullable=True),
    sa.Column('dvar2', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_rhythm__beats_loudness_stats_song_id'), 'rhythm__beats_loudness_stats', ['song_id'], unique=False, schema='analysis')
    op.create_table('rhythm__beats_position',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('pos', sa.Integer(), nullable=False),
    sa.Column('value', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id', 'pos', name='rhythm__beats_position_song_id_pos_key'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_rhythm__beats_position_song_id'), 'rhythm__beats_position', ['song_id'], unique=False, schema='analysis')
    op.create_table('rhythm__bpm_histogram',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('pos', sa.Integer(), nullable=False),
    sa.Column('value', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id', 'pos', name='rhythm__bpm_histogram_song_id_pos_key'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_rhythm__bpm_histogram_song_id'), 'rhythm__bpm_histogram', ['song_id'], unique=False, schema='analysis')
    op.create_table('tonal',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('chords_changes_rate', sa.REAL(), nullable=True),
    sa.Column('chords_key', sa.Text(), nullable=True),
    sa.Column('chords_number_rate', sa.REAL(), nullable=True),
    sa.Column('chords_scale', sa.Text(), nullable=True),
    sa.Column('key_edma_key', sa.Text(), nullable=True),
    sa.Column('key_edma_scale', sa.Text(), nullable=True),
    sa.Column('key_edma_strength', sa.REAL(), nullable=True),
    sa.Column('key_krumhansl_key', sa.Text(), nullable=True),
    sa.Column('key_krumhansl_scale', sa.Text(), nullable=True),
    sa.Column('key_krumhansl_strength', sa.REAL(), nullable=True),
    sa.Column('key_temperley_key', sa.Text(), nullable=True),
    sa.Column('key_temperley_scale', sa.Text(), nullable=True),
    sa.Column('key_temperley_strength', sa.REAL(), nullable=True),
    sa.Column('tuning_diatonic_strength', sa.REAL(), nullable=True),
    sa.Column('tuning_equal_tempered_deviation', sa.REAL(), nullable=True),
    sa.Column('tuning_frequency', sa.REAL(), nullable=True),
    sa.Column('tuning_nontempered_energy_ratio', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_tonal_song_id'), 'tonal', ['song_id'], unique=False, schema='analysis')
    op.create_table('tonal__chords_histogram',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('pos', sa.Integer(), nullable=False),
    sa.Column('value', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id', 'pos', name='tonal__chords_histogram_song_id_pos_key'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_tonal__chords_histogram_song_id'), 'tonal__chords_histogram', ['song_id'], unique=False, schema='analysis')
    op.create_table('tonal__thpcp',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('pos', sa.Integer(), nullable=False),
    sa.Column('value', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id', 'pos', name='tonal__thpcp_song_id_pos_key'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_tonal__thpcp_song_id'), 'tonal__thpcp', ['song_id'], unique=False, schema='analysis')
    op.create_table('version',
    sa.Column('song_id', sa.Integer(), nullable=False),
    sa.Column('essentia', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['song_id'], ['songs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('song_id'),
    schema='analysis'
    )
    op.create_index(op.f('ix_analysis_version_song_id'), 'version', ['song_id'], unique=False, schema='analysis')


def downgrade():
    op.drop_index(op.f('ix_analysis_version_song_id'), table_name='version', schema='analysis')
    op.drop_table('version', schema='analysis')
    op.drop_index(op.f('ix_analysis_tonal__thpcp_song_id'), table_name='tonal__thpcp', schema='analysis')
    op.drop_table('tonal__thpcp', schema='analysis')
    op.drop_index(op.f('ix_analysis_tonal__chords_histogram_song_id'), table_name='tonal__chords_histogram', schema='analysis')
    op.drop_table('tonal__chords_histogram', schema='analysis')
    op.drop_index(op.f('ix_analysis_tonal_song_id'), table_name='tonal', schema='analysis')
    op.drop_table('tonal', schema='analysis')
    op.drop_index(op.f('ix_analysis_rhythm__bpm_histogram_song_id'), table_name='rhythm__bpm_histogram', schema='analysis')
    op.drop_table('rhythm__bpm_histogram', schema='analysis')
    op.drop_index(op.f('ix_analysis_rhythm__beats_position_song_id'), table_name='rhythm__beats_position', schema='analysis')
    op.drop_table('rhythm__beats_position', schema='analysis')
    op.drop_index(op.f('ix_analysis_rhythm__beats_loudness_stats_song_id'), table_name='rhythm__beats_loudness_stats', schema='analysis')
    op.drop_table('rhythm__beats_loudness_stats', schema='analysis')
    op.drop_index(op.f('ix_analysis_rhythm__beats_loudness_song_id'), table_name='rhythm__beats_loudness', schema='analysis')
    op.drop_table('rhythm__beats_loudness', schema='analysis')
    op.drop_index(op.f('ix_analysis_rhythm_song_id'), table_name='rhythm', schema='analysis')
    op.drop_table('rhythm', schema='analysis')
    op.drop_index(op.f('ix_analysis_lowlevel__mfcc__mean_song_id'), table_name='lowlevel__mfcc__mean', schema='analysis')
    op.drop_table('lowlevel__mfcc__mean', schema='analysis')
    op.drop_index(op.f('ix_analysis_lowlevel__gfcc__mean_song_id'), table_name='lowlevel__gfcc__mean', schema='analysis')
    op.drop_table('lowlevel__gfcc__mean', schema='analysis')
    op.drop_index(op.f('ix_analysis_lowlevel_song_id'), table_name='lowlevel', schema='analysis')
    op.drop_table('lowlevel', schema='analysis')
    op.drop_index(op.f('ix_analysis_highlevel__moods_mirex_song_id'), table_name='highlevel__moods_mirex', schema='analysis')
    op.drop_table('highlevel__moods_mirex', schema='analysis')
    op.drop_index(op.f('ix_analysis_highlevel__ismir04_rhythm_song_id'), table_name='highlevel__ismir04_rhythm', schema='analysis')
    op.drop_table('highlevel__ismir04_rhythm', schema='analysis')
    op.drop_index(op.f('ix_analysis_highlevel__genre_tzanetakis_song_id'), table_name='highlevel__genre_tzanetakis', schema='analysis')
    op.drop_table('highlevel__genre_tzanetakis', schema='analysis')
    op.drop_index(op.f('ix_analysis_highlevel__genre_rosamerica_song_id'), table_name='highlevel__genre_rosamerica', schema='analysis')
    op.drop_table('highlevel__genre_rosamerica', schema='analysis')
    op.drop_index(op.f('ix_analysis_highlevel__genre_electronic_song_id'), table_name='highlevel__genre_electronic', schema='analysis')
    op.drop_table('highlevel__genre_electronic', schema='analysis')
    op.drop_index(op.f('ix_analysis_highlevel__genre_dortmund_song_id'), table_name='highlevel__genre_dortmund', schema='analysis')
    op.drop_table('highlevel__genre_dortmund', schema='analysis')
    op.drop_index(op.f('ix_analysis_highlevel_song_id'), table_name='highlevel', schema='analysis')
    op.drop_table('highlevel', schema='analysis')

    op.execute("DROP SCHEMA analysis")

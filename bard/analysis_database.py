# https://essentia.upf.edu/reference/std_MusicExtractor.html
from bard.musicdatabase import MusicDatabase, table
from bard import essentia_helper  # noqa
try:
    from essentia.standard import MusicExtractor
except ImportError:
    pass
from sqlalchemy import text
import os
import tempfile
import subprocess

conversion_dict = {
    'highlevel.danceability.all.danceable': ('highlevel', 'danceable'),
    'highlevel.gender.all.female': ('highlevel', 'gender_female'),
    'highlevel.mood_acoustic.all.acoustic': ('highlevel', 'acoustic'),
    'highlevel.mood_aggressive.all.aggressive': ('highlevel', 'aggressive'),
    'highlevel.mood_electronic.all.electronic': ('highlevel', 'electronic'),
    'highlevel.mood_happy.all.happy': ('highlevel', 'happy'),
    'highlevel.mood_party.all.party': ('highlevel', 'party'),
    'highlevel.mood_relaxed.all.relaxed': ('highlevel', 'relaxed'),
    'highlevel.mood_sad.all.sad': ('highlevel', 'sad'),
    'highlevel.timbre.all.bright': ('highlevel', 'bright'),
    'highlevel.tonal_atonal.all.atonal': ('highlevel', 'atonal'),
    'highlevel.voice_instrumental.all.instrumental':
        ('highlevel', 'instrumental'),

    'lowlevel.average_loudness': ('lowlevel', 'average_loudness'),
    'lowlevel.dynamic_complexity': ('lowlevel', 'dynamic_complexity'),
    'lowlevel.loudness_ebu128.integrated':
        ('lowlevel', 'loudness_ebu128_integrated'),
    'lowlevel.loudness_ebu128.loudness_range':
        ('lowlevel', 'loudness_ebu128_loudness_range'),

    'metadata.version.essentia': ('version', 'essentia'),

    'rhythm.beats_count': ('rhythm', 'beats_count'),
    'rhythm.bpm': ('rhythm', 'bpm'),
    'rhythm.bpm_histogram_first_peak_bpm':
        ('rhythm', 'bpm_histogram_first_peak_bpm'),
    'rhythm.bpm_histogram_first_peak_weight':
        ('rhythm', 'bpm_histogram_first_peak_weight'),
    'rhythm.bpm_histogram_second_peak_bpm':
        ('rhythm', 'bpm_histogram_second_peak_bpm'),
    'rhythm.bpm_histogram_second_peak_spread':
        ('rhythm', 'bpm_histogram_second_peak_spread'),
    'rhythm.bpm_histogram_second_peak_weight':
        ('rhythm', 'bpm_histogram_second_peak_weight'),
    'rhythm.danceability': ('rhythm', 'danceability'),
    'rhythm.onset_rate': ('rhythm', 'onset_rate'),

    'tonal.chords_changes_rate': ('tonal', 'chords_changes_rate'),
    'tonal.chords_key': ('tonal', 'chords_key'),
    'tonal.chords_number_rate': ('tonal', 'chords_number_rate'),
    'tonal.chords_scale': ('tonal', 'chords_scale'),
    'tonal.key_edma.key': ('tonal', 'key_edma_key'),
    'tonal.key_edma.scale': ('tonal', 'key_edma_scale'),
    'tonal.key_edma.strength': ('tonal', 'key_edma_strength'),
    'tonal.key_krumhansl.key': ('tonal', 'key_krumhansl_key'),
    'tonal.key_krumhansl.scale': ('tonal', 'key_krumhansl_scale'),
    'tonal.key_krumhansl.strength': ('tonal', 'key_krumhansl_strength'),
    'tonal.key_temperley.key': ('tonal', 'key_temperley_key'),
    'tonal.key_temperley.scale': ('tonal', 'key_temperley_scale'),
    'tonal.key_temperley.strength': ('tonal', 'key_temperley_strength'),
    'tonal.tuning_diatonic_strength': ('tonal', 'tuning_diatonic_strength'),
    'tonal.tuning_equal_tempered_deviation':
        ('tonal', 'tuning_equal_tempered_deviation'),
    'tonal.tuning_frequency': ('tonal', 'tuning_frequency'),
    'tonal.tuning_nontempered_energy_ratio':
        ('tonal', 'tuning_nontempered_energy_ratio'),

    'highlevel.genre_dortmund.value': ('highlevel__genre_dortmund', 'value'),
    'highlevel.genre_dortmund.probability':
        ('highlevel__genre_dortmund', 'probability'),
    'highlevel.genre_dortmund.all.alternative':
        ('highlevel__genre_dortmund', 'alternative'),
    'highlevel.genre_dortmund.all.blues':
        ('highlevel__genre_dortmund', 'blues'),
    'highlevel.genre_dortmund.all.electronic':
        ('highlevel__genre_dortmund', 'electronic'),
    'highlevel.genre_dortmund.all.folkcountry':
        ('highlevel__genre_dortmund', 'folkcountry'),
    'highlevel.genre_dortmund.all.funksoulrnb':
        ('highlevel__genre_dortmund', 'funksoulrnb'),
    'highlevel.genre_dortmund.all.jazz': ('highlevel__genre_dortmund', 'jazz'),
    'highlevel.genre_dortmund.all.pop': ('highlevel__genre_dortmund', 'pop'),
    'highlevel.genre_dortmund.all.raphiphop':
        ('highlevel__genre_dortmund', 'raphiphop'),
    'highlevel.genre_dortmund.all.rock': ('highlevel__genre_dortmund', 'rock'),
    'highlevel.genre_electronic.value':
        ('highlevel__genre_electronic', 'value'),
    'highlevel.genre_electronic.probability':
        ('highlevel__genre_electronic', 'probability'),
    'highlevel.genre_electronic.all.ambient':
        ('highlevel__genre_electronic', 'ambient'),
    'highlevel.genre_electronic.all.dnb':
        ('highlevel__genre_electronic', 'dnb'),
    'highlevel.genre_electronic.all.house':
        ('highlevel__genre_electronic', 'house'),
    'highlevel.genre_electronic.all.techno':
        ('highlevel__genre_electronic', 'techno'),
    'highlevel.genre_electronic.all.trance':
        ('highlevel__genre_electronic', 'trance'),
    'highlevel.genre_rosamerica.value':
        ('highlevel__genre_rosamerica', 'value'),
    'highlevel.genre_rosamerica.probability':
        ('highlevel__genre_rosamerica', 'probability'),
    'highlevel.genre_rosamerica.all.cla':
        ('highlevel__genre_rosamerica', 'cla'),
    'highlevel.genre_rosamerica.all.dan':
        ('highlevel__genre_rosamerica', 'dan'),
    'highlevel.genre_rosamerica.all.hip':
        ('highlevel__genre_rosamerica', 'hip'),
    'highlevel.genre_rosamerica.all.jaz':
        ('highlevel__genre_rosamerica', 'jaz'),
    'highlevel.genre_rosamerica.all.pop':
        ('highlevel__genre_rosamerica', 'pop'),
    'highlevel.genre_rosamerica.all.rhy':
        ('highlevel__genre_rosamerica', 'rhy'),
    'highlevel.genre_rosamerica.all.roc':
        ('highlevel__genre_rosamerica', 'roc'),
    'highlevel.genre_rosamerica.all.spe':
        ('highlevel__genre_rosamerica', 'spe'),
    'highlevel.genre_tzanetakis.value':
        ('highlevel__genre_tzanetakis', 'value'),
    'highlevel.genre_tzanetakis.probability':
        ('highlevel__genre_tzanetakis', 'probability'),
    'highlevel.genre_tzanetakis.all.blu':
        ('highlevel__genre_tzanetakis', 'blu'),
    'highlevel.genre_tzanetakis.all.cla':
        ('highlevel__genre_tzanetakis', 'cla'),
    'highlevel.genre_tzanetakis.all.cou':
        ('highlevel__genre_tzanetakis', 'cou'),
    'highlevel.genre_tzanetakis.all.dis':
        ('highlevel__genre_tzanetakis', 'dis'),
    'highlevel.genre_tzanetakis.all.hip':
        ('highlevel__genre_tzanetakis', 'hip'),
    'highlevel.genre_tzanetakis.all.jaz':
        ('highlevel__genre_tzanetakis', 'jaz'),
    'highlevel.genre_tzanetakis.all.met':
        ('highlevel__genre_tzanetakis', 'met'),
    'highlevel.genre_tzanetakis.all.pop':
        ('highlevel__genre_tzanetakis', 'pop'),
    'highlevel.genre_tzanetakis.all.reg':
        ('highlevel__genre_tzanetakis', 'reg'),
    'highlevel.genre_tzanetakis.all.roc':
        ('highlevel__genre_tzanetakis', 'roc'),
    'highlevel.ismir04_rhythm.value':
        ('highlevel__ismir04_rhythm', 'value'),
    'highlevel.ismir04_rhythm.probability':
        ('highlevel__ismir04_rhythm', 'probability'),
    'highlevel.ismir04_rhythm.all.ChaChaCha':
        ('highlevel__ismir04_rhythm', 'chachacha'),
    'highlevel.ismir04_rhythm.all.Jive':
        ('highlevel__ismir04_rhythm', 'jive'),
    'highlevel.ismir04_rhythm.all.Quickstep':
        ('highlevel__ismir04_rhythm', 'quickstep'),
    'highlevel.ismir04_rhythm.all.Rumba-American':
        ('highlevel__ismir04_rhythm', 'rumba_american'),
    'highlevel.ismir04_rhythm.all.Rumba-International':
        ('highlevel__ismir04_rhythm', 'rumba_international'),
    'highlevel.ismir04_rhythm.all.Rumba-Misc':
        ('highlevel__ismir04_rhythm', 'rumba_misc'),
    'highlevel.ismir04_rhythm.all.Samba':
        ('highlevel__ismir04_rhythm', 'samba'),
    'highlevel.ismir04_rhythm.all.Tango':
        ('highlevel__ismir04_rhythm', 'tango'),
    'highlevel.ismir04_rhythm.all.VienneseWaltz':
        ('highlevel__ismir04_rhythm', 'viennesewaltz'),
    'highlevel.ismir04_rhythm.all.Waltz':
        ('highlevel__ismir04_rhythm', 'waltz'),
    'highlevel.moods_mirex.value':
        ('highlevel__moods_mirex', 'value'),
    'highlevel.moods_mirex.probability':
        ('highlevel__moods_mirex', 'probability'),
    'highlevel.moods_mirex.all.Cluster1':
        ('highlevel__moods_mirex', 'cluster1'),
    'highlevel.moods_mirex.all.Cluster2':
        ('highlevel__moods_mirex', 'cluster2'),
    'highlevel.moods_mirex.all.Cluster3':
        ('highlevel__moods_mirex', 'cluster3'),
    'highlevel.moods_mirex.all.Cluster4':
        ('highlevel__moods_mirex', 'cluster4'),
    'highlevel.moods_mirex.all.Cluster5':
        ('highlevel__moods_mirex', 'cluster5')
}

keys_with_stats = ['lowlevel.barkbands_crest',
                   'lowlevel.barkbands_flatness_db',
                   'lowlevel.barkbands_kurtosis',
                   'lowlevel.barkbands_skewness',
                   'lowlevel.barkbands_spread', 'lowlevel.dissonance',
                   'lowlevel.erbbands_crest',
                   'lowlevel.erbbands_flatness_db',
                   'lowlevel.erbbands_kurtosis', 'lowlevel.erbbands_skewness',
                   'lowlevel.erbbands_spread', 'lowlevel.hfc',
                   'lowlevel.loudness_ebu128.momentary',
                   'lowlevel.loudness_ebu128.short_term',
                   'lowlevel.melbands_crest',
                   'lowlevel.melbands_flatness_db',
                   'lowlevel.melbands_kurtosis', 'lowlevel.melbands_skewness',
                   'lowlevel.melbands_spread', 'lowlevel.pitch_salience',
                   'lowlevel.silence_rate_20dB', 'lowlevel.silence_rate_30dB',
                   'lowlevel.silence_rate_60dB', 'lowlevel.spectral_centroid',
                   'lowlevel.spectral_complexity',
                   'lowlevel.spectral_decrease', 'lowlevel.spectral_energy',
                   'lowlevel.spectral_energyband_high',
                   'lowlevel.spectral_energyband_low',
                   'lowlevel.spectral_energyband_middle_high',
                   'lowlevel.spectral_energyband_middle_low',
                   'lowlevel.spectral_entropy', 'lowlevel.spectral_flux',
                   'lowlevel.spectral_kurtosis', 'lowlevel.spectral_rms',
                   'lowlevel.spectral_rolloff', 'lowlevel.spectral_skewness',
                   'lowlevel.spectral_spread', 'lowlevel.spectral_strongpeak',
                   'lowlevel.zerocrossingrate', 'rhythm.beats_loudness',
                   'tonal.chords_strength',
                   'tonal.hpcp_crest', 'tonal.hpcp_entropy']


# stats keys with lists for stats variables
keys_with_lists_stats = ['lowlevel.barkbands',
                         'lowlevel.erbbands',
                         'lowlevel.melbands',
                         'lowlevel.melbands128',
                         'lowlevel.spectral_contrast_coeffs',
                         'lowlevel.spectral_contrast_valleys',
                         'rhythm.beats_loudness_band_ratio',
                         'tonal.hpcp']

# stats keys with lists
keys_with_lists = ['lowlevel.gfcc.mean', 'lowlevel.mfcc.mean']

# frame keys with lists of values
fkeys_with_lists = ['lowlevel.barkbands_crest',
                    'lowlevel.barkbands_flatness_db',
                    'lowlevel.barkbands_kurtosis',
                    'lowlevel.barkbands_skewness',
                    'lowlevel.barkbands_spread',
                    'lowlevel.dissonance',
                    'lowlevel.erbbands_crest',
                    'lowlevel.erbbands_flatness_db',
                    'lowlevel.erbbands_kurtosis',
                    'lowlevel.erbbands_skewness',
                    'lowlevel.erbbands_spread',
                    'lowlevel.hfc',
                    'lowlevel.loudness_ebu128.momentary',
                    'lowlevel.loudness_ebu128.short_term',
                    'lowlevel.melbands_crest',
                    'lowlevel.melbands_flatness_db',
                    'lowlevel.melbands_kurtosis',
                    'lowlevel.melbands_skewness',
                    'lowlevel.melbands_spread',
                    'lowlevel.pitch_salience',
                    'lowlevel.silence_rate_20dB',
                    'lowlevel.silence_rate_30dB',
                    'lowlevel.silence_rate_60dB',
                    'lowlevel.spectral_centroid',
                    'lowlevel.spectral_complexity',
                    'lowlevel.spectral_decrease',
                    'lowlevel.spectral_energy',
                    'lowlevel.spectral_energyband_high',
                    'lowlevel.spectral_energyband_low',
                    'lowlevel.spectral_energyband_middle_high',
                    'lowlevel.spectral_energyband_middle_low',
                    'lowlevel.spectral_entropy',
                    'lowlevel.spectral_flux',
                    'lowlevel.spectral_kurtosis',
                    'lowlevel.spectral_rms',
                    'lowlevel.spectral_rolloff',
                    'lowlevel.spectral_skewness',
                    'lowlevel.spectral_spread',
                    'lowlevel.spectral_strongpeak',
                    'lowlevel.zerocrossingrate',
                    'rhythm.beats_loudness',
                    'tonal.chords_strength',
                    'tonal.hpcp_crest',
                    'tonal.hpcp_entropy',
                    'rhythm.beats_position',
                    'rhythm.bpm_histogram',
                    'tonal.chords_histogram',
                    'tonal.thpcp']

# frame keys with lists of lists of values

fkeys_with_lists_of_lists = [('lowlevel.barkbands', 27),
                             ('lowlevel.erbbands', 40),
                             ('lowlevel.gfcc', 13),
                             ('lowlevel.melbands', 40),
                             ('lowlevel.melbands128', 128),
                             ('lowlevel.mfcc', 13),
                             ('lowlevel.spectral_contrast_coeffs', 6),
                             ('lowlevel.spectral_contrast_valleys', 6),
                             ('rhythm.beats_loudness_band_ratio', 6),
                             ('tonal.hpcp', 36)]

# lowlevel.barkbands is a list of 9273 lists of 27 values
# lowlevel.erbbands is a list of 9273 lists of 40 values
# lowlevel.melbands is a list of 9273 lists of 40 values
# lowlevel.melbands128 is a list of 9273 lists of 128 values
# lowlevel.gfcc is a list of 9273 lists of 13 values
# lowlevel.mfcc is a list of 9273 lists of 13 values
# lowlevel.spectral_contrast_coeffs is a list of 9273 lists of 6 values
# lowlevel.spectral_contrast_valleys is a list of 9273 lists of 6 values
# rhythm.beats_loudness_band_ratio is a list of 394 lists of 6 values
# tonal.hpcp is a list of 4637 lists of 36 values

# stat_variables = [x[25:]
#                   for x in keys if x.startswith('lowlevel.barkbands_crest')]
stat_variables = {'mean': 'mean',
                  'min': 'minimum',
                  'max': 'maximum',
                  'stdev': 'stdev',
                  'var': 'var',
                  'median': 'median',
                  'dmean': 'dmean',
                  'dmean2': 'dmean2',
                  'dvar': 'dvar',
                  'dvar2': 'dvar2'}


# Storing everything in the database is _too_much_
# Just for 179 songs, this is the space used by the largest tables:
#
# > select concat(schemaname, '.', tablename),
#          pg_total_relation_size( concat(schemaname, '.', tablename))
#    from  pg_catalog.pg_tables
#    where schemaname='analysis' order by 2;
#
# analysis.lowlevel__loudness_ebu128__short_term        |     49438720
# analysis.lowlevel__loudness_ebu128__momentary         |     49848320
# analysis.tonal__hpcp_crest                            |    105766912
# analysis.tonal__chords_strength                       |    105766912
# analysis.tonal__hpcp_entropy                          |    105766912
# analysis.lowlevel__spectral_rolloff                   |    210616320
# analysis.lowlevel__spectral_rms                       |    210616320
# analysis.lowlevel__spectral_energyband_middle_high    |    210616320
# analysis.lowlevel__spectral_strongpeak                |    210624512
# analysis.lowlevel__spectral_energyband_middle_low     |    210624512
# analysis.lowlevel__spectral_entropy                   |    210624512
# analysis.lowlevel__spectral_flux                      |    210624512
# analysis.lowlevel__spectral_kurtosis                  |    210624512
# analysis.lowlevel__spectral_skewness                  |    210624512
# analysis.lowlevel__spectral_spread                    |    210624512
# analysis.lowlevel__zerocrossingrate                   |    210624512
# analysis.lowlevel__spectral_energyband_low            |    211349504
# analysis.lowlevel__melbands_crest                     |    212140032
# analysis.lowlevel__melbands_flatness_db               |    212140032
# analysis.lowlevel__melbands_kurtosis                  |    212140032
# analysis.lowlevel__erbbands_spread                    |    212148224
# analysis.lowlevel__hfc                                |    212148224
# analysis.lowlevel__barkbands_crest                    |    212148224
# analysis.lowlevel__barkbands_flatness_db              |    212148224
# analysis.lowlevel__barkbands_kurtosis                 |    212148224
# analysis.lowlevel__spectral_decrease                  |    212148224
# analysis.lowlevel__spectral_energyband_high           |    212148224
# analysis.lowlevel__spectral_energy                    |    212148224
# analysis.lowlevel__barkbands_skewness                 |    212156416
# analysis.lowlevel__spectral_complexity                |    212156416
# analysis.lowlevel__spectral_centroid                  |    212156416
# analysis.lowlevel__silence_rate_60db                  |    212156416
# analysis.lowlevel__silence_rate_30db                  |    212156416
# analysis.lowlevel__silence_rate_20db                  |    212156416
# analysis.lowlevel__pitch_salience                     |    212156416
# analysis.lowlevel__melbands_spread                    |    212156416
# analysis.lowlevel__melbands_skewness                  |    212156416
# analysis.lowlevel__erbbands_skewness                  |    212156416
# analysis.lowlevel__erbbands_kurtosis                  |    212156416
# analysis.lowlevel__erbbands_flatness_db               |    212156416
# analysis.lowlevel__erbbands_crest                     |    212156416
# analysis.lowlevel__dissonance                         |    212156416
# analysis.lowlevel__barkbands_spread                   |    212156416
# analysis.tonal__hpcp                                  |    295223296
# analysis.lowlevel__spectral_contrast_coeffs           |    305414144
# analysis.lowlevel__spectral_contrast_valleys          |    305422336
# analysis.lowlevel__gfcc                               |    382296064
# analysis.lowlevel__mfcc                               |    382296064
# analysis.lowlevel__barkbands                          |    517488640
# analysis.lowlevel__erbbands                           |    628678656
# analysis.lowlevel__melbands                           |    628678656
# analysis.lowlevel__melbands128                        |   1487192064
#
# So we have to ignore some keys and not store them in the database
# in order to save some space


keys_to_ignore = {'lowlevel.loudness_ebu128.short_term',
                  'lowlevel.loudness_ebu128.momentary',
                  'tonal.hpcp_crest',
                  'tonal.chords_strength',
                  'tonal.hpcp_entropy',
                  'lowlevel.spectral_rolloff',
                  'lowlevel.spectral_rms',
                  'lowlevel.spectral_energyband_middle_high',
                  'lowlevel.spectral_strongpeak',
                  'lowlevel.spectral_energyband_middle_low',
                  'lowlevel.spectral_entropy',
                  'lowlevel.spectral_flux',
                  'lowlevel.spectral_kurtosis',
                  'lowlevel.spectral_skewness',
                  'lowlevel.spectral_spread',
                  'lowlevel.zerocrossingrate',
                  'lowlevel.spectral_energyband_low',
                  'lowlevel.melbands_crest',
                  'lowlevel.melbands_flatness_db',
                  'lowlevel.melbands_kurtosis',
                  'lowlevel.erbbands_spread',
                  'lowlevel.hfc',
                  'lowlevel.barkbands_crest',
                  'lowlevel.barkbands_flatness_db',
                  'lowlevel.barkbands_kurtosis',
                  'lowlevel.spectral_decrease',
                  'lowlevel.spectral_energyband_high',
                  'lowlevel.spectral_energy',
                  'lowlevel.barkbands_skewness',
                  'lowlevel.spectral_complexity',
                  'lowlevel.spectral_centroid',
                  'lowlevel.silence_rate_60dB',
                  'lowlevel.silence_rate_30dB',
                  'lowlevel.silence_rate_20dB',
                  'lowlevel.pitch_salience',
                  'lowlevel.melbands_spread',
                  'lowlevel.melbands_skewness',
                  'lowlevel.erbbands_skewness',
                  'lowlevel.erbbands_kurtosis',
                  'lowlevel.erbbands_flatness_db',
                  'lowlevel.erbbands_crest',
                  'lowlevel.dissonance',
                  'lowlevel.barkbands_spread',
                  'tonal.hpcp',
                  'lowlevel.spectral_contrast_coeffs',
                  'lowlevel.spectral_contrast_valleys',
                  'lowlevel.gfcc',
                  'lowlevel.mfcc',
                  'lowlevel.barkbands',
                  'lowlevel.erbbands',
                  'lowlevel.melbands',
                  'lowlevel.melbands128'}


essentia_allowed_exts = ['.wav', '.mp3', '.flac', '.ogg']


class SongAnalysis:
    def __init__(self, path):
        """Create an Analyzer object."""
        self.path = path
        self.stats = None
        self.frames = None

    @staticmethod
    def analyze(path):
        analysis = SongAnalysis(path)

        dir = '/usr/share/essentia-extractor-svm_models/'
        history_files = [os.path.join(dir, x)
                         for x in os.listdir(dir) if x.endswith('.history')]

        extractor = MusicExtractor(highlevel=history_files,
                                   lowlevelSilentFrames='keep',
                                   tonalSilentFrames='keep')
        if any(path.lower().endswith(x) for x in essentia_allowed_exts):
            analysis.stats, analysis.frames = extractor(path)
        else:
            with (tempfile.NamedTemporaryFile(mode='w',
                  prefix='bard_raw_audio', suffix='.wav')) as raw:
                args = ['ffmpeg', '-y', '-i', path, '-ac', '2', raw.name]
                subprocess.run(args, capture_output=True)
                analysis.stats, analysis.frames = extractor(raw.name)

        return analysis


class AnalysisImporter:
    def __init__(self, song_id, song_analysis):
        """Create an AnalysisImporter obj. that imports a SongAnalysis obj."""
        self.song_id = song_id
        self.stats = song_analysis.stats
        self.frames = song_analysis.frames

    def import_keys_with_stats(self):
        for key in keys_with_stats:
            if key in keys_to_ignore:
                continue
            t = table('analysis.' + key.replace('.', '__').lower() + '_stats')
            vars = {db_var: self.stats[key + '.' + st_var]
                    for st_var, db_var in stat_variables.items()}
            vars['song_id'] = self.song_id
            self.connection.execute(t.insert().values(**vars))

    def import_keys_with_lists_stats(self):
        for key in keys_with_lists_stats:
            if key in keys_to_ignore:
                continue

            for pos in range(len(self.stats[key + '.var'])):
                t = table('analysis.' + key.replace('.', '__').lower() +
                          '_stats')
                vars = {db_var: self.stats[key + '.' + st_var][pos].item()
                        for st_var, db_var in stat_variables.items()}
                vars['song_id'] = self.song_id
                vars['pos'] = pos
                self.connection.execute(t.insert().values(**vars))

    def import_keys_with_lists(self):
        for key in keys_with_lists:
            if key in keys_to_ignore:
                continue
            t = table('analysis.' + key.replace('.', '__').lower())
            vars = {'values': list(x.item() for x in self.stats[key]),
                    'song_id': self.song_id}
            self.connection.execute(t.insert().values(**vars))

    def import_fkeys_with_lists(self):
        for key in fkeys_with_lists:
            if key in keys_to_ignore:
                continue
            tablename = 'analysis.' + key.replace('.', '__').lower()
            sql = text(f'INSERT INTO {tablename} (song_id, pos, value) '
                       f'VALUES ({self.song_id}, :pos, :value)')
            vars = [{'pos': pos, 'value': val.item()}
                    for pos, val in enumerate(self.frames[key])]

            self.connection.execute(sql, vars)

    def import_fkeys_with_lists_of_lists(self):
        for key in fkeys_with_lists_of_lists:
            if key[0] in keys_to_ignore:
                continue
            tablename = 'analysis.' + key[0].replace('.', '__').lower()
            vars = [{'pos': pos, 'values': list(x.item() for x in val)}
                    for pos, val in enumerate(self.frames[key[0]])]
            sql = text(f'INSERT INTO {tablename} (song_id, pos, values) '
                       f'VALUES ({self.song_id}, :pos, :values)')

            self.connection.execute(sql, vars)

    def import_conversion_dict(self):
        tables = set(x[0] for x in conversion_dict.values())
        for tablename in tables:
            t = table('analysis.' + tablename.lower())
            vars = {v[1]: self.stats[k]
                    for k, v in conversion_dict.items() if v[0] == tablename}
            vars['song_id'] = self.song_id
            self.connection.execute(t.insert().values(**vars))

    def import_analysis(self, *, connection=None):
        if not self.stats or not self.frames:
            raise ValueError("There's no analysis to import")

        self.connection = connection or MusicDatabase.getCursor()

        if self.has_analysis_for_song_id(self.song_id,
                                         connection=self.connection):
            print(f'Removing existing data for song {self.song_id}...')
            self.remove_analysis_for_song_id(self.song_id,
                                             connection=self.connection)

        self.import_keys_with_stats()
        self.import_keys_with_lists_stats()
        self.import_keys_with_lists()
        self.import_fkeys_with_lists()
        self.import_fkeys_with_lists_of_lists()
        self.import_conversion_dict()

        if not connection:
            self.connection.commit()
            self.connection = None

    def has_analysis_for_song_id(self, song_id, *, connection=None):
        if not connection:
            connection = MusicDatabase.getCursor()
        sql = text('select song_id from analysis.highlevel '
                   f' where song_id = {song_id}')
        result = connection.execute(sql)
        return bool(result.fetchone())

    def remove_analysis_for_song_id(self, song_id, *, connection=None):
        c = connection or MusicDatabase.getCursor()
        tables = list(set(x[0] for x in conversion_dict.values()))
        tables += [key.replace('.', '__').lower() + '_stats'
                   for key in keys_with_stats]
        tables += [key.replace('.', '__').lower() + '_stats'
                   for key in keys_with_lists_stats]
        tables += [key.replace('.', '__').lower()
                   for key in keys_with_lists]
        tables += [key.replace('.', '__').lower()
                   for key in fkeys_with_lists]
        tables += [key[0].replace('.', '__').lower()
                   for key in fkeys_with_lists_of_lists]

        for tablename in tables:
            sql = text(f'DELETE FROM analysis.{tablename} '
                       'WHERE song_id = :song_id')
            c.execute(sql.bindparams(song_id=song_id))

        if not connection:
            c.commit()


class AnalysisDatabase:
    @staticmethod
    def songsWithoutAnalysis(from_song_id=0):
        c = MusicDatabase.getCursor()
        sql = text('SELECT id, path, duration FROM songs, properties '
                   'WHERE NOT EXISTS (SELECT song_id '
                   '                    FROM analysis.highlevel '
                   '                   WHERE song_id = id) '
                   '  AND songs.id = properties.song_id '
                   f'  AND songs.id >= {from_song_id} '
                   'ORDER BY id')
        result = c.execute(sql)
        return [(x[0], x[1], x[2]) for x in result.fetchall()]

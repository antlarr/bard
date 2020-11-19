CREATE SCHEMA analysis;
CREATE TABLE analysis.rhythm__beats_loudness_stats (
        song_id INTEGER PRIMARY KEY,
        mean REAL,
        minimum REAL,
        maximum REAL,
        stdev REAL,
        var REAL,
        median REAL,
        dmean REAL,
        dmean2 REAL,
        dvar REAL,
        dvar2 REAL,
        FOREIGN KEY(song_id)
            REFERENCES public.songs(id) ON DELETE CASCADE
);
CREATE TABLE analysis.lowlevel__gfcc__mean (
        song_id INTEGER PRIMARY KEY,
        values REAL[],
        FOREIGN KEY(song_id)
            REFERENCES public.songs(id) ON DELETE CASCADE
);
CREATE TABLE analysis.lowlevel__mfcc__mean (
        song_id INTEGER PRIMARY KEY,
        values REAL[],
        FOREIGN KEY(song_id)
            REFERENCES public.songs(id) ON DELETE CASCADE
);
CREATE TABLE analysis.rhythm__beats_loudness (
        song_id INTEGER, pos INTEGER,
        value REAL,
        UNIQUE(song_id, pos),
        FOREIGN KEY(song_id)
            REFERENCES public.songs(id) ON DELETE CASCADE
);
CREATE INDEX rhythm__beats_loudness_song_id_idx
                  ON analysis.rhythm__beats_loudness (song_id);

CREATE TABLE analysis.rhythm__beats_position (
        song_id INTEGER, pos INTEGER,
        value REAL,
        UNIQUE(song_id, pos),
        FOREIGN KEY(song_id)
            REFERENCES public.songs(id) ON DELETE CASCADE
);
CREATE INDEX rhythm__beats_position_song_id_idx
                  ON analysis.rhythm__beats_position (song_id);

CREATE TABLE analysis.rhythm__bpm_histogram (
        song_id INTEGER, pos INTEGER,
        value REAL,
        UNIQUE(song_id, pos),
        FOREIGN KEY(song_id)
            REFERENCES public.songs(id) ON DELETE CASCADE
);
CREATE INDEX rhythm__bpm_histogram_song_id_idx
                  ON analysis.rhythm__bpm_histogram (song_id);

CREATE TABLE analysis.tonal__chords_histogram (
        song_id INTEGER, pos INTEGER,
        value REAL,
        UNIQUE(song_id, pos),
        FOREIGN KEY(song_id)
            REFERENCES public.songs(id) ON DELETE CASCADE
);
CREATE INDEX tonal__chords_histogram_song_id_idx
                  ON analysis.tonal__chords_histogram (song_id);

CREATE TABLE analysis.tonal__thpcp (
        song_id INTEGER, pos INTEGER,
        value REAL,
        UNIQUE(song_id, pos),
        FOREIGN KEY(song_id)
            REFERENCES public.songs(id) ON DELETE CASCADE
);
CREATE INDEX tonal__thpcp_song_id_idx
                  ON analysis.tonal__thpcp (song_id);

CREATE TABLE analysis.highlevel (
   song_id INTEGER PRIMARY KEY,
   danceable REAL,
   gender_female REAL,
   acoustic REAL,
   aggressive REAL,
   electronic REAL,
   happy REAL,
   party REAL,
   relaxed REAL,
   sad REAL,
   bright REAL,
   atonal REAL,
   instrumental REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.lowlevel (
   song_id INTEGER PRIMARY KEY,
   average_loudness REAL,
   dynamic_complexity REAL,
   loudness_ebu128_integrated REAL,
   loudness_ebu128_loudness_range REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.version (
   song_id INTEGER PRIMARY KEY,
   essentia TEXT,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.rhythm (
   song_id INTEGER PRIMARY KEY,
   beats_count REAL,
   bpm REAL,
   bpm_histogram_first_peak_bpm REAL,
   bpm_histogram_first_peak_weight REAL,
   bpm_histogram_second_peak_bpm REAL,
   bpm_histogram_second_peak_spread REAL,
   bpm_histogram_second_peak_weight REAL,
   danceability REAL,
   onset_rate REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.tonal (
   song_id INTEGER PRIMARY KEY,
   chords_changes_rate REAL,
   chords_key TEXT,
   chords_number_rate REAL,
   chords_scale TEXT,
   key_edma_key TEXT,
   key_edma_scale TEXT,
   key_edma_strength REAL,
   key_krumhansl_key TEXT,
   key_krumhansl_scale TEXT,
   key_krumhansl_strength REAL,
   key_temperley_key TEXT,
   key_temperley_scale TEXT,
   key_temperley_strength REAL,
   tuning_diatonic_strength REAL,
   tuning_equal_tempered_deviation REAL,
   tuning_frequency REAL,
   tuning_nontempered_energy_ratio REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.highlevel__genre_dortmund (
   song_id INTEGER PRIMARY KEY,
   value TEXT,
   probability REAL,
   alternative REAL,
   blues REAL,
   electronic REAL,
   folkcountry REAL,
   funksoulrnb REAL,
   jazz REAL,
   pop REAL,
   raphiphop REAL,
   rock REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.highlevel__genre_electronic (
   song_id INTEGER PRIMARY KEY,
   value TEXT,
   probability REAL,
   ambient REAL,
   dnb REAL,
   house REAL,
   techno REAL,
   trance REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.highlevel__genre_rosamerica (
   song_id INTEGER PRIMARY KEY,
   value TEXT,
   probability REAL,
   cla REAL,
   dan REAL,
   hip REAL,
   jaz REAL,
   pop REAL,
   rhy REAL,
   roc REAL,
   spe REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.highlevel__genre_tzanetakis (
   song_id INTEGER PRIMARY KEY,
   value TEXT,
   probability REAL,
   blu REAL,
   cla REAL,
   cou REAL,
   dis REAL,
   hip REAL,
   jaz REAL,
   met REAL,
   pop REAL,
   reg REAL,
   roc REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.highlevel__ismir04_rhythm (
   song_id INTEGER PRIMARY KEY,
   value TEXT,
   probability REAL,
   chachacha REAL,
   jive REAL,
   quickstep REAL,
   rumba_american REAL,
   rumba_international REAL,
   rumba_misc REAL,
   samba REAL,
   tango REAL,
   viennesewaltz REAL,
   waltz REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);

CREATE TABLE analysis.highlevel__moods_mirex (
   song_id INTEGER PRIMARY KEY,
   value TEXT,
   probability REAL,
   cluster1 REAL,
   cluster2 REAL,
   cluster3 REAL,
   cluster4 REAL,
   cluster5 REAL,
   FOREIGN KEY(song_id)
              REFERENCES public.songs(id) ON DELETE CASCADE
);


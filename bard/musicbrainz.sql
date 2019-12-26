CREATE SCHEMA musicbrainz;
SET search_path TO musicbrainz,public;

-- Enum types:

CREATE TABLE musicbrainz.enum_area_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_artist_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_artist_alias_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_event_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_release_group_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_release_group_secondary_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_release_status_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_language_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_gender_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_label_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_medium_format_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_work_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_place_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_series_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

CREATE TABLE musicbrainz.enum_instrument_type_values (
       id_value SERIAL PRIMARY KEY,
       name TEXT
);

-- MusicBrainz schema (lite):

CREATE TABLE musicbrainz.area (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,
       name TEXT,
       area_type INTEGER,  -- Country, Subdivision, County, City...

       FOREIGN KEY(area_type)
         REFERENCES enum_area_type_values(id_value)
);

CREATE INDEX ON musicbrainz.area (mbid);

CREATE OR REPLACE TABLE musicbrainz.event (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,

       name TEXT,
       event_type INTEGER,
       begin_date_year INTEGER,
       begin_date_month INTEGER,
       begin_date_day INTEGER,
       end_date_year INTEGER,
       end_date_month INTEGER,
       end_date_day INTEGER,
       setlist TEXT,
       comment TEXT

       FOREIGN KEY(event_type)
         REFERENCES enum_event_type_values(id_value)
);

CREATE TABLE musicbrainz.place (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,

       name TEXT,
       disambiguation TEXT,
       place_type INTEGER,
       area_id INTEGER,

       FOREIGN KEY(place_type)
         REFERENCES enum_place_type_values(id_value),
       FOREIGN KEY(area_id)
         REFERENCES area(id)
);

CREATE TABLE musicbrainz.label (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,

       name TEXT,
       disambiguation TEXT
       label_type          INTEGER,
       area_id             INTEGER,
       begin_date_year     SMALLINT,
       begin_date_month    SMALLINT,
       begin_date_day      SMALLINT,
       end_date_year       SMALLINT,
       end_date_month      SMALLINT,
       end_date_day        SMALLINT,

       FOREIGN KEY(label_type)
         REFERENCES enum_label_type_values(id_value),
       FOREIGN KEY(area_id)
         REFERENCES area(id)
);
CREATE INDEX ON musicbrainz.label (mbid);

CREATE TABLE musicbrainz.artist (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,
       name TEXT,
       disambiguation TEXT,
       sort_name TEXT,
       artist_type INTEGER,  -- Person, group, orchestra...
       gender INTEGER,
       area_id INTEGER,

       FOREIGN KEY(artist_type)
         REFERENCES enum_artist_type_values(id_value),
       FOREIGN KEY(gender)
         REFERENCES enum_gender_values(id_value),
       FOREIGN KEY(area_id)
         REFERENCES musicbrainz.area(id)
);

CREATE INDEX ON musicbrainz.artist (mbid);

CREATE TABLE musicbrainz.artist_credit (
        id SERIAL PRIMARY KEY,
        name TEXT
);

CREATE TABLE musicbrainz.artist_credit_name (
       artist_credit_id INTEGER,
       artist_id INTEGER,

       position SMALLINT,
       name TEXT,
       join_phrase TEXT DEFAULT '',

       FOREIGN KEY(artist_credit_id)
         REFERENCES artist_credit(id),
       FOREIGN KEY(artist_id)
         REFERENCES artist(id)
);

CREATE INDEX ON musicbrainz.artist_credit_name (artist_credit_id);
CREATE INDEX ON musicbrainz.artist_credit_name (artist_id);

CREATE TABLE musicbrainz.release_group (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,
       name TEXT,
       disambiguation TEXT,
       release_group_type INTEGER,
       artist_credit_id INTEGER,

       FOREIGN KEY(release_group_type)
         REFERENCES enum_release_group_type_values(id_value),
       FOREIGN KEY(artist_credit_id)
         REFERENCES artist_credit(id)
);

CREATE INDEX ON musicbrainz.release_group (mbid);
CREATE INDEX ON musicbrainz.release_group (artist_credit_id);

CREATE TABLE musicbrainz.release_group_secondary_type_join (
       release_group_id INTEGER PRIMARY KEY,
       secondary_type INTEGER NOT NULL,

       FOREIGN KEY(release_group_id)
         REFERENCES release_group(id),
       FOREIGN KEY(secondary_type)
         REFERENCES enum_release_group_secondary_type_values(id_value)
);

CREATE TABLE musicbrainz.release (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,
       name TEXT,
       disambiguation TEXT,
       artist_credit_id INTEGER,
       release_group_id INTEGER,
       release_status INTEGER,
       language INTEGER,

       barcode TEXT,

       FOREIGN KEY(release_status)
         REFERENCES enum_release_status_values(id_value),
       FOREIGN KEY(language)
         REFERENCES enum_language_values(id_value),
       FOREIGN KEY(artist_credit_id)
         REFERENCES artist_credit(id),
       FOREIGN KEY(release_group_id)
         REFERENCES release_group(id)
);

CREATE INDEX ON musicbrainz.release (mbid);
CREATE INDEX ON musicbrainz.release (release_group_id);
CREATE INDEX ON musicbrainz.release (artist_credit_id);

CREATE TABLE musicbrainz.recording (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,
       name TEXT,
       disambiguation TEXT,
       artist_credit_id INTEGER,

       FOREIGN KEY(artist_credit_id)
         REFERENCES artist_credit(id)
);

CREATE INDEX ON musicbrainz.recording (mbid);

CREATE TABLE musicbrainz.medium (
       id SERIAL PRIMARY KEY,
       release_id INTEGER,
       position INTEGER,
       format   INTEGER,
       name     TEXT NOT NULL DEFAULT '',

       FOREIGN KEY(format)
         REFERENCES enum_medium_format_values(id_value)
);

CREATE INDEX ON musicbrainz.medium (release_id);

CREATE TABLE musicbrainz.track (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,
       recording_id INTEGER,
       medium_id    INTEGER,

       position    INTEGER,
       number_text TEXT,
       name        TEXT,
       artist_credit_id INTEGER,
       length        INTEGER,
       is_data_track BOOLEAN DEFAULT FALSE,

       FOREIGN KEY(recording_id)
         REFERENCES recording(id),
       FOREIGN KEY(medium_id)
         REFERENCES medium(id),
       FOREIGN KEY(artist_credit_id)
         REFERENCES artist_credit(id)
);

CREATE INDEX ON musicbrainz.track (mbid);
CREATE INDEX ON musicbrainz.track (recording_id);
CREATE INDEX ON musicbrainz.track (medium_id);

CREATE TABLE musicbrainz.work (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,

       name TEXT,
       disambiguation TEXT,
       work_type INTEGER,

       FOREIGN KEY(work_type)
         REFERENCES enum_work_type_values(id_value)
);
CREATE INDEX ON musicbrainz.work (mbid);

CREATE TABLE musicbrainz.series (
       id SERIAL PRIMARY KEY,
       mbid TEXT UNIQUE,

       name TEXT,
       disambiguation TEXT,
       series_type INTEGER,  -- release group, release, recording, work ...

       FOREIGN KEY(series_type)
         REFERENCES enum_series_type_values(id_value)

);

CREATE TABLE musicbrainz.instrument (
       id SERIAL PRIMARY KEY,
       mbid uuid,

       name TEXT,
       type INTEGER,

       FOREIGN KEY(type)
         REFERENCES enum_instrument_type_values(id_value)
);

CREATE TABLE musicbrainz.release_country (
       release_id    INTEGER NOT NULL,
       country_id    INTEGER NOT NULL,
       date_year  SMALLINT,
       date_month SMALLINT,
       date_day   SMALLINT,

       PRIMARY KEY(release_id, country_id),

       FOREIGN KEY(release_id)
         REFERENCES musicbrainz.release(id),
       FOREIGN KEY(country_id)
         REFERENCES musicbrainz.area(id)
);

CREATE INDEX ON musicbrainz.release_country(release_id);

CREATE TABLE musicbrainz.release_label (
       id                  INTEGER PRIMARY KEY,
       release_id          INTEGER NOT NULL,
       label_id            INTEGER,
       catalog_number      VARCHAR(255),

       FOREIGN KEY(release_id)
         REFERENCES musicbrainz.release(id),
       FOREIGN KEY(label_id)
         REFERENCES musicbrainz.label(id)
);

CREATE INDEX ON musicbrainz.release_label(release_id);


CREATE TABLE musicbrainz.link_type (
       id SERIAL PRIMARY KEY,
       mbid UUID NOT NULL,
       name TEXT,

       entity_type0 TEXT,
       entity_type1 TEXT,

       description TEXT,
       link_phrase TEXT,
       reverse_link_phrase TEXT,
       long_link_phrase TEXT,
       entity0_cardinality INTEGER,
       entity1_cardinality INTEGER
);

CREATE INDEX ON musicbrainz.link_type(mbid);
CREATE INDEX ON musicbrainz.link_type(name);

CREATE TABLE musicbrainz.link (
    id SERIAL PRIMARY KEY,
    link_type_id INTEGER NOT NULL,

    begin_date_year     SMALLINT,
    begin_date_month    SMALLINT,
    begin_date_day      SMALLINT,
    end_date_year       SMALLINT,
    end_date_month      SMALLINT,
    end_date_day        SMALLINT,

    FOREIGN KEY(link_type_id)
      REFERENCES link_type(id)
);

CREATE TABLE musicbrainz.link_attribute_type (
       id SERIAL PRIMARY KEY,
       parent INTEGER, -- references link_attribute_type.id
       root INTEGER NOT NULL, -- references link_attribute_type.id
       child_order INTEGER NOT NULL DEFAULT 0,
       mbid  UUID NOT NULL,
       name TEXT,
       description TEXT,

       FOREIGN KEY(parent)
         REFERENCES link_attribute_type(id),
       FOREIGN KEY(root)
         REFERENCES link_attribute_type(id)
);

CREATE TABLE musicbrainz.link_attribute (
       link_id INTEGER NOT NULL,
       link_attribute_type_id INTEGER NOT NULL,

       PRIMARY KEY (link_id, link_attribute_type_id),
       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(link_attribute_type_id)
         REFERENCES link_attribute_type(id)
);

CREATE TABLE musicbrainz.link_attribute_credit (
  link_id INT NOT NULL,
  link_attribute_type_id INT NOT NULL,
  credited_as TEXT NOT NULL,

  PRIMARY KEY(link_id, link_attribute_type_id),
  FOREIGN KEY(link_id)
    REFERENCES link(id),
  FOREIGN KEY(link_attribute_type_id)
    REFERENCES link_attribute_type(id)
);


-- Aliases

CREATE TABLE musicbrainz.artist_alias (
       id SERIAL PRIMARY KEY,
       artist_id INTEGER,

       name TEXT,
       sort_name TEXT,
       locale TEXT,
       artist_alias_type INTEGER,
       primary_for_locale BOOLEAN NOT NULL DEFAULT false,

       FOREIGN KEY(artist_id)
         REFERENCES artist(id),
       FOREIGN KEY(artist_alias_type)
         REFERENCES enum_artist_alias_type_values(id_value)
);

CREATE INDEX ON musicbrainz.artist_alias(artist_id);

-- Relations
-- Do not edit this section. It's generated automatically by the generate_l_tables.py script

CREATE TABLE musicbrainz.l_area_area (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES area(id)
);

CREATE TABLE musicbrainz.l_area_artist (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES artist(id)
);

CREATE TABLE musicbrainz.l_area_event (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES event(id)
);

CREATE TABLE musicbrainz.l_area_instrument (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES instrument(id)
);

CREATE TABLE musicbrainz.l_area_label (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES label(id)
);

CREATE TABLE musicbrainz.l_area_place (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES place(id)
);

CREATE TABLE musicbrainz.l_area_recording (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES recording(id)
);

CREATE TABLE musicbrainz.l_area_release (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES release(id)
);

CREATE TABLE musicbrainz.l_area_release_group (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES release_group(id)
);

CREATE TABLE musicbrainz.l_area_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_area_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES area(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_artist_artist (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES artist(id)
);

CREATE TABLE musicbrainz.l_artist_event (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES event(id)
);

CREATE TABLE musicbrainz.l_artist_instrument (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES instrument(id)
);

CREATE TABLE musicbrainz.l_artist_label (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES label(id)
);

CREATE TABLE musicbrainz.l_artist_place (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES place(id)
);

CREATE TABLE musicbrainz.l_artist_recording (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES recording(id)
);

CREATE TABLE musicbrainz.l_artist_release (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES release(id)
);

CREATE TABLE musicbrainz.l_artist_release_group (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES release_group(id)
);

CREATE TABLE musicbrainz.l_artist_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_artist_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES artist(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_event_event (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES event(id),
       FOREIGN KEY(entity1)
         REFERENCES event(id)
);

CREATE TABLE musicbrainz.l_event_instrument (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES event(id),
       FOREIGN KEY(entity1)
         REFERENCES instrument(id)
);

CREATE TABLE musicbrainz.l_event_label (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES event(id),
       FOREIGN KEY(entity1)
         REFERENCES label(id)
);

CREATE TABLE musicbrainz.l_event_place (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES event(id),
       FOREIGN KEY(entity1)
         REFERENCES place(id)
);

CREATE TABLE musicbrainz.l_event_recording (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES event(id),
       FOREIGN KEY(entity1)
         REFERENCES recording(id)
);

CREATE TABLE musicbrainz.l_event_release (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES event(id),
       FOREIGN KEY(entity1)
         REFERENCES release(id)
);

CREATE TABLE musicbrainz.l_event_release_group (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES event(id),
       FOREIGN KEY(entity1)
         REFERENCES release_group(id)
);

CREATE TABLE musicbrainz.l_event_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES event(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_event_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES event(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_instrument_instrument (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES instrument(id),
       FOREIGN KEY(entity1)
         REFERENCES instrument(id)
);

CREATE TABLE musicbrainz.l_instrument_label (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES instrument(id),
       FOREIGN KEY(entity1)
         REFERENCES label(id)
);

CREATE TABLE musicbrainz.l_instrument_place (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES instrument(id),
       FOREIGN KEY(entity1)
         REFERENCES place(id)
);

CREATE TABLE musicbrainz.l_instrument_recording (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES instrument(id),
       FOREIGN KEY(entity1)
         REFERENCES recording(id)
);

CREATE TABLE musicbrainz.l_instrument_release (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES instrument(id),
       FOREIGN KEY(entity1)
         REFERENCES release(id)
);

CREATE TABLE musicbrainz.l_instrument_release_group (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES instrument(id),
       FOREIGN KEY(entity1)
         REFERENCES release_group(id)
);

CREATE TABLE musicbrainz.l_instrument_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES instrument(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_instrument_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES instrument(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_label_label (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES label(id),
       FOREIGN KEY(entity1)
         REFERENCES label(id)
);

CREATE TABLE musicbrainz.l_label_place (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES label(id),
       FOREIGN KEY(entity1)
         REFERENCES place(id)
);

CREATE TABLE musicbrainz.l_label_recording (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES label(id),
       FOREIGN KEY(entity1)
         REFERENCES recording(id)
);

CREATE TABLE musicbrainz.l_label_release (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES label(id),
       FOREIGN KEY(entity1)
         REFERENCES release(id)
);

CREATE TABLE musicbrainz.l_label_release_group (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES label(id),
       FOREIGN KEY(entity1)
         REFERENCES release_group(id)
);

CREATE TABLE musicbrainz.l_label_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES label(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_label_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES label(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_place_place (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES place(id),
       FOREIGN KEY(entity1)
         REFERENCES place(id)
);

CREATE TABLE musicbrainz.l_place_recording (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES place(id),
       FOREIGN KEY(entity1)
         REFERENCES recording(id)
);

CREATE TABLE musicbrainz.l_place_release (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES place(id),
       FOREIGN KEY(entity1)
         REFERENCES release(id)
);

CREATE TABLE musicbrainz.l_place_release_group (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES place(id),
       FOREIGN KEY(entity1)
         REFERENCES release_group(id)
);

CREATE TABLE musicbrainz.l_place_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES place(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_place_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES place(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_recording_recording (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES recording(id),
       FOREIGN KEY(entity1)
         REFERENCES recording(id)
);

CREATE TABLE musicbrainz.l_recording_release (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES recording(id),
       FOREIGN KEY(entity1)
         REFERENCES release(id)
);

CREATE TABLE musicbrainz.l_recording_release_group (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES recording(id),
       FOREIGN KEY(entity1)
         REFERENCES release_group(id)
);

CREATE TABLE musicbrainz.l_recording_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES recording(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_recording_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES recording(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_release_release (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES release(id),
       FOREIGN KEY(entity1)
         REFERENCES release(id)
);

CREATE TABLE musicbrainz.l_release_release_group (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES release(id),
       FOREIGN KEY(entity1)
         REFERENCES release_group(id)
);

CREATE TABLE musicbrainz.l_release_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES release(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_release_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES release(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_release_group_release_group (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES release_group(id),
       FOREIGN KEY(entity1)
         REFERENCES release_group(id)
);

CREATE TABLE musicbrainz.l_release_group_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES release_group(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_release_group_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES release_group(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_series_series (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES series(id),
       FOREIGN KEY(entity1)
         REFERENCES series(id)
);

CREATE TABLE musicbrainz.l_series_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES series(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);

CREATE TABLE musicbrainz.l_work_work (
       id SERIAL PRIMARY KEY,
       link_id INTEGER,
       entity0 INTEGER,
       entity1 INTEGER,
       link_order INTEGER,
       entity0_credit TEXT,
       entity1_credit TEXT,

       FOREIGN KEY(link_id)
         REFERENCES link(id),
       FOREIGN KEY(entity0)
         REFERENCES work(id),
       FOREIGN KEY(entity1)
         REFERENCES work(id)
);


-- This table doesn't come from MB. To fill it with data,
-- run "bard cache-mb-data"
CREATE TABLE artists_mb (
       id INTEGER PRIMARY KEY,

       locale_name TEXT,
       locale_sort_name TEXT,
       locale TEXT,
       artist_alias_type INTEGER,

       image_path TEXT,

       FOREIGN KEY(id)
          REFERENCES musicbrainz.artist(id)
);


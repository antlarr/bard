entities = ['area', 'artist', 'event', 'instrument', 'label', 'place',
            'recording', 'release', 'release_group', 'series', 'work']
remaining_entities = entities[:]
for entity0 in entities:
    for entity1 in remaining_entities:
        cmd = f'''CREATE TABLE l_{entity0}_{entity1} (
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
         REFERENCES {entity0}(id),
       FOREIGN KEY(entity1)
         REFERENCES {entity1}(id)
);
'''
        print(cmd)
    remaining_entities.remove(entity0)

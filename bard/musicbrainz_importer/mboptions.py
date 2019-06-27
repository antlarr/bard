class MBOptions(dict):
    def forbid_table(self, tablename):
        try:
            self['tables_to_not_follow'].add(tablename)
        except KeyError:
            self['tables_to_not_follow'] = set()
            self['tables_to_not_follow'].add(tablename)

    def should_follow_table(self, tablename):
        try:
            return tablename not in self['tables_to_not_follow']
        except KeyError:
            return True

    def set_inmediate_flag(self, b=True):
        if b:
            self['inmediate'] = True
        else:
            try:
                del self['inmediate']
            except KeyError:
                pass

    def has_inmediate_flag(self):
        try:
            return self['inmediate']
        except KeyError:
            return True

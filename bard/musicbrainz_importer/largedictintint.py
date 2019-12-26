import bisect
from array import array


class LargeDictOfIntToInt:
    def __init__(self):
        self.key_array = array('L', [])
        self.val_array = array('L', [])

    def __setitem__(self, k, v):
        pos = bisect.bisect_left(self.key_array, k)
        self.key_array.insert(pos, k)
        self.val_array.insert(pos, v)

    def __getitem__(self, k):
        pos = bisect.bisect_left(self.key_array, k)
        if pos >= len(self.key_array) or self.key_array[pos] != k:
            return KeyError(f'Item {k} not found')
        return self.val_array[pos]

    def __contains__(self, k):
        pos = bisect.bisect_left(self.key_array, k)
        return pos < len(self.key_array) and self.key_array[pos] == k

    def __len__(self):
        return len(self.key_array)

    def fromdict(self, dictionary):
        self.key_array = array('L', [])
        self.val_array = array('L', [])

        #print('1', dictionary[1])
        #print('2', dictionary[2])
        keys = sorted(dictionary.keys())
        for x in keys:
            values = dictionary[x]
            self.key_array.extend([x]*len(values))
            self.val_array.extend(values)

        # self.key_array = array('L', keys)
        # self.val_array = array('L', [dictionary[x] for x in keys])
        self.dumpvalues()

    def dumpvalues(self):
        print(len(self.key_array), len(self.val_array))
        print(self.key_array[0:10])
        print(self.val_array[0:10])


    def getallvalues(self, k):
        pos = bisect.bisect_left(self.key_array, k)
        if pos >= len(self.key_array) or self.key_array[pos] != k:
            #raise KeyError(f'Item {k} not found')
            return []
        kv = self.key_array[pos]
        r = []
        while kv == k:
            r.append(self.val_array[pos])
            pos += 1
            kv = self.key_array[pos]

        return r

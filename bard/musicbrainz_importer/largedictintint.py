import bisect
from array import array

class LargeDictOfIntToInt:
    def __init__(self):
        self.key_array = array('L',[])
        self.val_array = array('L',[])

    def __setitem__(self, k, v):
        pos = bisect.bisect_left(self.key_array, k)
        self.key_array.insert(pos, k)
        self.val_array.insert(pos, v)

    def __getitem__(self, k):
        pos = bisect.bisect_left(self.key_array, k)
        if pos >= len(self.key_array) or self.key_array[pos] != k:
            return KeyError(f'Item {k} not found')
        return self.val_array[pos]



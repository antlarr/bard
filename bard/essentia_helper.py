try:
    import essentia
except ModuleNotFoundError:
    essentia = None

if getattr(essentia, 'log', None):
    essentia.log.infoActive = False

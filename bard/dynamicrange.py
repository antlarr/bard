import numpy
try:
    from dr14tmeter.compute_dr14 import compute_dr14
    from dr14tmeter.duration import StructDuration
except ModuleNotFoundError:
    pass

def calculate(audiodata, properties):
    nframes = properties.samples
    channels = properties.channels
    sample_type = "int%d" % (properties.decoded_bytes_per_sample * 8)

    Y = numpy.fromstring(audiodata, dtype=sample_type).reshape(
               nframes, channels)

    if sample_type == 'int16':
        convert_16_bit = numpy.float32(2**15 + 1.0)
        Y = Y / (convert_16_bit)
    elif sample_type == 'int32':
        convert_32_bit = numpy.float32(2**31 + 1.0)
        Y = Y / (convert_32_bit)
    else:
        convert_8_bit = numpy.float32(2**8 + 1.0)
        Y = Y / (convert_8_bit)

    try:
        duration = StructDuration()
    except NameError:
        print('Error: DR14-T.meter python module not found, this is required to calculate Dynamic Range')
        raise

    (dr14, db_peak, db_rms) = compute_dr14(Y, properties.sample_rate)
    return (dr14, db_peak, db_rms)

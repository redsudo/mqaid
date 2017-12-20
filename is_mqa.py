import struct
import sys
import io
import wave
import flac
from pathlib import Path
from bitstring import Bits

MAGIC = Bits('0xbe0498c88')

def twos_complement(n, bits):
    mask = 2 ** (bits - 1)
    return -(n & mask) + (n & ~mask)

def iter_i24_as_i32(data):
    for l, h in struct.iter_unpack('<BH', data):
        yield twos_complement(h << 8 | l, 24) << 8

def iter_i16_as_i32(data):
    for x, in struct.iter_unpack('<h', data):
        yield x << 16

def peek(f, n):
    o = f.tell()
    r = f.read(n)
    f.seek(o)
    return r

def main(path):
        with open(str(path), 'rb') as f:
            magic = peek(f, 4)

            if magic == b'fLaC':
                with flac.BitInputStream(f) as bf:
                    f = io.BytesIO()
                    flac.decode_file(bf, f, seconds=1)
                    f.seek(0)

            with wave.open(f) as wf:
                nchannels, sampwidth, framerate, *_ = wf.getparams()

                if nchannels != 2:
                    raise ValueError('Input must be stereo')

                if sampwidth == 3:
                    iter_data = iter_i24_as_i32
                elif sampwidth == 2:
                    iter_data = iter_i16_as_i32
                else:
                    raise ValueError('Input must be 16- or 24-bit')

                sound_data = wf.readframes(framerate)

        samples = list(iter_data(sound_data))
        streams = (Bits((x ^ y) >> p & 1
            for x, y in zip(samples[::2], samples[1::2]))
            for p in range(16, 24))

        if any(s.find(MAGIC) for s in streams):
            print('\x1b[1;31m MQA syncword present. [{}] \x1b[0m'.format(str(path)))
        else:
            print('\x1b[1;32m Didn\'t find an MQA syncword. [{}] \x1b[0m'.format(path.parts[-1]))

if __name__ == '__main__':
    args = sys.argv[1:]
    flacpaths = []

    for path in args:
        path = Path(path)
        if Path.is_dir(path):
            flacpaths += sorted(Path(path).glob('**/*.flac'))
        elif str(path).endswith('.flac') and path.is_file():
            flacpaths.append(path)

    print('\x1b[1;33m Found {} flac file(s). Decoding now... \x1b[0m'.format(len(flacpaths)))
    for fpath in flacpaths:
        try:
            main(fpath)
        except Exception as ex:
            print(ex)

import binascii
import collections
import enum
import io
import logging
import struct

logger = logging.getLogger(__name__)

# Convenience object for organizing data about a particular sector.
SectorID = collections.namedtuple('SectorID', ['sector_id', 'display', 'offset'])

SECTOR_SHIFT_OFFSET = 30
SECTOR_SHIFT_SIZE = 2
NUM_DIFAT_SECTS_OFFSET = 72
NUM_DIFAT_SECTS_SIZE = 4
FIRST_DIFAT_SECT_OFFSET = 68
FIRST_DIFAT_SECT_SIZE = 4
HEADER_DIFAT_OFFSET = 76
HEADER_DIFAT_SIZE = 436
NUM_FAT_SECTS_OFFSET = 44
NUM_FAT_SECTS_SIZE = 4
FIRST_DIR_SECT_OFFSET = 48
FIRST_DIR_SECT_SIZE = 4


class SectorType(enum.Enum):
    """Enumeration for the special sector types per documentation."""

    DIFSECT = -4
    FATSECT = -3
    ENDOFCHAIN = -2
    FREESECT = -1


def get_sector_id(sector_id_raw, sector_size):
    """Translate the raw bytes to a number for the sector ID data."""
    r_sector = binascii.hexlify(sector_id_raw).upper().decode()
    logger.debug('Raw sector ID: {}'.format(r_sector))

    (sector_id, ) = struct.unpack_from('<l', sector_id_raw)
    logger.debug('Sector ID: {}'.format(sector_id))

    if sector_id < 0:
        offset = None
        display = SectorType(sector_id).name
    else:
        offset = sector_size + sector_id * sector_size
        display = f'0x{offset:X}'
    logger.debug('Offset: {}; Display: {}'.format(offset, display))

    return SectorID(sector_id, display, offset)


def get_sector_data(offset, size, data):
    """Select the data from one sector based on the sector ID."""
    sector_data = data[offset:offset + size]
    sector_hex = binascii.hexlify(sector_data).upper().decode()
    output = ' '.join([sector_hex[i:i + 8] for i in range(0, len(sector_hex), 8)])
    logger.debug('Sector data:\n{}'.format(output))

    return sector_data


def get_count(count_raw):
    """Convert count data to number."""
    (count, ) = struct.unpack_from('<L', count_raw)
    count_hex = binascii.hexlify(count_raw).upper().decode()
    logger.debug('Raw count: {}; Count: {}'.format(count_hex, count))

    return count


def parse_direntry(dir_entry):
    """Parse one directory entry."""
    name = dir_entry[:64]
    logger.debug('Directory entry name: {}'.format(name.decode('utf-16')))
    (name_length, ) = struct.unpack_from('<H', dir_entry[64:66])
    (object_type, ) = struct.unpack_from('<B', dir_entry[66:67])
    (color_flag, ) = struct.unpack_from('<B', dir_entry[67:68])
    (left_sibling, ) = struct.unpack_from('<l', dir_entry[68:72])
    (right_sibling, ) = struct.unpack_from('<l', dir_entry[72:76])
    (child_id, ) = struct.unpack_from('<l', dir_entry[76:80])
    (starting_sector, ) = struct.unpack_from('<L', dir_entry[116:120])
    (stream_size, ) = struct.unpack_from('<Q', dir_entry[120:128])
    record = {'name_decoded': name.decode('utf-16').rstrip('\x00'),
              'name': name,
              'name_length': name_length,
              'object_type': object_type,
              'color_flag': color_flag,
              'left_sibling': left_sibling,
              'right_sibling': right_sibling,
              'child_id': child_id,
              'clsid': dir_entry[80:96],
              'state': dir_entry[96:100],
              'creation_time': dir_entry[100:108],
              'modification_time': dir_entry[108:116],
              'starting_sector': starting_sector,
              'stream_size': stream_size}

    return record


def run(target):
    """Parse one compound file."""
    if not target.exists():
        raise FileNotFoundError('Target file does not exist.')

    with open(target, 'rb') as fh:
        data = fh.read()
    logger.debug('Length of data from file: {}'.format(len(data)))

    magic = data[:8]
    if magic != b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        raise RuntimeError('Not a compound file.')

    sector_shift_raw = data[SECTOR_SHIFT_OFFSET:SECTOR_SHIFT_OFFSET + SECTOR_SHIFT_SIZE]
    sector_shift_hex = binascii.hexlify(sector_shift_raw).upper().decode()
    logger.debug('Hex sector shift: {}'.format(sector_shift_hex))
    (sector_shift, ) = struct.unpack_from('<H', sector_shift_raw)
    logger.debug('Numeric sector shift: {}'.format(sector_shift))

    sector_size = 2 ** sector_shift
    logger.debug('Sector size: {}'.format(sector_size))

    count_raw = data[NUM_DIFAT_SECTS_OFFSET:NUM_DIFAT_SECTS_OFFSET + NUM_DIFAT_SECTS_SIZE]
    difat_sector_count = get_count(count_raw)

    sector_id_raw = data[FIRST_DIFAT_SECT_OFFSET:FIRST_DIFAT_SECT_OFFSET + FIRST_DIFAT_SECT_SIZE]
    difat_start = get_sector_id(sector_id_raw, sector_size)

    output = io.BytesIO()
    header_difat = get_sector_data(HEADER_DIFAT_OFFSET, HEADER_DIFAT_SIZE, data)
    output.write(header_difat)

    if difat_sector_count and difat_start.offset:
        difat_next = get_sector_data(difat_start.offset, sector_size, data)

        output.append(difat_next[:-4])

        for i in range(1, difat_sector_count):
            last_bytes = difat_next[-4:]
            logger.debug('Sector last bytes: {}'.format(binascii.hexlify(last_bytes).upper().decode()))
            sector_id = get_sector_id(last_bytes, sector_size)
            logger.debug('Next sector ID: {}'.format(sector_id))
            difat_next = get_sector_data(sector_id.offset, sector_size, data)
            output.append(difat_next[:-4])

    sector_chain_difat = list()
    output.seek(0)
    difat = output.read()
    output.close()

    for uint32 in [difat[i:i + 4] for i in range(0, len(difat), 4)]:
        sector_id = get_sector_id(uint32, sector_size)
        if sector_id.sector_id < 0:
            break
        sector_chain_difat.append(sector_id)

    logger.debug('Last sector ID in DIFAT chain: {}'.format(sector_chain_difat[-1:]))

    fat_sector_count = get_count(data[NUM_FAT_SECTS_OFFSET:NUM_FAT_SECTS_OFFSET + NUM_FAT_SECTS_SIZE])
    logger.debug('Count of fat sectors: {}'.format(fat_sector_count))

    logger.debug('Length of DIFAT chain: {}'.format(len(sector_chain_difat)))

    if len(sector_chain_difat) != fat_sector_count:
        raise RuntimeError('Number of FAT sectors from DIFAT length does not match count in header.')

    logger.debug('First sector ID in DIFAT chain: {}'.format(sector_chain_difat[0]))

    cache = io.BytesIO()

    for sector_id in sector_chain_difat:
        sector_data = get_sector_data(sector_id.offset, sector_size, data)
        cache.write(sector_data)

    cache.seek(0)

    sector_chain_fat = list()

    fat_entry = '1'

    while len(fat_entry) > 0:
        fat_entry = cache.read(4)
        if fat_entry:
            sector_id = get_sector_id(fat_entry, sector_size)
            sector_chain_fat.append(sector_id)

    cache.close()

    logger.debug('Length of FAT chain: {}'.format(len(sector_chain_fat)))
    logger.debug('Last sector ID in FAT chain: {}'.format(sector_chain_fat[-1:]))

    dirsect = get_sector_id(data[FIRST_DIR_SECT_OFFSET:FIRST_DIR_SECT_OFFSET + FIRST_DIR_SECT_SIZE], sector_size)
    logger.debug('First directory sector ID: {}; Display: {}'.format(dirsect.sector_id, dirsect.display))

    cache = io.BytesIO()

    cache.write(get_sector_data(dirsect.offset, sector_size, data))
    sector_id = dirsect.sector_id
    logger.debug('Sector ID object: {}'.format(dirsect))

    while sector_id >= 0:
        dirsect = sector_chain_fat[dirsect.sector_id]
        logger.debug('Sector ID object: {}'.format(dirsect))

        if dirsect.sector_id >= 0:
            cache.write(get_sector_data(dirsect.offset, sector_size, data))
        sector_id = dirsect.sector_id

    cache.seek(0)

    directory = list()

    dir_entry = '1'

    while len(dir_entry) > 0:
        dir_entry = cache.read(128)
        if dir_entry:
            directory.append(parse_direntry(dir_entry))

    cache.close()

    for entry in directory:
        if entry['name_decoded'] in ['Book', 'Workbook']:
            logger.info('File is Excel')
            break

    return directory

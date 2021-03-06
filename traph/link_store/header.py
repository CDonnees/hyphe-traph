# =============================================================================
# Link Store Header
# =============================================================================
#
# Class representing the header of the Link Store buffer. This header can be
# used to store various metadata and/or state.
#
import struct

# Binary format
# -
# NOTE: Since python mimics C struct, the block size should be respecting
# some rules (namely have even addresses or addresses divisble by 4 on some
# architecture).
LINK_STORE_HEADER_FORMAT = 'QQH'

# Header blocks
# -
# We are retaining at least one header block so we can keep the 0 block address
# as a NULL pointer and be able to store some metadata about the structure.
LINK_STORE_HEADER_BLOCKS = 1

# Positions


# Main class
class LinkStoreHeader(object):

    # =========================================================================
    # Constructor
    # =========================================================================
    def __init__(self, storage):

        # Properties
        self.storage = storage
        self.data = [
            0,
            0,
            0
        ] * LINK_STORE_HEADER_BLOCKS

        self.__ensure()
        self.read()

    def __repr__(self):
        class_name = self.__class__.__name__

        return (
            '<%(class_name)s>'
        ) % {
            'class_name': class_name
        }

    def __ensure(self):
        block = 0

        empty_data = struct.pack(LINK_STORE_HEADER_FORMAT, *([0] * 3))

        while block < LINK_STORE_HEADER_BLOCKS:
            data = self.storage.read(block)

            if not data:
                self.storage.write(empty_data, block)

            block += self.storage.block_size

    # =========================================================================
    # Utilities
    # =========================================================================

    # Method used to unpack data
    def unpack(self, data):
        return list(struct.unpack(LINK_STORE_HEADER_FORMAT, data))

    # Method used to set a switch to another block
    def read(self):
        self.data = self.unpack(self.storage.read(0))

    # Method used to pack the node to binary form
    def pack(self):
        return struct.pack(LINK_STORE_HEADER_FORMAT, *self.data)

    # Method used to write the node's data to storage
    def write(self):
        self.storage.write(self.pack(), 0)

    # =========================================================================
    # Getters/Setters
    # =========================================================================

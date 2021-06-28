"""
:brief:      Hamming Code Implementation
:details:
Hamming codes belong to the family of linear error correcting codes.
Documentation: https://en.wikipedia.org/wiki/Hamming_code
They can be used to identify up to two bit errors and correct one bit error per 256 byte block.

Translated from ATMEL C library.
/* ----------------------------------------------------------------------------
 *         ATMEL Microcontroller Software Support
 * ----------------------------------------------------------------------------
 * Copyright (c) 2008, Atmel Corporation
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *
 * - Redistributions of source code must retain the above copyright notice,
 * this list of conditions and the disclaimer below.
 *
 * Atmel's name may not be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * DISCLAIMER: THIS SOFTWARE IS PROVIDED BY ATMEL "AS IS" AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT ARE
 * DISCLAIMED. IN NO EVENT SHALL ATMEL BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
 * OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
 * LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
 * NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
 * EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 * ----------------------------------------------------------------------------
 */
"""
from enum import Enum

from tmtccmd.utility.logger import get_console_logger

LOGGER = get_console_logger()


class HammingReturnCodes(Enum):
    # No bit flips
    CODE_OKAY = 0,
    # Single bit flip which can be corrected
    ERROR_SINGLE_BIT = 1,
    # Error in the hamming code
    ERROR_ECC = 2,
    # Multi bit error which can not be corrected
    ERROR_MULTI_BIT = 3
    # Invalid input
    OTHER_ERROR = 4


def hamming_compute_256x(data: bytearray) -> bytearray:
    """
    Computes 3-bytes hamming codes for a data block whose size is multiple of
    256 bytes. Each 256 bytes block gets its own code.
    :param data: Data to compute code for. Should be a multiple of 256 bytes, pad data with 0
    if necessary!
    :return: bytearray of hamming codes with the size (3 / 256 * size). Empty bytearray if input
    is invalid.
    """
    if len(data) % 256 != 0:
        LOGGER.error("hamming_compute_256: Invalid input, datablock is not a multiple of "
                     "256 bytes!")
        return bytearray()

    remaining_size = len(data)
    hamming_code = bytearray()
    current_idx = 0
    while remaining_size > 0:
        hamming_code.extend(hamming_compute_256(data[current_idx: current_idx + 256]))
        remaining_size -= 256
        current_idx += 256
    return hamming_code


def hamming_verify_256x(data: bytearray, original_hamming_code: bytearray) -> HammingReturnCodes:
    if len(data) % 256 != 0:
        LOGGER.error("hamming_compute_256: Invalid input, datablock is not a multiple of "
                     "256 bytes!")
        return HammingReturnCodes.OTHER_ERROR
    if len(original_hamming_code) != len(data) / 256 * 3:
        LOGGER.error("hamming_compute_256: Invalid input, original hamming code does not have the"
                     "correct size!")
        return HammingReturnCodes.OTHER_ERROR

    remaining_size = len(data)
    current_data_idx = 0
    current_hamming_idx = 0
    error_code = HammingReturnCodes.CODE_OKAY
    while remaining_size > 0:
        current_data = bytearray(data[current_data_idx:current_data_idx + 256])
        error_code = hamming_verify_256(
            current_data, original_hamming_code[current_hamming_idx:current_hamming_idx + 3]
        )
        if error_code == HammingReturnCodes.ERROR_SINGLE_BIT:
            # Assign corrected data
            data[current_data_idx:current_data_idx + 256] = current_data
            LOGGER.info(f"Corrected single bit error at data block starting at {current_data_idx}")
            error_code = HammingReturnCodes.ERROR_SINGLE_BIT
        elif error_code == HammingReturnCodes.ERROR_MULTI_BIT:
            LOGGER.info(f"Detected multi-bit error at data block starting at {current_data_idx}")
            return error_code
        elif error_code == HammingReturnCodes.ERROR_ECC:
            LOGGER.info('Possible error in ECC code')
            return error_code
        current_data_idx += 256
        current_hamming_idx += 3
        remaining_size -= 256
    return error_code


def hamming_compute_256(data: bytearray) -> bytearray:
    """
    Takes a bytearray with the size of 256 bytes and calculates the 22 parity bits for the hamming
    code which will be returned as a three byte bytearray.
    :param data:
    :return:
    """
    hamming_code = bytearray(3)
    if len(data) != 256:
        LOGGER.error("hamming_compute_256: Invalid input, data does not have "
                     "a length of 256 bytes!")
        return hamming_code

    # Xor all bytes together to get the column sum;
    # At the same time, calculate the even and odd line codes
    column_sum = 0
    even_line_code = 0
    odd_line_code = 0
    even_column_code = 0
    odd_column_code = 0
    for index, byte in enumerate(data):
        column_sum ^= byte
        if (bin(byte).count('1') & 1) == 1:
            """
            Parity groups are formed by forcing a particular index bit to 0
            (even) or 1 (odd).
            Example on one byte:

            bits (dec)  7   6   5   4   3   2   1   0
                 (bin) 111 110 101 100 011 010 001 000
                                       '---'---'---'----------.
                                                              |
            groups P4' ooooooooooooooo eeeeeeeeeeeeeee P4     |
                   P2' ooooooo eeeeeee ooooooo eeeeeee P2     |
                   P1' ooo eee ooo eee ooo eee ooo eee P1     |
                                                              |
            We can see that:                                  |
             - P4  -> bit 2 of index is 0 --------------------'
             - P4' -> bit 2 of index is 1.
             - P2  -> bit 1 of index if 0.
             - etc...
            We deduce that a bit position has an impact on all even Px if
            the log2(x)nth bit of its index is 0
                ex: log2(4) = 2, bit2 of the index must be 0 (-> 0 1 2 3)
            and on all odd Px' if the log2(x)nth bit of its index is 1
                ex: log2(2) = 1, bit1 of the index must be 1 (-> 0 1 4 5)

            As such, we calculate all the possible Px and Px' values at the
            same time in two variables, evenLineCode and oddLineCode, such as
                 evenLineCode bits: P128  P64  P32  P16  P8  P4  P2  P1
                 oddLineCode  bits: P128' P64' P32' P16' P8' P4' P2' P1'
            """
            even_line_code ^= (255 - index)
            odd_line_code ^= index

    # At this point, we have the line parities, and the column sum.
    # First, We must caculate the parity group values on the column sum.
    for index in range(8):
        if column_sum & 1:
            even_column_code ^= 7 - index
            odd_column_code ^= index
        column_sum >>= 1

    # Now, we must interleave the parity values, to obtain the following layout:
    # Code[0] = Line1
    # Code[1] = Line2
    # Code[2] = Column
    # Line = Px' Px P(x-1)- P(x-1) ...
    # Column = P4' P4 P2' P2 P1' P1 PadBit PadBit
    hamming_code[0] = 0
    hamming_code[1] = 0
    hamming_code[2] = 0

    for index in range(4):
        hamming_code[0] <<= 2
        hamming_code[1] <<= 2
        hamming_code[2] <<= 2

        # Line 1
        if (odd_line_code & 0x80) != 0:
            hamming_code[0] |= 2
        if (even_line_code & 0x80) != 0:
            hamming_code[0] |= 1

        # Line 2
        if (odd_line_code & 0x08) != 0:
            hamming_code[1] |= 2
        if (even_line_code & 0x08) != 0:
            hamming_code[1] |= 1

        # Column
        if (odd_column_code & 0x04) != 0:
            hamming_code[2] |= 2
        if (even_column_code & 0x04) != 0:
            hamming_code[2] |= 1

        odd_line_code <<= 1
        even_line_code <<= 1
        odd_column_code <<= 1
        even_column_code <<= 1

    # Invert codes (linux compatibility)
    hamming_code[0] ^= 0xFF
    hamming_code[1] ^= 0xFF
    hamming_code[2] ^= 0xFF

    return hamming_code


def hamming_verify_256(data: bytearray, original_hamming_code: bytearray) -> HammingReturnCodes:
    """
    Verifies and corrects a 256-bytes block of data using the given 22-bits hamming code.
    Returns 0 if there is no error, otherwise returns a HAMMING_ERROR code.
    :param data: 256 code block to verify
    :param original_hamming_code: Original 3 byte hamming code with 22 parity bits
    :return: See HammingReturnCodes enums.
        - -1 for invalid input
        - 0 if there are no errors.
        - 1 if there is a single bit error which has been corrected
        - 2 if the hamming code has been corrupted
        - 3 if there was a multi bit error which can not be corrected
    """
    if len(data) != 256:
        LOGGER.error("hamming_compute_256: Invalid input, data does not have "
                     "a length of 256 bytes!")
        return HammingReturnCodes.OTHER_ERROR
    if len(original_hamming_code) != 3:
        LOGGER.error("hamming_compute_256: Invalid input, hamming code does not have "
                     "a length of 3 bytes!")
        return HammingReturnCodes.OTHER_ERROR

    # Calculate new code
    computed_hamming_code = hamming_compute_256(data)
    correction_code = bytearray(3)

    # Xor both codes together
    correction_code[0] = original_hamming_code[0] ^ computed_hamming_code[0]
    correction_code[1] = original_hamming_code[1] ^ computed_hamming_code[1]
    correction_code[2] = original_hamming_code[2] ^ computed_hamming_code[2]

    # If all bytes are 0, there is not error
    if correction_code[0] == 0 and correction_code[1] == 0 and correction_code[2] == 0:
        return HammingReturnCodes.CODE_OKAY

    # If there is a single bit error, there are 11 bits set to 1
    hamming_bit_count = \
        bin(correction_code[0]).count('1') + bin(correction_code[1]).count('1') + \
        bin(correction_code[2]).count('1')
    if hamming_bit_count == 11:
        # Get byte and bit indexes
        byte_idx = correction_code[0] & 0x80
        byte_idx |= (correction_code[0] << 1) & 0x40
        byte_idx |= (correction_code[0] << 2) & 0x20
        byte_idx |= (correction_code[0] << 3) & 0x10

        byte_idx |= (correction_code[1] >> 4) & 0x08
        byte_idx |= (correction_code[1] >> 3) & 0x04
        byte_idx |= (correction_code[1] >> 2) & 0x02
        byte_idx |= (correction_code[1] >> 1) & 0x01

        bit_idx = (correction_code[2] >> 5) & 0x04
        bit_idx |= (correction_code[2] >> 4) & 0x02
        bit_idx |= (correction_code[2] >> 3) & 0x01

        # Correct bit
        print_string = "Correcting byte " + str(byte_idx) + " at bit " + str(bit_idx)
        LOGGER.info(print_string)
        data[byte_idx] ^= (1 << bit_idx)
        return HammingReturnCodes.ERROR_SINGLE_BIT

    # Check whether ECC has been corrupted
    if hamming_bit_count == 1:
        return HammingReturnCodes.ERROR_ECC
    # Otherwise, this is a multibit error
    else:
        return HammingReturnCodes.ERROR_MULTI_BIT


def hamming_test():
    """
    Algorithm was verified with this  simple test.
    @return:
    """
    test_data = bytearray(256)
    for index in range(128):
        test_data[index] = index
    for index in range(128):
        test_data[index + 128] = 128 - index
    hamming_code = hamming_compute_256(test_data)
    print("Hamming code: " + str(hex(hamming_code[0])) + ", " + str(hex(hamming_code[1])) +
          ", " + str(hex(hamming_code[2])))

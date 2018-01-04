import time

import config
import dummy
import gbn
import ss


def get_transport_layer_by_name(name, local_port, remote_port, msg_handler):
    assert name == 'dummy' or name == 'ss' or name == 'gbn'
    if name == 'dummy':
        return dummy.DummyTransportLayer(local_port, remote_port, msg_handler)
    if name == 'ss':
        return ss.StopAndWait(local_port, remote_port, msg_handler)
    if name == 'gbn':
        return gbn.GoBackN(local_port, remote_port, msg_handler)


def make_data_packet(type, sequence, msg):
    """ Make the data packet
    """

    result = bytearray()
    type_bytes = type.to_bytes(2, BIG_ENDIAN)
    result.extend(type_bytes)
    sequence_bytes = sequence.to_bytes(2, BIG_ENDIAN)
    result.extend(sequence_bytes)
    checksum = make_checksum(type, sequence, msg)
    checksum_bytes = checksum.to_bytes(2, BIG_ENDIAN)
    result.extend(checksum_bytes)
    result.extend(msg)
    return result


def make_ack_packet(type, sequence):
    """ Make the ACK packet
    """

    result = bytearray()
    type_bytes = type.to_bytes(2, BIG_ENDIAN)
    result.extend(type_bytes)
    sequence_bytes = sequence.to_bytes(2, BIG_ENDIAN)
    result.extend(sequence_bytes)
    checksum = type + sequence
    checksum_bytes = checksum.to_bytes(2, BIG_ENDIAN)
    result.extend(checksum_bytes)
    return result


def make_checksum(type, sequence, msg):
    """ Calculate the checksum
    """

    return (type + sequence + calc_payload_sum(msg)) % HASH_SIZE


def calc_payload_sum(msg):
    """calculate sum of payload
    """

    total = 0
    data = bytearray()
    data.extend(msg)
    if len(msg) % 2 == 1:
        data.extend((1).to_bytes(1, BIG_ENDIAN))
    for i in range(0, len(data), 2):
        total = total + int.from_bytes(data[i:i + 2], BIG_ENDIAN)
    return total


def now():
    """ Get current time in msec
    """

    return int(round(time.time() * 1000))


def valid_data(msg):
    """ Check if it is valid data packet
    """

    type = int.from_bytes(msg[0:2], BIG_ENDIAN)
    sequence = int.from_bytes(msg[2:4], BIG_ENDIAN)
    checksum = int.from_bytes(msg[4:6], BIG_ENDIAN)
    payload = msg[6::]
    payload_sum = calc_payload_sum(payload)
    if type == config.MSG_TYPE_DATA and checksum == (type + sequence + payload_sum) % HASH_SIZE:
        return True
    return False


def valid_ack(msg):
    """Check if it is valid ack packet
    """

    type = int.from_bytes(msg[0:2], BIG_ENDIAN)
    sequence = int.from_bytes(msg[2:4], BIG_ENDIAN)
    checksum = int.from_bytes(msg[4:6], BIG_ENDIAN)
    if type == config.MSG_TYPE_ACK and checksum == type + sequence:
        return True
    return False


def get_sequence(msg):
    """Return the sequence number of ack packet
    """

    return int.from_bytes(msg[2:4], BIG_ENDIAN)


def get_payload(msg):
    """Get payload from packet
    """
    return msg[6::]


BIG_ENDIAN = "big"
HASH_SIZE = 65536

import logging
import threading

import config
import udt
import util


# Stop-And-Wait reliable transport protocol.
class StopAndWait:
    # static variable
    sender_ack_sequence = -1
    receiver_sequence = -1
    ss_lock = threading.Lock()


    # "msg_handler" is used to deliver messages to application layer
    # when it's ready.
    def __init__(self, local_port, remote_port, msg_handler):
        self.network_layer = udt.NetworkLayer(local_port, remote_port, self)
        self.msg_handler = msg_handler
        # Logger
        LOGGER_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        logging.basicConfig(format=LOGGER_FORMAT)
        self.logger = logging.getLogger('Stop and Wait Transport Protocol')
        self.logger.setLevel(logging.INFO)
        self.sender_count = 0

    # "send" is called by application. Return true on success, false
    # otherwise.
    def send(self, msg):
        # TODO: impl protocol to send packet from application layer.
        # call self.network_layer.send() to send to network layer.

        sequence = self.sender_count % 2
        packet = util.make_data_packet(config.MSG_TYPE_DATA, sequence, msg)
        self.network_layer.send(packet)
        self.logger.info('Sender sent pkt%d', sequence)
        start_time = util.now()
        while(True):
            current_time = util.now()
            if current_time - start_time > config.TIMEOUT_MSEC:
                self.logger.warning('Sender waits for ack%d timeout, resend pkt%d', sequence, sequence)
                self.network_layer.send(packet)
            with StopAndWait.ss_lock:
                if StopAndWait.sender_ack_sequence == sequence:
                    self.logger.info('Sender received ack%d', sequence)
                    break

        self.sender_count += 1
        return True

    # "handler" to be called by network layer when packet is ready.
    def handle_arrival_msg(self):
        # TODO: impl protocol to handle arrived packet from network layer.
        # call self.msg_handler() to deliver to application layer.

        msg = self.network_layer.recv()
        if util.valid_ack(msg):
            with StopAndWait.ss_lock:
                StopAndWait.sender_ack_sequence = util.get_sequence(msg)

        if util.valid_data(msg):
            sequence = util.get_sequence(msg)
            packet = util.make_ack_packet(config.MSG_TYPE_ACK, sequence)
            self.network_layer.send(packet)
            if StopAndWait.receiver_sequence != sequence:
                self.logger.info('Receiver received new packet: pkt%d', sequence)
                with StopAndWait.ss_lock:
                    StopAndWait.receiver_sequence = sequence
                payload = util.get_payload(msg)
                self.msg_handler(payload)
            else:
                self.logger.info('Receiver received duplicate packet: pkt%d, ignored', sequence)

    # Cleanup resources.
    def shutdown(self):
        # TODO: cleanup anything else you may have when implementing this class

        # static variable sender_ack_sequence, receiver_sequence
        with StopAndWait.ss_lock:
            StopAndWait.sender_ack_sequence = -1
            StopAndWait.receiver_sequence = -1
        self.network_layer.shutdown()


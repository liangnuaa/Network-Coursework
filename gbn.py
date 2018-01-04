import udt
import logging
import config
import util
import threading
import time

# Go-Back-N reliable transport protocol.
class GoBackN:
    # "msg_handler" is used to deliver messages to application layer
    # when it's ready.
    receiver_expect_sequence = 0
    gbn_lock = threading.Lock()


    def __init__(self, local_port, remote_port, msg_handler):
        self.network_layer = udt.NetworkLayer(local_port, remote_port, self)
        self.msg_handler = msg_handler
        self.sender_lock = threading.Lock()
        self.sender_stop_monitor = False
        self.sender_packet_list = []
        self.sender_timer_list = []
        self.sender_sequence_list = []
        self.sender_sequence_count = 0
        self.sender_ack_base = -1

        # Logger
        LOGGER_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        logging.basicConfig(format=LOGGER_FORMAT)
        self.logger = logging.getLogger('GoBackN Transport Protocol')
        self.logger.setLevel(logging.INFO)
        threading.Thread(target=self._timeout_monitor).start()
        threading.Thread(target=self._base_ack_monitor).start()


    # "send" is called by application. Return true on success, false
    # otherwise.
    def send(self, msg):
        # TODO: impl protocol to send packet from application layer.
        # call self.network_layer.send() to send to network layer.

        with self.sender_lock:
            if len(self.sender_packet_list) >= config.WINDOW_SIZE:
                return False

        sequence = self.sender_sequence_count % util.HASH_SIZE
        packet = util.make_data_packet(config.MSG_TYPE_DATA, sequence, msg)
        self.logger.info("Sender sent pkt%d", sequence)
        self.network_layer.send(packet)
        timer = util.now()
        with self.sender_lock:
            self.sender_sequence_list.append(sequence)
            self.sender_packet_list.append(packet)
            self.sender_timer_list.append(timer)
        self.sender_sequence_count += 1

        return True


    # "handler" to be called by network layer when packet is ready.
    def handle_arrival_msg(self):
        # TODO: impl protocol to handle arrived packet from network layer.
        # call self.msg_handler() to deliver to application layer.

        msg = self.network_layer.recv()

        if util.valid_ack(msg):
            sequence = util.get_sequence(msg)
            self.logger.info("Sender received ack%d", sequence)
            with self.sender_lock:
                self.sender_ack_base = sequence

        if util.valid_data(msg):
            sequence = util.get_sequence(msg)
            if sequence == GoBackN.receiver_expect_sequence:
                self.logger.info("Receiver received expected packet pkt%d", sequence)
                packet = util.make_ack_packet(config.MSG_TYPE_ACK, sequence)
                self.network_layer.send(packet)
                self.logger.info("Receiver send back ack%d", sequence)
                payload = util.get_payload(msg)
                self.msg_handler(payload)
                with GoBackN.gbn_lock:
                    GoBackN.receiver_expect_sequence = (GoBackN.receiver_expect_sequence + 1) % util.HASH_SIZE
            else:
                self.logger.info("Receiver received unexpected packet pkt%d", sequence)
                if GoBackN.receiver_expect_sequence > 0:
                    packet= util.make_ack_packet(config.MSG_TYPE_ACK, GoBackN.receiver_expect_sequence - 1)
                    self.network_layer.send(packet)
                    self.logger.info("Recevier send back ack%d", GoBackN.receiver_expect_sequence - 1)


    def _timeout_monitor(self):
        while not self.sender_stop_monitor:
            time.sleep(1)
            with self.sender_lock:
                if len(self.sender_packet_list) > 0:
                    pass
                else:
                    continue
                has_timeout = False
                current_time = util.now()
                if current_time - self.sender_timer_list[0] > config.TIMEOUT_MSEC:
                    self.logger.warning("Sender waiting for ack%d timeout", self.sender_sequence_list[0])
                    has_timeout = True
                if has_timeout:
                    self.sender_timer_list = []
                    for i in range(len(self.sender_packet_list)):
                        self.network_layer.send(self.sender_packet_list[i])
                        self.logger.info("Sender resent pkt%d", self.sender_sequence_list[i])
                        timer = util.now()
                        self.sender_timer_list.append(timer)


    def _base_ack_monitor(self):
        while not self.sender_stop_monitor:
            time.sleep(1)
            with self.sender_lock:
                while len(self.sender_packet_list) > 0:
                    if self.sender_ack_base >= self.sender_sequence_list[0]:
                        self.logger.info("Sender remove pkt%d from list", self.sender_ack_base)
                        self.sender_timer_list.pop(0)
                        self.sender_sequence_list.pop(0)
                        self.sender_packet_list.pop(0)
                    else:
                        break



    # Cleanup resources.
    def shutdown(self):
        # TODO: cleanup anything else you may have when implementing this
        # class.
        while len(self.sender_packet_list) != 0:
            time.sleep(1)
        with GoBackN.gbn_lock:
            GoBackN.receiver_expect_sequence = 0
        self.sender_stop_monitor = True
        self.network_layer.shutdown()


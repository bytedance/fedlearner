import gc
import logging
import os
import threading
import time

import grpc
from google.protobuf.empty_pb2 import Empty

import fedlearner.common.private_set_union_pb2 as psu_pb
import fedlearner.common.private_set_union_pb2_grpc as psu_grpc
import fedlearner.common.transmitter_service_pb2_grpc as tsmt_grpc
from fedlearner.channel import Channel
from fedlearner.data_join.private_set_union import transmit
from fedlearner.data_join.private_set_union import utils
from fedlearner.data_join.transmitter.components import Sender, Receiver
from fedlearner.data_join.transmitter.transmitter_worker import \
    TransmitterWorker
from fedlearner.proxy.channel import make_insecure_channel, ChannelType


class PSUTransmitterWorkerServicer(TransmitterWorker):
    def __init__(self,
                 phase,
                 receiver: Receiver,
                 sender: Sender):
        if isinstance(phase, str):
            self.phase = getattr(psu_pb, phase.title())
        else:
            assert phase in psu_pb.Phase.values()
            self.phase = phase
        super().__init__(receiver, sender)

    def enter_new_phase(self,
                        phase,
                        receiver: Receiver,
                        sender: Sender):
        assert phase in psu_pb.Phase.values()
        self.phase = phase
        self._receiver = receiver
        self._sender = sender


class PSUTransmitterWorker:
    def __init__(self,
                 role,
                 rank_id: int,
                 listen_port: int,
                 remote_address: str,
                 master_address: str,
                 psu_options,
                 encrypt_options,
                 sync_options,
                 l_diff_options,
                 r_diff_options):
        self._role = role
        self._rank_id = rank_id
        self._listen_address = "[::]:{}".format(listen_port)
        self._remote_address = remote_address
        self._token = "{}-{}".format('PSUTransmitterWorker', rank_id)

        self._options = psu_options
        self._encrypt_opt = encrypt_options
        self._sync_opt = sync_options
        self._l_diff_opt = l_diff_options
        self._r_diff_opt = r_diff_options
        self._phase = psu_pb.PSU_Encrypt

        self._condition = threading.Condition()
        self._connected = False
        self._terminated = False
        self._peer_terminated = False

        # channel
        self._channel = Channel(
            self._listen_address, self._remote_address, token=self._token)
        self._channel.subscribe(self._channel_callback)
        master_channel = make_insecure_channel(
            master_address, ChannelType.INTERNAL,
            options=[('grpc.max_send_message_length', 2 ** 31 - 1),
                     ('grpc.max_receive_message_length', 2 ** 31 - 1)]
        )

        # client & server
        self._master = psu_grpc.PSUTransmitterMasterServiceStub(master_channel)
        self._peer = tsmt_grpc.TransmitterWorkerServiceStub(self._channel)
        self._servicer = self._sender = self._receiver = None

    def _channel_callback(self, channel, event):
        if event == Channel.Event.PEER_CLOSED:
            with self._condition:
                self._peer_terminated = True
                self._condition.notify_all()
        if event == Channel.Event.ERROR:
            err = channel.error()
            logging.fatal("[Bridge] suicide due to channel exception: %s, "
                          "may be caused by peer restart", repr(err))
            os._exit(138)  # Tell Scheduler to restart myself

    def run(self):
        while True:
            try:
                resp = self._master.GetPhase(Empty())
                self._phase = resp.phase
                break
            except grpc.RpcError as e:
                logging.info(
                    '[Transmitter]: Error getting phase from master: %s, '
                    'sleep 5 secs and retry.', e.details())
                time.sleep(5)

        if self._phase == psu_pb.PSU_Encrypt:
            self._run_encrypt()
            self.wait_for_finish()
            self._phase = psu_pb.PSU_Sync
            self._wait_for_master()

        if self._phase == psu_pb.PSU_Sync:
            self._run_sync()
            self.wait_for_finish()
            self._phase = psu_pb.PSU_L_Diff
            self._wait_for_master()

        if self._phase == psu_pb.PSU_L_Diff:
            self._run_diff(self._phase)
            self.wait_for_finish()
            self._phase = psu_pb.PSU_R_Diff
            self._wait_for_master()

        if self._phase == psu_pb.PSU_R_Diff:
            self._run_diff(self._phase)
            self.wait_for_finish()
            self._phase = psu_pb.PSU_Reload
            self._wait_for_master()

    def _run_encrypt(self):
        receiver = transmit.ParquetEncryptReceiver(
            peer_client=self._peer,
            master_client=self._master,
            recv_queue_len=self._encrypt_opt.recv_queue_len
        )
        sender = transmit.ParquetEncryptSender(
            rank_id=self._rank_id,
            batch_size=self._encrypt_opt.batch_size,
            peer_client=self._peer,
            master_client=self._master,
            send_queue_len=self._encrypt_opt.send_queue_len,
            resp_queue_len=self._encrypt_opt.resp_queue_len,
            join_key=self._options.join_key
        )
        self._config_servicer(psu_pb.PSU_Encrypt, receiver, sender)

    def _run_sync(self):
        if self._role == psu_pb.Left:
            receiver = transmit.ParquetSyncReceiver(
                peer_client=self._peer,
                recv_queue_len=self._sync_opt.recv_queue_len
            )
            sender = None
        else:
            receiver = None
            sender = transmit.ParquetSyncSender(
                rank_id=self._rank_id,
                sync_columns=[utils.E2],
                need_shuffle=True,
                peer_client=self._peer,
                master_client=self._master,
                batch_size=self._sync_opt.batch_size,
                send_queue_len=self._sync_opt.send_queue_len,
                resp_queue_len=self._sync_opt.resp_queue_len
            )
        self._config_servicer(psu_pb.PSU_Sync, receiver, sender)

    def _run_diff(self, phase):
        if phase == psu_pb.PSU_L_Diff:
            mode = transmit.SetDiffMode.L
            opt = self._l_diff_opt
        else:
            mode = transmit.SetDiffMode.R
            opt = self._r_diff_opt

        if self._role == psu_pb.Left:
            receiver = None
            sender = transmit.ParquetSetDiffSender(
                rank_id=self._rank_id,
                mode=mode,
                peer_client=self._peer,
                master_client=self._master,
                batch_size=opt.batch_size,
                send_queue_len=opt.send_queue_len,
                resp_queue_len=opt.resp_queue_len
            )
        else:
            receiver = transmit.ParquetSetDiffReceiver(
                mode=mode,
                peer_client=self._peer,
                master_client=self._master,
                recv_queue_len=opt.recv_queue_len
            )
            sender = None
        self._config_servicer(phase, receiver, sender)

    def _config_servicer(self,
                         phase,
                         new_receiver: Receiver,
                         new_sender: Sender):
        if not self._servicer:
            self._servicer = PSUTransmitterWorkerServicer(
                phase, new_receiver, new_sender)
            tsmt_grpc.add_TransmitterWorkerServiceServicer_to_server(
                self._servicer, self._channel)
            self._channel.connect()
        else:  # new phase is guaranteed to be greater than that of servicer
            self.wait_for_finish()
            self._servicer.enter_new_phase(phase, new_receiver, new_sender)
        self._receiver = new_receiver
        self._sender = new_sender
        gc.collect()
        if self._receiver:
            self._receiver.start()
        if self._sender:
            self._sender.start()

    def wait_for_finish(self):
        if self._receiver:
            self._receiver.wait_for_finish()
        if self._sender:
            self._sender.wait_for_finish()

    def _wait_for_master(self, wait_time=30):
        while True:
            try:
                resp = self._master.GetPhase(Empty())
                if resp.phase == self._phase:
                    break
                logging.info('[Transmitter]: Master still in {} phase. '
                             'Worker phase: {}. Waiting...'
                             .format(psu_pb.Phase.keys()[resp.phase],
                                     psu_pb.Phase.keys()[self._phase]))
            except grpc.RpcError as e:
                logging.warning('[Transmitter]: Error getting master phase: %s',
                                e.details())
            time.sleep(wait_time)

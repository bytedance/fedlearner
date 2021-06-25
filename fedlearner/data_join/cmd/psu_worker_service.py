import argparse

import fedlearner.common.private_set_union_pb2 as psu_pb
from fedlearner.common.common import set_logger
from fedlearner.data_join.private_set_union.transmit import PSUTransmitterWorker
from fedlearner.data_join.private_set_union import parquet_utils as pqu
from fedlearner.data_join.private_set_union.utils import Paths

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PSUMasterService cmd.')
    parser.add_argument('--rank_id', type=int,
                        help='Rank id of this worker.')
    parser.add_argument('--role', type=str,
                        choices=['left', 'follower', 'right', 'leader'],
                        help='PSU role. Left/Follower will calculate union.')
    parser.add_argument('--master_address', '-m', type=str,
                        help='Address of local master')
    parser.add_argument('--remote_address', '-r', type=str,
                        help='Address of remote peer.')
    parser.add_argument('--listen_port', '-p', type=int, default=50051,
                        help='Listen port of remote connections.')
    parser.add_argument('--join_key', '-k', type=str,
                        help='Key to join examples.')
    # ======== Encrypt Phase Opts ========
    parser.add_argument('--batch_size', type=int,
                        help='Read batch size in encrypt phase.')
    parser.add_argument('--send_queue_len', type=int, default=3,
                        help='Length of sending queue in encrypt phase.')
    parser.add_argument('--recv_queue_len', type=int, default=3,
                        help='Length of receiving queue in encrypt phase.')
    parser.add_argument('--resp_queue_len', type=int, default=3,
                        help='Length of response queue in encrypt phase.')
    # ======== Sync Phase Opts ========
    # arg will be replaced by corresponding arg in encrypt phase if not provided
    parser.add_argument('--sync_batch_size', type=int,
                        help='Read batch size in l_diff phase.')
    parser.add_argument('--sync_send_queue_len', type=int, default=3,
                        help='Length of sending queue in sync phase.')
    parser.add_argument('--sync_recv_queue_len', type=int, default=3,
                        help='Length of receiving queue in sync phase.')
    parser.add_argument('--sync_resp_queue_len', type=int, default=3,
                        help='Length of response queue in sync phase.')
    # ======== L_Diff Phase Opts ========
    # arg will be replaced by corresponding arg in encrypt phase if not provided
    parser.add_argument('--l_diff_batch_size', type=int,
                        help='Read batch size in l_diff phase.')
    parser.add_argument('--l_diff_send_queue_len', type=int, default=3,
                        help='Length of sending queue in l_diff phase.')
    parser.add_argument('--l_diff_recv_queue_len', type=int, default=3,
                        help='Length of receiving queue in l_diff phase.')
    parser.add_argument('--l_diff_resp_queue_len', type=int, default=3,
                        help='Length of response queue in l_diff phase.')
    # ======== R_Diff Phase Opts ========
    # arg will be replaced by corresponding arg in encrypt phase if not provided
    parser.add_argument('--r_diff_batch_size', type=int,
                        help='Read batch size in r_diff phase.')
    parser.add_argument('--r_diff_send_queue_len', type=int, default=3,
                        help='Length of sending queue in r_diff phase.')
    parser.add_argument('--r_diff_recv_queue_len', type=int, default=3,
                        help='Length of receiving queue in r_diff phase.')
    parser.add_argument('--r_diff_resp_queue_len', type=int, default=3,
                        help='Length of response queue in r_diff phase.')

    args = parser.parse_args()
    set_logger()

    role = args.role.lower()
    if role == 'left' or role == 'follower':
        role = psu_pb.Left
    else:
        role = psu_pb.Right

    worker = PSUTransmitterWorker(
        role=role,
        rank_id=args.rank_id,
        listen_port=args.listen_port,
        remote_address=args.remote_address,
        master_address=args.master_address,
        psu_options=psu_pb.PSUOptions(
            join_key=args.join_key
        ),
        encrypt_options=psu_pb.EncryptOptions(
            batch_size=args.batch_size,
            send_queue_len=args.send_queue_len,
            recv_queue_len=args.recv_queue_len,
            resp_queue_len=args.resp_queue_len
        ),
        sync_options=psu_pb.SyncOptions(
            batch_size=args.sync_batch_size or args.batch_size,
            send_queue_len=args.sync_send_queue_len or args.send_queue_len,
            recv_queue_len=args.sync_recv_queue_len or args.recv_queue_len,
            resp_queue_len=args.sync_resp_queue_len or args.sync_queue_len
        ),
        l_diff_options=psu_pb.LDiffOptions(
            batch_size=args.l_diff_batch_size or args.batch_size,
            send_queue_len=args.l_diff_send_queue_len or args.send_queue_len,
            recv_queue_len=args.l_diff_recv_queue_len or args.recv_queue_len,
            resp_queue_len=args.l_diff_resp_queue_len or args.sync_queue_len
        ),
        r_diff_options=psu_pb.RDiffOptions(
            batch_size=args.r_diff_batch_size or args.batch_size,
            send_queue_len=args.r_diff_send_queue_len or args.send_queue_len,
            recv_queue_len=args.r_diff_recv_queue_len or args.recv_queue_len,
            resp_queue_len=args.r_diff_resp_queue_len or args.sync_queue_len
        ),
    )
    worker.run()

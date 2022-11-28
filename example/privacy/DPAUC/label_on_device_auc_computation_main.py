import datetime
import argparse
import pickle
import pandas as pd
from pytz import timezone
import tensorflow as tf
import numpy as np
from label_on_device_auc_computation_util import DataSet, DataSample, Client, \
                                                            ground_truth_auc
from resource_setup import setup_gpu

# import multiprocessing as mp
# from multiprocessing.pool import ThreadPool as Pool
# from multiprocessing import current_process

nprocs = 16
print(f"Number of CPU cores: {nprocs}")

west_tz = timezone('US/Pacific')
stamp = datetime.datetime.now(tz=west_tz).strftime("%Y%m%d_%H_%M_%S")

parser = argparse.ArgumentParser()
parser.add_argument('--number_clients', type=int, default=10 * 100)

parser.add_argument(
    "--clients_sampled_ratio",
    type=float,
    default=1.0,
    help='Clients sampled ratio when selecting clients to cal ROC AUC')
parser.add_argument(
    '--one_sample_per_device',
    action='store_true',
    help='one sample per device')
parser.add_argument(
    '--num_thresholds',
    type=int,
    default=100)  # AUC calculattion thresholds
# repeat the calcuation many times to get the mean and std of the estimated AUC
parser.add_argument('--repeat_times', type=int, default=1)
parser.add_argument(
    '--is_full_dataset',
    action='store_true',
    help='using the full dataset to evaluate')
parser.add_argument(
    '--clients_id_assigned_ranking_skewed',
    action='store_true',
    help="if ture: clients_id_assigned_ranking_skewed," \
                                        "otherwise assign clients id uniformly")

parser.add_argument(
    "--dp_noise_epsilon",
    type=float,
    default=0.0,
    help="dp noise epsilon for each value in the quadruple (i.e. TP). " \
                "The total dp budget is: 4 * num_thresholds * dp_noise_epsilon")
parser.add_argument(
    '--dp_noise_mechanism',
    type=str,
    default="None",
    help="Gaussian, Laplace, RR (rr), None")

parser.add_argument(
    '--gpu_option',
    action='store_true',
    help='whether to use gpu')
parser.add_argument('--device_number', type=int, default=0)

args = parser.parse_args()

setup_gpu(gpu_option=args.gpu_option, device_number=args.device_number)


# num_thresholds = args.num_thresholds
# repeat_times = args.repeat_times
clients_sampled_ratio = args.clients_sampled_ratio
label_flipping_eps = args.dp_noise_epsilon
# number_clients = args.number_clients
# one_sample_per_device = args.one_sample_per_device
# clients_id_assigned_ranking_skewed = args.clients_id_assigned_ranking_skewed
# dp_noise_eps = args.dp_noise_epsilon
# dp_noise_mechanism = args.dp_noise_mechanism
# is_full = args.is_full_dataset


def assign_client_id_uniformly(
        sample_id,
        number_clients,
        max_client_id,
        one_sample_per_device=False):
    if one_sample_per_device or number_clients >= max_client_id:
        return sample_id
    # else:
    return np.random.randint(0, high=number_clients)


def assign_client_id_ranking_skewed(
        ranking_idx,
        number_clients,
        max_client_id):
    if number_clients >= max_client_id:
        return ranking_idx
    block_size = max_client_id / number_clients
    client_id = int(ranking_idx / block_size)
    return client_id


def load_dataset(is_full=False):
    if is_full:
        label_pred_dict = pickle.load(open("./data/test_label_pred.pkl", "rb"))
    else:
        label_pred_dict = pickle.load(
            open("./data/test_0.1_label_pred.pkl", "rb"))
    return label_pred_dict



# def multi_epoch_run_paralle(is_full = False):
#     label_pred_dict = load_dataset(is_full = is_full)
#     t_s = datetime.datetime.now()
#     print("start: {}".format(t_s))
#     # aucs_gt_tf = []
#     # aucs_gt_sl = []
#     # roc_aucs_mean = []
#     # roc_aucs_std = []
#     # epochs = []

#     def run_one_epoch(epoch_idx):
#         print("worker: {} is running epoch: {}".format(current_process().pid, epoch_idx))
#         epoch = epoch_idx
#         d = label_pred_dict[epoch]


#     # for epoch, d in label_pred_dict.items():
#     #     if epoch >= 3:
#     #         break
#         labels, preds = [], []
#         for batch_idx, label_pred_pair in d.items():
#             labels += tf.cast(label_pred_pair[0], dtype=tf.float32).numpy().tolist()
#             preds += label_pred_pair[1].numpy().tolist()
#         preds = [p[0] for p in preds] # p is a list with one value (prediction score)
#         clients = []
#         clients_dict = {}
#         total_number_of_points = len(labels)
#         if clients_id_assigned_ranking_skewed:
#             sorted_res = sorted(zip(labels, preds), key = lambda x: x[1], reverse=False)
#             for i, (label, pred) in enumerate(sorted_res):
#                 sample = DataSample(pred, label)
#                 client_id = assign_client_id_ranking_skewed(i, number_clients, total_number_of_points)
#                 if client_id in clients_dict:
#                     clients_dict[client_id].append(sample)
#                 else:
#                     clients_dict[client_id] = [sample]
#         else:
#             for i, (label, pred) in enumerate(zip(labels, preds)):
#                 sample = DataSample(pred, label)
#                 client_id = assign_client_id_uniformly(i, number_clients,total_number_of_points, one_sample_per_device=one_sample_per_device)
#                 if client_id in clients_dict:
#                     clients_dict[client_id].append(sample)
#                 else:
#                     clients_dict[client_id] = [sample]
#         total_points = 0
#         for k,v in clients_dict.items():
#             client = Client(k, v)
#             # print("client_id: {}, # samples: {}".format(k, len(v)))
#             total_points += len(v)
#             clients.append(client)
#         print("# clients: {}, # total samples: {}".format(len(clients_dict.keys()), total_points))
#         dataset = DataSet(clients)
#         n_pos, n_neg = dataset.aggregate_noisy_number_of_positives(), dataset.aggregate_noisy_number_of_negatives()
#         print("# positives: {}, # negatives: {}".format(n_pos, n_neg))
#         auc_gt_tf_list = []
#         auc_gt_sl_list = []
#         auc_roc_list = []

#         # thresholds = list(np.linspace(0.0, 1.0, int(num_thresholds)))[::-1]
#         thresholds_1 = list(np.linspace(0.0, 0.2, int(num_thresholds * 0.5)))
#         thresholds_2 = list(np.linspace(0.2, 0.5, int(num_thresholds * 0.25)))
#         thresholds_3 = list(np.linspace(0.5, 1.0, int(num_thresholds * 0.25)))
#         thresholds = (thresholds_1 + thresholds_2 + thresholds_3)[::-1]
#         # print("thresholds: {}".format(thresholds))
#         def cal_auc_one_time():
#             print("worker: {} is running cal roc_auc".format(current_process().pid))
#             auc_roc = dataset.report_final_ROC_AUC(sampled_clients_ratio =clients_sampled_ratio,
#                                                    thresholds = thresholds,
#                                                    dp_noise_mechanism=dp_noise_mechanism,
#                                                    dp_noise_eps=dp_noise_eps)
#             # auc_roc = dataset.cal_ROC_AUC_rr(label_flipping_eps=label_flipping_eps, sampled_clients_ratio=clients_sampled_ratio, thresholds=thresholds)
#             return auc_roc
#             # auc_roc_list.append(auc_roc)

#         auc_gt_tf = ground_truth_auc(tf.cast(labels, dtype=tf.float32), preds, method="tf",
#                                         num_thresholds=200)
#         auc_gt_sl = ground_truth_auc(labels, preds, method="sklearn")

#         auc_gt_tf_list.append(auc_gt_tf)
#         auc_gt_sl_list.append(auc_gt_sl)
#             # return (auc_roc, auc_gt_tf, auc_gt_sl)

#         with Pool(nprocs) as pool:
#             auc_roc_list = pool.starmap_async(cal_auc_one_time, [() for _ in range(repeat_times)])
#             auc_roc_list.wait()
#         auc_roc_list = list(auc_roc_list.get())
#         # pool = Pool(processes=nprocs)
#         #
#         # auc_roc_list = list(pool.starmap(cal_auc_one_time, [() for _ in range(repeat_times)]))
#         # pool.close()
#         # pool.join()

#         print("epoch: {}, mean_auc_tf: {}, std_auc_tf: {}".format(epoch, np.mean(auc_gt_tf_list), np.std(auc_gt_tf_list)))
#         print("epoch: {}, mean_auc_sk: {}, std_auc_sk: {}".format(epoch, np.mean(auc_gt_sl_list), np.std(auc_gt_sl_list)))
#         print("epoch: {}, mean_roc_auc: {}, std_roc_auc: {}".format(epoch, np.mean(auc_roc_list), np.std(auc_roc_list)))
#         t_e = datetime.datetime.now()
#         print("epoch {} ends at: {} , uses: {}".format(epoch, t_e, t_e - t_s))

#         return (np.mean(auc_gt_tf_list), np.mean(auc_gt_sl_list), np.mean(auc_roc_list), np.std(auc_roc_list))

#     with Pool() as pool:
#         results = pool.map_async(run_one_epoch, range(3))
#         results.wait()
#         # pool.close()
#         # pool.join()

#     aucs_gt_tf = [r for (r, _, _, _) in results.get()]
#     aucs_gt_sl = [r for (_, r, _, _) in results.get()]
#     roc_aucs_mean = [r for (_, _, r, _) in results.get()]
#     roc_aucs_std = [r for (_, _, _, r) in results.get()]

#     epochs = list(range(3))

#     df = pd.DataFrame(data={"epoch":epochs, "auc_gt_tf":aucs_gt_tf, "auc_gt_sl":aucs_gt_sl, "roc_auc_mean":roc_aucs_mean, "roc_auc_std":roc_aucs_std})
#     file_name = str(stamp) + "_test_labeldpeps_{}_numClients_{}_repeat_times_{}_numThresholds_{}_ClientsSampledRatio_{}_nprocs_{}".format(
#                                         str(label_flipping_eps),
#                                         str(number_clients),
#                                         str(repeat_times),
#                                         str(num_thresholds),
#                                         str(clients_sampled_ratio),
#                                         str(nprocs))
#     if clients_id_assigned_ranking_skewed:
#         file_name += "_ClientsAssignedSkewed"
#     else:
#         file_name += "_ClientsAssignedUniformly"
#     if is_full:
#         file_name = "logs/test_set/" + file_name + ".csv"
#     else:
#         file_name = "logs/sample_0.1_of_test/" + file_name + ".csv"

#     df.to_csv(file_name,index=False)



def multi_epoch_run(is_full=False, 
                    number_clients=10,
                    num_thresholds=100,
                    repeat_times=50,
                    clients_id_assigned_ranking_skewed=False,
                    dp_noise_eps=1.0,
                    dp_noise_mechanism="Laplace",
                    one_sample_per_device=False,):

    label_pred_dict = load_dataset(is_full=is_full)
    t_s = datetime.datetime.now()
    print("start: {}".format(t_s))
    aucs_gt_tf = []
    aucs_gt_sl = []
    roc_aucs_mean = []
    roc_aucs_std = []
    epochs = []

    # def run_one_epoch(epoch_idx):
    #     epoch = epoch_idx
    #     d = label_pred_dict[epoch]

    for epoch, d in label_pred_dict.items():
        if epoch >= 3:
            break
        labels, preds = [], []
        for batch_idx, label_pred_pair in d.items():
            labels += tf.cast(label_pred_pair[0],
                              dtype=tf.float32).numpy().tolist()
            preds += label_pred_pair[1].numpy().tolist()
        preds = [p[0] for p in preds]
        clients = []
        clients_dict = {}
        total_number_of_points = len(labels)
        if clients_id_assigned_ranking_skewed:
            sorted_res = sorted(zip(labels, preds),
                                key=lambda x: x[1], reverse=False)
            for i, (label, pred) in enumerate(sorted_res):
                sample = DataSample(pred, label)
                client_id = assign_client_id_ranking_skewed(
                    i, number_clients, total_number_of_points)
                if client_id in clients_dict:
                    clients_dict[client_id].append(sample)
                else:
                    clients_dict[client_id] = [sample]
        else:
            for i, (label, pred) in enumerate(zip(labels, preds)):
                sample = DataSample(pred, label)
                client_id = assign_client_id_uniformly(
                    i,
                    number_clients,
                    total_number_of_points,
                    one_sample_per_device=one_sample_per_device)
                if client_id in clients_dict:
                    clients_dict[client_id].append(sample)
                else:
                    clients_dict[client_id] = [sample]
        total_points = 0
        for k, v in clients_dict.items():
            client = Client(k, v)
            # print("client_id: {}, # samples: {}".format(k, len(v)))
            total_points += len(v)
            clients.append(client)
        print("# clients: {}, # total samples: {}".format(
            len(clients_dict.keys()), total_points))
        dataset = DataSet(clients)
        n_pos, n_neg = dataset.aggregate_noisy_number_of_positives(
        ), dataset.aggregate_noisy_number_of_negatives()
        print("# positives: {}, # negatives: {}".format(n_pos, n_neg))
        auc_gt_tf_list = []
        auc_gt_sl_list = []
        # auc_roc_list = []

        # thresholds = list(np.linspace(0.0, 1.0, int(num_thresholds)))[::-1]
        thresholds_1 = list(np.linspace(0.0, 0.2, int(num_thresholds * 0.5)))
        thresholds_2 = list(np.linspace(0.2, 0.5, int(num_thresholds * 0.25)))
        thresholds_3 = list(np.linspace(0.5, 1.0, int(num_thresholds * 0.25)))
        thresholds = (thresholds_1 + thresholds_2 + thresholds_3)[::-1]
        # print("thresholds: {}".format(thresholds))

        def cal_auc_one_time():
            return dataset.report_final_ROC_AUC(
                                    sampled_clients_ratio=clients_sampled_ratio,
                                    thresholds=thresholds,
                                    dp_noise_mechanism=dp_noise_mechanism,
                                    dp_noise_eps=dp_noise_eps)

        auc_gt_tf = ground_truth_auc(tf.cast(labels,dtype=tf.float32),
                                    preds,
                                    method="tf",
                                    num_thresholds=200)

        auc_gt_sl = ground_truth_auc(labels, preds, method="sklearn")

        auc_gt_tf_list.append(auc_gt_tf)
        auc_gt_sl_list.append(auc_gt_sl)

        auc_roc_list = list(
                        map(lambda x: cal_auc_one_time(), range(repeat_times)))

        print("epoch: {}, mean_auc_tf: {}, std_auc_tf: {}".format(
            epoch, np.mean(auc_gt_tf_list), np.std(auc_gt_tf_list)))
        print("epoch: {}, mean_auc_sk: {}, std_auc_sk: {}".format(
            epoch, np.mean(auc_gt_sl_list), np.std(auc_gt_sl_list)))

        aucs_gt_tf.append(np.mean(auc_gt_tf_list))
        aucs_gt_sl.append(np.mean(auc_gt_sl_list))

        roc_aucs_mean.append(np.mean(auc_roc_list))
        roc_aucs_std.append(np.std(auc_roc_list))
        epochs.append(epoch)
        t_e = datetime.datetime.now()
        print("epoch {} ends at: {} , uses: {}".format(epoch, t_e, t_e - t_s))

    df = pd.DataFrame(
        data={
            "epoch": epochs,
            "auc_gt_tf": aucs_gt_tf,
            "auc_gt_sl": aucs_gt_sl,
            "roc_auc_mean": roc_aucs_mean,
            "roc_auc_std": roc_aucs_std})
    file_name = str(stamp) + \
        "_{}_eps_{}_numClients_{}_repeat_times_{}_" \
                            "numThresholds_{}_ClientsSampledRatio_{}".format(
                                        str(dp_noise_mechanism),
                                        str(dp_noise_eps),
                                        str(args.number_clients),
                                        str(repeat_times),
                                        str(num_thresholds),
                                        str(clients_sampled_ratio))
    if clients_id_assigned_ranking_skewed:
        file_name += "_ClientsAssignedSkewed"
    else:
        file_name += "_ClientsAssignedUniformly"
    if is_full:
        file_name = "outputs/test_set/" + file_name + ".csv"
    else:
        file_name = "outputs/sample_0.1_of_test/" + file_name + ".csv"

    df.to_csv(file_name, index=False)


if __name__ == "__main__":
    multi_epoch_run(is_full=args.is_full_dataset,
                    number_clients=args.number_clients,
                    num_thresholds=args.num_thresholds,
                    repeat_times=args.repeat_times,
                    clients_id_assigned_ranking_skewed= \
                            args.clients_id_assigned_ranking_skewed,
                    dp_noise_eps=args.dp_noise_epsilon,
                    dp_noise_mechanism=args.dp_noise_mechanism,
                    one_sample_per_device=args.one_sample_per_device,
                    )

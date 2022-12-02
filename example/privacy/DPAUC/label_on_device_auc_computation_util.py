from itertools import chain
import random
# import datetime
from functools import reduce
# from visualization_util import visualize_roc_auc
# import multiprocessing as mp
from multiprocessing.pool import ThreadPool as Pool
import tensorflow as tf
from sklearn import metrics
import numpy as np

run_parallel = False
nprocs = 8
print(f"Using Number of CPU cores: {nprocs}")


def dp_flipping_rate(eps):
    if eps >= 99.0 or eps <= 0:
        return 0.0
    # else:
    return 1.0 / (1.0 + np.exp(eps))


def convert_dp_sensitivity_to_std(
                            sensitivity,
                            epsilon,
                            delta,
                            mechanism="Laplace"):
    noise_std = 0.0
    if epsilon <= 0.0 or epsilon >= 101.0:
        noise_std = 0.0
    if mechanism.endswith("Laplace"):
        # Laplace
        # print("epsilon: {}".format(epsilon))
        noise_std = sensitivity / epsilon
    return noise_std


def generate_noisy_value_w_dp(
        sensititvity=1.0,
        noise_eps=0.0,
        noisy_mechanism="Laplace"):
    noise_std = convert_dp_sensitivity_to_std(
        sensititvity, noise_eps, delta=0.0, mechanism=noisy_mechanism)
    if noise_std > 0.0:
        if noisy_mechanism.endswith("Laplace"):
            noise = np.random.laplace(0, noise_std)
        else:
            noise = 0.0
    else:
        noise = 0.0
    return noise


class DataSample:
    def __init__(self, prediction_score, true_label, client_id=None):
        self.prediction_score = prediction_score
        self.true_label = true_label
        self.client_id = client_id
        self.report_label = self.true_label

    def report_quadruple(self, threshold):
        # print("prediction score: {}, threshold: {}, label: {}".format(
        #                 self.prediction_score, threshold, self.report_label))
        quadruple_res = (0.0, 0.0, 1.0, 0.0)
        if self.prediction_score >= threshold and self.report_label >= 0.99:
            quadruple_res = (1.0, 0.0, 0.0, 0.0)  # TP, FP, TN, FN
        elif self.prediction_score >= threshold and self.report_label <= 0.01:
            quadruple_res = (0.0, 1.0, 0.0, 0.0)
        elif self.prediction_score < threshold and self.report_label >= 0.99:
            quadruple_res = (0.0, 0.0, 0.0, 1.0)
        else:
            quadruple_res = (0.0, 0.0, 1.0, 0.0)
        return quadruple_res

    def set_client_id(self, client_id):
        self.client_id = client_id

    def flip_label(self, dp_epsilon=None, flipping_prob=None):
        if not dp_epsilon and not flipping_prob:
            self.report_label = self.true_label
        if dp_epsilon:
            flipping_prob = dp_flipping_rate(dp_epsilon)
        output = np.random.binomial(1, flipping_prob)
        # print("output: {}".format(output))
        self.report_label = output * \
            (1 - self.true_label) + (1 - output) * self.true_label

    def reset_report_label(self):
        self.report_label = self.true_label


class Client:
    def __init__(self, client_id, data_samples):
        self.client_id = client_id
        self.data_samples = data_samples
        self.update_client_id()
        self.true_number_of_positives = self.report_true_number_of_positives()
        self.true_number_of_negatives = self.report_true_number_of_negatives()

    def update_client_id(self):
        for sample in self.data_samples:
            sample.set_client_id(self.client_id)

    def report_noisy_number_of_positives(self):  # can add noise later
        return sum([sample.report_label for sample in self.data_samples])
    # def get_number_of_negatives(self):
    #     return sum([1 - sample.report_label for sample in self.data_samples])

    def report_noisy_number_of_negatives(self):
        return sum([1 - sample.report_label for sample in self.data_samples])

    def report_true_number_of_positives(self):
        return sum([sample.true_label for sample in self.data_samples])

    def report_true_number_of_negatives(self):
        return sum([1 - sample.true_label for sample in self.data_samples])

    def get_number_of_data_samples(self):
        return len(self.data_samples)

    def aggregate_quadruples(self, threshold):
        def report_quadruple_per_sample(a_sample, threshold):
            return np.array(a_sample.report_quadruple(threshold))

        if run_parallel:
            pool = Pool(processes=nprocs)
            result = pool.starmap(
                report_quadruple_per_sample, [
                    (a_sample, threshold) for a_sample in self.data_samples])
            pool.close()
            pool.join()
            # print("results: {}".format(result))
            return reduce(lambda x, y: x + y, result)
        # else:
        return reduce(lambda x,
                          y: x + y,
                          map(lambda x: np.array(x.report_quadruple(threshold)),
                              self.data_samples))

    def report_aggregated_quadruples(
            self,
            threshold,
            dp_noise_mechanism="None",
            dp_noise_eps=0.0):
        vanilla_res = self.aggregate_quadruples(threshold)
        # print("vanilla_res_quadruples: {}".format(vanilla_res))
        noise = np.array([generate_noisy_value_w_dp(sensititvity=1.0,
                                                    noise_eps=dp_noise_eps,
                        noisy_mechanism=dp_noise_mechanism) for _ in range(4)])
        # noise = np.array((0.0, 0.0, 0.0, 0.0))
        # print("vanilla_res: {}, noise: {}".format(vanilla_res, noise))
        return vanilla_res + noise


class DataSet:
    def __init__(self, clients):
        self.clients = clients
        self.number_of_clients = len(self.clients)
        self.all_data_samples = list(chain.from_iterable(
            [client.data_samples for client in self.clients]))
        self.total_true_number_of_samples = len(self.all_data_samples)
        self.noisy_number_of_positives = -1.0
        self.noisy_number_of_negatives = -1.0

    def cal_quadruples_once(
            self,
            sampled_clients_ratio=1.0,
            threshold=0.5,
            dp_noise_mechanism="None",
            dp_noise_eps=0.0):
        # print(type(self.clients))
        sampled_clients = random.sample(self.clients, int(
            self.number_of_clients * sampled_clients_ratio))
        # print("sampled_clients: {}, corresponding length: {}".format(
        #                               sampled_clients, len(sampled_clients)))

        def report_aggregated_quadruples_per_client(
                a_client, threshold, dp_noise_mechanism, dp_noise_eps):
            return a_client.report_aggregated_quadruples(
                threshold, dp_noise_mechanism=dp_noise_mechanism,
                                        dp_noise_eps=dp_noise_eps)

        if run_parallel:
            pool = Pool(processes=nprocs)
            result = pool.starmap(
                report_aggregated_quadruples_per_client, [
                    (a_client, threshold, dp_noise_mechanism, dp_noise_eps)
                                            for a_client in sampled_clients])
            pool.close()
            pool.join()
            res = reduce(lambda x, y: x + y, result)
        else:
            res = reduce(lambda x,
                         y: x + y,
                         map(lambda x: x.report_aggregated_quadruples(threshold,
                                        dp_noise_mechanism=dp_noise_mechanism,
                                                    dp_noise_eps=dp_noise_eps),
                             sampled_clients))

        res = [v * 1.0 for v in list(res)]
        tp, fp, tn, fn = max(
            res[0], 0), max(
            res[1], 0), max(
            res[2], 0), max(
                res[3], 0)
        if fp + tn == 0 or tp + fn == 0:
            fpr, tpr = 0.0, 0.0
        else:
            fpr, tpr = fp / (fp + tn), tp / (tp + fn)
        return (fpr, tpr)

    def cal_fpr_tpr(
            self,
            sampled_clients_ratio=1.0,
            thresholds=None,
            dp_noise_mechanism="None",
            dp_noise_eps=0.0):
        if run_parallel:
            pool = Pool(processes=nprocs)
            res = pool.starmap(self.cal_quadruples_once,
                               [(sampled_clients_ratio,
                                 threshold,
                                 dp_noise_mechanism,
                                 dp_noise_eps) for threshold in thresholds])
            pool.close()
            pool.join()
        else:
            res = [
                self.cal_quadruples_once(
                    sampled_clients_ratio,
                    threshold,
                    dp_noise_mechanism,
                    dp_noise_eps) for threshold in thresholds]

        # print('unsorted res: {}'.format(res))
        res = sorted(res, key=lambda x: x[0])
        # print("sorted res: {}".format(res))
        # print("resulted fprs, tprs: {}".format(res))
        fprs = [r[0] for r in res]
        tprs = [r[1] for r in res]
        # print("fprs: {}".format(fprs))
        # print("tprs: {}".format(tprs))
        # visualize_roc_auc(fprs, tprs, "sampled_clients_ratio_" + str(
        #                 sampled_clients_ratio) + "_numThresholds_" +
        #                 str(len(thresholds)) + "_" + str(dp_noise_mechanism)+
        #                   "_eps_" + str(dp_noise_eps))
        return (fprs, tprs)

    def cal_roc_auc(
            self,
            sampled_clients_ratio=1.0,
            thresholds=None,
            dp_noise_mechanism="None",
            dp_noise_eps=0.0):
        fprs, tprs = self.cal_fpr_tpr(
            sampled_clients_ratio, thresholds, dp_noise_mechanism, dp_noise_eps)
        res = metrics.auc(fprs, tprs)
        print("final auc: {}".format(res))
        return res

    def flip_all_labels(self, prob):
        for sample in self.all_data_samples:
            sample.flip_label(flipping_prob=prob)

        self.aggregate_noisy_number_of_positives()
        self.aggregate_noisy_number_of_negatives()

    def reset_all_flipped_labels(self):
        for sample in self.all_data_samples:
            sample.reset_report_label()

    def aggregate_noisy_number_of_positives(self):
        # based on randomized responses
        self.total_noisy_number_of_positives = sum(
            [client.report_noisy_number_of_positives()
                                                    for client in self.clients])
        return self.total_noisy_number_of_positives

    def aggregate_noisy_number_of_negatives(self):
        # based on randomized responses
        self.total_noisy_number_of_negatives = sum(
            [client.report_noisy_number_of_negatives()
                                                    for client in self.clients])
        return self.total_noisy_number_of_negatives

    def aggregate_true_number_of_positives(self):
        self.total_true_number_of_positives = sum(
            [client.true_number_of_positives for client in self.clients])
        return self.total_true_number_of_positives

    def aggregate_true_number_of_negatives(self):
        self.total_true_number_of_negatives = sum(
            [client.true_number_of_negatives for client in self.clients])
        return self.total_true_number_of_negatives

    def aggregate_number_of_samples(self):
        return self.total_true_number_of_samples

    def convert_corrupted_auc_to_real(self, p2n_p, n2p_q, auc_corrupted):
        true_total_number_of_positives = sum(
            [client.true_number_of_positives for client in self.clients])
        true_total_number_of_negatives = sum(
            [client.true_number_of_negatives for client in self.clients])
         # pi
        base_rate = true_total_number_of_positives * 1.0 / \
            (true_total_number_of_positives + true_total_number_of_negatives)
        print("true base_rate: {}".format(base_rate))

        estimated_total_number_of_positives = (
            (self.total_noisy_number_of_positives * (1.0 - n2p_q) -
           self.total_noisy_number_of_negatives * n2p_q) / (1.0 - p2n_p - n2p_q)
            )

        estimated_total_number_of_negatives = true_total_number_of_positives + \
            true_total_number_of_negatives - estimated_total_number_of_positives
        base_rate = estimated_total_number_of_positives * 1.0 / \
                                        (estimated_total_number_of_negatives +
                                            estimated_total_number_of_positives)
        print("base_rate_corr: {}".format(base_rate))
        alpha = (1.0 - base_rate) * n2p_q / (base_rate * \
                 (1.0 - p2n_p) + (1.0 - base_rate) * n2p_q)
        beta = base_rate * p2n_p / \
            (base_rate * p2n_p + (1.0 - base_rate) * (1.0 - n2p_q))
        # print("base_rate: {}, alpha: {}, beta: {}".format(base_rate,
        #                                                     alpha, beta))
        auc_real = (auc_corrupted - (alpha + beta) / 2.0) / \
            (1.0 - alpha - beta)
        return auc_real

    def cal_ROC_AUC_rr(
                    self,
                    label_flipping_eps=10000.0,
                    sampled_clients_ratio=1.0,
                    thresholds=None):

        label_flipping_prob = dp_flipping_rate(label_flipping_eps)
        self.flip_all_labels(label_flipping_prob)
        auc_corrupted = self.cal_roc_auc(
            sampled_clients_ratio=sampled_clients_ratio,
            thresholds=thresholds,
            dp_noise_mechanism="None",
            dp_noise_eps=label_flipping_eps)

        auc_real = self.convert_corrupted_auc_to_real(
            p2n_p=label_flipping_prob,
            n2p_q=label_flipping_prob,
            auc_corrupted=auc_corrupted)
        print(
            "auc_corrupted: {}, auc_real: {}".format(
                auc_corrupted,
                auc_real))
        return auc_real

    def report_final_ROC_AUC(
            self,
            sampled_clients_ratio=1.0,
            thresholds=None,
            dp_noise_mechanism="RR",
            dp_noise_eps=10000.0):
        if dp_noise_mechanism in ["RR", "rr"]:
            return self.cal_ROC_AUC_rr(
                label_flipping_eps=dp_noise_eps,
                sampled_clients_ratio=sampled_clients_ratio,
                thresholds=thresholds)
        noisy_auc = self.cal_roc_auc(
            sampled_clients_ratio=sampled_clients_ratio,
            thresholds=thresholds,
            dp_noise_mechanism=dp_noise_mechanism,
            dp_noise_eps=dp_noise_eps)
        print("noisy_auc:{} with: {} and eps: {}".format(
            noisy_auc, dp_noise_mechanism, dp_noise_eps))
        return noisy_auc


def ground_truth_auc(input_y, input_pred, method="sklearn",
                                                        num_thresholds=1000):
    y = np.array(input_y)
    pred = np.array(input_pred)
    if method == "sklearn":
        fpr, tpr, thresholds = metrics.roc_curve(y, pred, pos_label=1)
        res = metrics.auc(fpr, tpr)
    else:
        m = tf.keras.metrics.AUC(num_thresholds=num_thresholds)
        m.update_state(y, pred)
        res = m.result().numpy()
    return res


if __name__ == "__main__":

    data = [(0.8, 0), (0.1, 0), (0.2, 0), (0.4, 0), (0.5, 0),
                                                (0.6, 1), (0.7, 1), (0.88, 0),
                    (0.12, 1), (0.98, 1), (0.98, 1), (0.998, 0), (0.765, 1),
                                                        (0.892, 0), (0.34, 1)]
    test_pred_list = [test_x for (test_x, _) in data]
    test_y_list = [test_y for (_, test_y) in data]
    auc_sklearn = ground_truth_auc(test_y_list, test_pred_list,
                                    "sklearn", num_thresholds=1000)
    auc_tf = ground_truth_auc(test_y_list, test_pred_list, "tf",
                                         num_thresholds=1000)
    test_clients = []
    test_threshold = 1.0
    for i, d in enumerate(data):
        data_sample = DataSample(d[0], d[1])
        # data_sample_2 = DataSample(0.21, 1.0)
        # data_sample_3 = DataSample(0.21, 0.0)
        client = Client(i, [data_sample])
        print(client.aggregate_quadruples(test_threshold))
        test_clients.append(client)
    dataset = DataSet(test_clients)
    for test_sample in dataset.all_data_samples:
        print(
            "client:{}, score: {}, report label: {}, ranking: {}".format(
                test_sample.client_id,
                test_sample.prediction_score,
                test_sample.report_label,
                test_sample.report_quadruple(test_threshold)))
    test_thresholds = list(np.linspace(0.0, 1.0, num=100))[::-1]

    dataset.cal_roc_auc(sampled_clients_ratio=1.0, thresholds=test_thresholds)
    print("ground truth: auc_sklearn: {}, auc_tf: {}".format(
                                                        auc_sklearn, auc_tf))

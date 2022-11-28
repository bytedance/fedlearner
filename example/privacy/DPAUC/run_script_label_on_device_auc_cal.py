# import os
import subprocess
# import time
import datetime
from pytz import timezone

west_tz = timezone('US/Pacific')
stamp = datetime.datetime.now(tz=west_tz).strftime("%Y%m%d_%H_%M_%S")

common_options = [
    'python3',
    'label_on_device_auc_computation_main.py',
]


using_gpu = False
gpu_opt = ["--gpu_option"]
gpu_start_idx = 3
gpus = {}
for gpu_id in range(8):
    gpus[gpu_id] = ['--device_number', str(gpu_id)]


number_clients_list = ["10"]
dp_noise_mechanisms = ["Laplace"] # "Laplace", "RR", "None" (no protection)
# total epsilon = dp_noise_eps * num_thresholds * 4 for Laplace;
# For RR, it's the dp budget as it is.
dp_noise_eps_list = ["0.1"]
assign_client_id_ranking_skewed = False
repeat_times = 5
num_thresholds = [10]

for i, number_clients in enumerate(number_clients_list):
    for j, noise_eps in enumerate(dp_noise_eps_list):
        for k, num_threshold in enumerate(num_thresholds):
            for z, dp_noise_mechanism in enumerate(dp_noise_mechanisms):
                dp_noise_mechanism_opt = [
                    "--dp_noise_mechanism", str(dp_noise_mechanism)]
                number_clients_opt = ["--number_clients", number_clients]
                dp_noise_eps_opt = ["--dp_noise_eps", str(noise_eps)]
                repeat_times_opt = ["--repeat_times", str(repeat_times)]
                num_thresholds_opt = ["--num_thresholds", str(num_threshold)]
                args_list = (
                    common_options +
                    number_clients_opt +
                    dp_noise_mechanism_opt +
                    dp_noise_eps_opt +
                    repeat_times_opt +
                    num_thresholds_opt)
                if using_gpu:
                    idx = i * (len(dp_noise_eps_list) * \
                            len(num_thresholds)) + j * len(num_thresholds) + k
                    args_list += gpu_opt + gpus[(gpu_start_idx + idx) % 8]
                log_file_name = "outputs/stdout_logs/" + \
                    str(stamp) + "_numberClients_" + number_clients + \
                    str(dp_noise_mechanism) + "_eps_" + noise_eps
                log_file_name += "numThreshold_" + \
                    str(num_threshold) + "_repeatTimes_" + str(repeat_times)
                if assign_client_id_ranking_skewed:
                    assign_client_id_ranking_skewed_opt = [
                        "--clients_id_assigned_ranking_skewed"]
                    log_f = open(log_file_name
                                 + "_ClientAssignedSkewed"
                                 + ".txt", "w")
                    args_list += assign_client_id_ranking_skewed_opt
                else:
                    log_f = open(log_file_name + ".txt", "w")
                print("args: {}".format(args_list))
                subprocess.Popen(args=args_list, stdout=log_f)
                log_f.close()
# FNULL.close()
log_f.close()

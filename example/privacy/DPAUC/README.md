## ReadMe

DPAUC has been accepted to The Thirty-Seventh AAAI Conference on Artificial Intelligence, Safe and Robust AI Track, AAAI 2023. The paper can be viewed at: https://arxiv.org/abs/2208.12294. If you have any questions and comments, feel free to reach: jiankai.sun@bytedance.com.


### Requirements

* Python 3.x
* Numpy 
* Tensorflow 2.x
* Scikitlearn 

### Dataset 

* We used Criteo dataset to do our evaluation. The corresponding trained model is wide and deep.
* The ```test_0.1_label_pred.pkl``` consists of 450,000 data samples, while ```test_label_pred.pkl``` is 10 times larger.
* Each pkl file contains a dict of which key is the epoch number and the value is also a dict (key is batch index and value is the corresponding label-pred pairs).
* Check ```label_on_device_auc_computation_main.py``` to see how to load the data.

### How to run

* ```python run_script_label_on_device_auc_cal.py```

Configurations:

```
number_clients_list = ["10", "1000"]
dp_noise_mechanisms = ["Laplace", "Laplace"]
dp_noise_eps_list = ["0.01", "0.005]
assign_client_id_ranking_skewed = True
repeat_times = 50
num_thresholds = [100]
```

* number_clients: number of clients, each client will have a roughly equal number of points. 
* dp_noise_eps: each dp epsilon budget for each value (i.e. TP) in the ququadruples (TP, FP, TN, FN). The total DP privacy budget epsilon = dp_noise_eps * num_thresholds * 4.
* dp_noise_mechanism: Laplace, Gaussian or RR (randomized responses)
* assign_client_id_ranking_skewed: True: Non-IID, False: IID
* num_thresholds: thresholds for calculating TP and FP
* repeat_times: repeat times for each setting, so that we can calculate corresponding mean and variance

Suppose, we would like to use Laplace mechanism with 1000 clients and total epsilon=1.0 (num_thresholds * 4 * dp_noise_eps) in the IID setting, our configurations will be like:

```
number_clients_list = ["1000"]
dp_noise_mechanisms = ["Laplace"]
dp_noise_eps_list = ["0.01]
assign_client_id_ranking_skewed = False
repeat_times = 50
num_thresholds = [100]
```


Suppose, we would like to use Laplace mechanism with 10 clients and total epsilon=2.0 in the Non-IID setting, our configurations will be like:

```
number_clients_list = ["10"]
dp_noise_mechanisms = ["Laplace"]
dp_noise_eps_list = ["0.005]
assign_client_id_ranking_skewed = True
repeat_times = 50
num_thresholds = [100]
```


Suppose, we would like to use Randomized Responses mechanism (baseline compared in our paper) with 100 clients and total epsilon=2.0 in the Non-IID setting, our configurations will be like:

```
number_clients_list = ["100"]
dp_noise_mechanisms = ["RR"]
dp_noise_eps_list = ["2.0]
assign_client_id_ranking_skewed = True
repeat_times = 50
num_thresholds = [100]
```

In our experiments, we divide the threshols in file `label_on_device_auc_computation_main.py` as:

```
thresholds_1 = list(np.linspace(0.0, 0.2, int(num_thresholds * 0.5)))
thresholds_2 = list(np.linspace(0.2, 0.5, int(num_thresholds * 0.25)))
thresholds_3 = list(np.linspace(0.5, 1.0, int(num_thresholds * 0.25)))
thresholds_list = (thresholds_1 + thresholds_2 + thresholds_3)[::-1]
```

You can also divide the thresholds uniformly as you need:

```
thresholds_list = list(np.linspace(0.0, 1.0, int(num_thresholds)))[::-1]
```


### Figures and logs

* You can check the Roc-AUC curve in the folder of `figures/roc_auc`. 
* You can check the logs of our previous results in the folder of `outputs`.

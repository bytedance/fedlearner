## Label Protection in FL

```FL_Label_Protection_FMNIST_Demo.py``` shows how we protect label informaiton in the settings of Federated Learning (FL).

We provide two protection methods in this demo:

* max norm alignment
* sumKL

### Usage 


#### Max norm alignment 

```python FL_Label_Protection_FMNIST_Demo.py --batch_size 600 --num_epochs 30 --max_norm```

After runing above codes, we can get some results as following:

> epoch 29, label leakage: baseline auc:1.0,  non_masking hidden layer: 1.0, masking hidden layer 1:0.5852134823799133, masking hidden layer 2: 0.5852072834968567
> epoch: 29, leak_auc_baseline_all: 1.000000238418579, leakage_auc_masked_hiddenlayer_1_all: 0.5841090083122253

It shows that we can decrease the label leakage AUC from 1.0 to 0.584. The model's performance does not change too much in the above experiments, since FMNIST is not a very complicated dataset. It's worth mentioning we call the function ```change_label``` to change it to a binary classification problem. 

The core of the max norm alignment algorithm is:

```Python
@tf.custom_gradient
def gradient_masking(x):
    # add scalar noise to align with the maximum norm in the batch
    def grad_fn(g):
        g_norm = tf.reshape(tf.norm(g, axis=1, keepdims=True), [-1, 1])
        max_norm = tf.reduce_max(g_norm)
        stds = tf.sqrt(tf.maximum(max_norm ** 2 / (g_norm ** 2 + 1e-32) - 1.0, 0.0))
        standard_gaussian_noise = tf.random.normal(shape = (tf.shape(g)[0], 1), mean=0.0, stddev=1.0)
        gaussian_noise = standard_gaussian_noise * stds
        res = g * (1 + gaussian_noise)
        return res
    return x, grad_fn
```

Please refer to the demo to check how to use add the customized function to prevent label leakage.

####

```python FL_Label_Protection_FMNIST_Demo.py --batch_size 600 --num_epochs 30 --sumKL```

If you would like to see the detailed prints, please consider to use the arguments ```debug```:

```python FL_Label_Protection_FMNIST_Demo.py --batch_size 600 --num_epochs 30 --sumKL --debug```


After runing above codes, we can get some results as following:

* sumKL_threshold = 0.64

> epoch: 4, leak_auc baseline_all: 0.9999999403953552, masked_HL_1_all: 0.6167622804641724
> baseline leak_auc:1.0, non_masking: 1.0
> masking L1:0.6150113940238953, masking L2: 0.6152912974357605
> test loss: 0.08250142087936402, test auc: 0.7901284098625183


You can vary the value of ```sumKL_threshold``` in the code to achieve the different trade-offs between protection and performance. 

To run with a lower Tensorflow version such as (tf 1.x), please consier to use ```tf.py_func```.

* Use the function ```compute_lambdas_tf1``` instead of ```compute_lambdas_tf2```

We also provide a tf 2.x version for the ```solver.py``` as ```gradient_noise_solver_tf2.py```.

We have filed patents for both protection methods. 

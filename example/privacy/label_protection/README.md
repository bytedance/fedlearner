## Label Protection in FL

```FL_Label_Protection_FMNIST_Demo.py``` shows how we protect label informaiton in the settings of Federated Learning (FL).

### Usage 

```python FL_Label_Protection_FMNIST_Demo.py --batch_size 600 --num_epochs 30```

After runing above codes, we can get some results as following:

> epoch 29, label leakage: baseline auc:1.0,  non_masking hidden layer: 1.0, masking hidden layer 1:0.5852134823799133, masking hidden layer 2: 0.5852072834968567
> epoch: 29, leak_auc_baseline_all: 1.000000238418579, leakage_auc_masked_hiddenlayer_1_all: 0.5841090083122253

It shows that we can decrease the label leakage AUC from 1.0 to 0.584. The model's performance does not change too much in the above experiments, since FMNIST is not a very complicated dataset. It's worth mentioning we call the function ```change_label``` to change it to a binary classification problem. 

### Our Main Contribution 

The core of the algorithm is:

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

We have filed a patent for the above algorithm on 6 July 2020. 

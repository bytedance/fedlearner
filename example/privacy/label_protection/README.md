## Label Protection in FL

```FL_Label_Protection_FMNIST_Demo.py``` shows how we protect label informaiton in the settings of Federated Learning (FL).

We provide two protection methods in this demo:

* max norm alignment
* sumKL minimzation 

More details can be viewed at our technical report. 

### Usage 

#### Requirements

* Python 3.x
* Tensorflow 1.x and 2.x 

In this demo, we use Tensorflow 2.x.

#### Max Norm Alignment 

```python FL_Label_Protection_FMNIST_Demo.py --batch_size 600 --num_epochs 30 --max_norm```

After runing above codes, we can get some results as following:

> epoch 29, label leakage: baseline auc:1.0,  non_masking hidden layer: 1.0, masking hidden layer 1:0.5852134823799133, masking hidden layer 2: 0.5852072834968567
> epoch: 29, leak_auc_baseline_all: 1.000000238418579, leakage_auc_masked_hiddenlayer_1_all: 0.5841090083122253

It shows that we can decrease the label leakage AUC from 1.0 to 0.584. The model's performance does not change too much in the above experiments, since FMNIST is not a very complicated dataset. It's worth mentioning we call the function ```change_label``` to change it to a binary classification problem. 

The core of the max norm alignment algorithm (work for both tf 1.x and tf 2.x) is:

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

#### SumKL Minimization 

```python FL_Label_Protection_FMNIST_Demo.py --batch_size 600 --num_epochs 10 --sumKL```

If you would like to see the detailed prints, please consider to use the arguments ```debug```:

```python FL_Label_Protection_FMNIST_Demo.py --batch_size 600 --num_epochs 30 --sumKL --debug```


After runing above codes, we can get some results as following:

* sumKL_threshold = 0.64

> epoch: 4, leak_auc baseline_all: 0.9999999403953552, masked_HL_1_all: 0.6167622804641724
> baseline leak_auc:1.0, non_masking: 1.0
> masking L1:0.6150113940238953, masking L2: 0.6152912974357605
> test loss: 0.08250142087936402, test auc: 0.7901284098625183


You can vary the value of ```sumKL_threshold``` in the code to achieve the different trade-offs between protection and performance. 

To run with a lower Tensorflow version such as (tf 1.x), please consier:

*  use ```tf.py_func```
* Use the function ```compute_lambdas_tf1``` instead of ```compute_lambdas_tf2```


A workable tf 1.x code snippet is:

```python
from solver import solve_isotropic_covariance, symKL_objective 
@tf.custom_gradient
def KL_gradient_perturb(x):
    uv_choice = "uv" #"uv"
    init_scale = 1.0

    p_frac='pos_frac'
    dynamic=True
    error_prob_lower_bound=None
    sumKL_threshold= 0.25 #0.25 #0.81 #0.64#0.16 #0.64

    if dynamic and (error_prob_lower_bound is not None):
        sumKL_threshold = (2 - 4 * error_prob_lower_bound)**2
    elif dynamic:
        print('using sumKL_threshold', sumKL_threshold)     

    global _Batch_Labels
    batch_y = tf.reshape(tf.cast(_Batch_Labels, dtype = tf.float32), [-1, 1])

    def grad_fn(g):
        # start = time.time()
        y = batch_y
        # pos_g = g[y==1]
        pos_g = tf.boolean_mask(g, tf.tile(tf.cast(y, dtype=tf.int32), [1, tf.shape(g)[1]]))
        pos_g = tf.reshape(pos_g, [-1, tf.shape(g)[1]])

        pos_g_mean = tf.math.reduce_mean(pos_g, axis=0, keepdims=True) # shape [1, d]
        pos_coordinate_var = tf.reduce_mean(tf.math.square(pos_g - pos_g_mean), axis=0) # use broadcast
        
        # neg_g = g[y==0]
        neg_g = tf.boolean_mask(g, tf.tile(1 - tf.cast(y, dtype=tf.int32), [1, tf.shape(g)[1]]))
        neg_g = tf.reshape(neg_g, [-1, tf.shape(g)[1]])

        neg_g_mean = tf.math.reduce_mean(neg_g, axis=0, keepdims=True) # shape [1, d]
        neg_coordinate_var = tf.reduce_mean(tf.math.square(neg_g - neg_g_mean), axis=0)

        avg_pos_coordinate_var = tf.reduce_mean(pos_coordinate_var)
        avg_neg_coordinate_var = tf.reduce_mean(neg_coordinate_var)
        g_diff = pos_g_mean - neg_g_mean

        g_diff_norm = tf.norm(tensor=g_diff)
        if uv_choice == 'uv':
            u = avg_neg_coordinate_var
            v = avg_pos_coordinate_var
        elif uv_choice == 'same':
            u = (avg_neg_coordinate_var + avg_pos_coordinate_var) / 2.0
            v = (avg_neg_coordinate_var + avg_pos_coordinate_var) / 2.0
        elif uv_choice == 'zero':
            u, v = 0.0, 0.0
        d = tf.cast(tf.shape(g)[1], dtype=tf.float32)
        if p_frac == 'pos_frac':
            p = tf.math.reduce_mean(y)
        else:
            p = float(p_frac)

        scale = init_scale
        g_norm_square = g_diff_norm ** 2

        def print_tensor(pos_g_mean, neg_g_mean, g_diff):
            logging.info("gradient pos_g_mean: {}, neg_g_mean: {}".format(np.mean(pos_g_mean), np.mean(neg_g_mean)))
            logging.info("gradient pos_g_max: {}, neg_g_max: {}".format(np.amax(pos_g_mean), np.amax(neg_g_mean)))
            logging.info("gradient pos_g_min: {}, neg_g_min: {}".format(np.amin(pos_g_mean), np.amin(neg_g_mean)))
            logging.info("gradient pos_g_norm: {}, neg_g_norm: {}".format(np.linalg.norm(pos_g_mean), np.linalg.norm(neg_g_mean)))
            logging.info("gradient g_diff_mean: {}, g_diff_min: {}, g_diff_max: {}, g_diff_norm: {}".format(np.mean(g_diff), np.amin(g_diff), np.amax(g_diff), np.linalg.norm(g_diff)))
            
        def compute_lambdas(u, v, scale, d, g_norm_square, p, sumKL_threshold, pos_g_mean, neg_g_mean, g_diff):
            
            print_tensor(pos_g_mean, neg_g_mean, g_diff)
            u = np.float32(np.asscalar(u))
            v = np.float32(np.asscalar(v))
            scale = np.float32(np.asscalar(scale))
            d = np.float32(np.asscalar(d))
            g_norm_square = np.float32(np.asscalar(g_norm_square))
            p = np.float32(np.asscalar(p))
            sumKL_threshold = np.float32(np.asscalar(sumKL_threshold))

            kl_obj = symKL_objective(np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(0.0), u, v, d, g_norm_square)
            logging.info("u: {}, v:{}, scale:{}, d:{}, g_diff_norm_square:{}, p:{}, sumKL_threshold:{}, current_kl: {}".format(u, v, scale, d, g_norm_square, p, sumKL_threshold, kl_obj))

            if kl_obj < sumKL_threshold:
                logging.info("lam10: {}, lam20: {}, lam11:{}, lam21:{}, sumKL:{}".format(0.0, 0.0, 0.0, 0.0, kl_obj))
                return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(0.0), kl_obj

            lam10, lam20, lam11, lam21 = None, None, None, None
            start = time.time()
            while True:
                P = scale * g_norm_square
                lam10, lam20, lam11, lam21, sumKL = solve_isotropic_covariance(u=u,
                                                                        v=v,
                                                                        d=d,
                                                                        g_norm_square=g_norm_square,
                                                                        p=p,
                                                                        P=P,
                                                                        lam10_init=lam10,
                                                                        lam20_init=lam20,
                                                                        lam11_init=lam11,
                                                                        lam21_init=lam21)
                # logging.info('scale: {}, sumKL: {}, P:{}, type_scale: {}, type_sumKL: {}, type_P:{}'.format(scale, sumKL, P, type(scale), type(sumKL), type(P)))
                if not dynamic or sumKL <= sumKL_threshold:
                    break

                scale *= np.float32(1.5) # loosen the power constraint

            logging.info('solve_isotropic_covariance solving time: {}'.format(time.time() - start))
            
            return lam10, lam20, lam11, lam21, sumKL
        
        lam10, lam20, lam11, lam21, sumKL = tf.py_func(compute_lambdas, [u, v, scale, d, g_norm_square, p, sumKL_threshold,pos_g_mean, neg_g_mean, g_diff], [tf.float32, tf.float32, tf.float32, tf.float32, tf.float32])
        lam10, lam20, lam11, lam21, sumKL= tf.reshape(lam10, shape=[1]), tf.reshape(lam20, shape=[1]), tf.reshape(lam11, shape=[1]), tf.reshape(lam21, shape=[1]), tf.reshape(sumKL, shape=[1]),

        perturbed_g = g
        y_float = tf.cast(y, dtype=tf.float32)
        
        noise_1 = tf.reshape(tf.multiply(x=tf.random.normal(shape=tf.shape(y)), y=y_float), shape=(-1, 1)) * g_diff * (tf.math.sqrt(tf.math.abs(lam11-lam21))/g_diff_norm)
        noise_1 = tf.debugging.check_numerics(noise_1, "noise_1 ERROR", name="noise_1_debugging")
        
        noise_2 = tf.random.normal(shape=tf.shape(g)) * tf.reshape(y_float, shape=(-1, 1)) * tf.math.sqrt(tf.math.maximum(lam21, 0.0))
        noise_2 = tf.debugging.check_numerics(noise_2, "noise_2 ERROR", name="noise_2_debugging")
        
        noise_3 = tf.reshape(tf.multiply(x=tf.random.normal(shape=tf.shape(y)), y=1-y_float), shape=(-1, 1)) * g_diff * (tf.math.sqrt(tf.math.abs(lam10-lam20))/g_diff_norm)
        noise_3 = tf.debugging.check_numerics(noise_3, "noise_3 ERROR", name="noise_3_debugging")
        
        noise_4 = tf.random.normal(shape=tf.shape(g)) * tf.reshape(1-y_float, shape=(-1, 1)) * tf.math.sqrt(tf.math.maximum(lam20, 0.0))
        noise_4 = tf.debugging.check_numerics(noise_4, "noise_3 ERROR", name="noise_4_debugging")

        perturbed_g += (noise_1 + noise_2 + noise_3 + noise_4)         
        perturbed_g = tf.debugging.check_numerics(perturbed_g, "perturbed_g ERROR", name="perturbed_g_debugging")

        return perturbed_g
    return x, grad_fn
```

The code snippet to compute lambdas can be viewed here:

```python
import math
import random
import numpy as np 
OBJECTIVE_EPSILON = np.float32(1e-16)
CONVEX_EPSILON = np.float32(1e-20)
NUM_CANDIDATE = 1
import logging

import sys
sys.setrecursionlimit(5000000)

def symKL_objective(lam10, lam20, lam11, lam21, u, v, d, g_norm_square):
    objective = np.float32((d - np.float32(1)) * (lam20 + u) / (lam21 + v) \
                + (d - np.float32(1)) * (lam21 + v) / (lam20 + u) \
                    + (lam10 + u + g_norm_square) / (lam11 + v) \
                        + (lam11 + v + g_norm_square) / (lam10 + u))
    
    # logging.info("symKL_objective, objective: {}, type: {}".format(objective, type(objective)))
    return objective


def symKL_objective_zero_uv(lam10, lam11, g_norm_square):
    objective = np.float32((lam10 + g_norm_square) / lam11 \
                    + (lam11 + g_norm_square) / lam10)
    # logging.info("symKL_objective_zero_uv, objective: {}, type: {}".format(objective, type(objective)))
    return objective


def solve_isotropic_covariance(u, v, d, g_norm_square, p, P,
                               lam10_init=None, lam20_init=None,
                               lam11_init=None, lam21_init=None):
    """ return the solution to the optimization problem
        Args:
        u ([type]): [the coordinate variance of the negative examples]
        v ([type]): [the coordinate variance of the positive examples]
        d ([type]): [the dimension of activation to protect]
        g_norm_square ([type]): [squared 2-norm of g_0 - g_1, i.e. \|g^{(0)} - g^{(1)}\|_2^2]
        P ([type]): [the power constraint value]
    """
    if u == np.float32(0.0) and v == np.float32(0.0):
        return solve_zero_uv(g_norm_square=g_norm_square, p=p, P=P)

    # logging.info("solve_isotropic_covariance, uv!=0")
    ordering = [0, 1, 2]
    random.shuffle(x=ordering)

    solutions = []
    if u <= v:
        # logging.info("solve_isotropic_covariance, u<=v")
        for i in range(NUM_CANDIDATE):
            if i % 3 == ordering[0]:
                # print('a')
                if lam20_init: # if we pass an initialization
                    lam20 = lam20_init
                    # print('here')
                else:
                    lam20 = np.float32(random.random() * P / (np.float32(1.0)-p) / d)
                lam10, lam11 = None, None
                # print('lam21', lam21)
            elif i % 3 == ordering[1]:
                # print('b')
                if lam11_init:
                    lam11 = lam11_init
                else:
                    lam11 = np.float32(random.random() * P / p)
                lam10, lam20 = None, None
                # print('lam11', lam11)
            else:
                # print('c')
                if lam10_init:
                    lam10 = lam10_init
                else:
                    lam10 = np.float32(random.random() * P / (np.float32(1.0)-p))
                lam11, lam20 = None, None
                # print('lam10', lam10)
            # logging.info("solve_isotropic_covariance, u<=v_iter_{}, lam10: {}, lam20: {}, lam11: {}, type_lam10: {}, type_lam20: {}, type_lam11: {}".format(i, lam10, lam20, lam11, type(lam10), type(lam20), type(lam11)))
            solutions.append(solve_small_neg(u=u,v=v,d=d,g_norm_square=g_norm_square,p=p,P=P, lam10=lam10, lam11=lam11, lam20=lam20))
        
    else:
        # logging.info("solve_isotropic_covariance, u>v")
        for i in range(NUM_CANDIDATE):
            if i % 3 == ordering[0]:
                if lam21_init:
                    lam21 = lam21_init
                else:
                    lam21 = np.float32(random.random() * P / p / d)
                lam10, lam11 = None, None
                # print('lam21', lam21)
            elif i % 3 == ordering[1]:
                if lam11_init:
                    lam11 = lam11_init
                else:
                    lam11 = np.float32(random.random() * P / p)
                lam10, lam21 = None, None
                # print('lam11', lam11)
            else:
                if lam10_init:
                    lam10 = lam10_init
                else:
                    lam10 = np.float32(random.random() * P / (1-p))
                lam11, lam21 = None, None
                # print('lam10', lam10)
            # logging.info("solve_isotropic_covariance, u>v_iter_{}, lam10: {}, lam21: {}, lam11: {}, type_lam10: {}, type_lam21: {}, type_lam11: {}".format(i, lam10, lam21, lam11, type(lam10), type(lam21), type(lam11)))
            solutions.append(solve_small_pos(u=u,v=v,d=d,g_norm_square=g_norm_square,p=p,P=P, lam10=lam10, lam11=lam11, lam21=lam21))

    # print(solutions)
    # logging.info("solve_isotropic_covariance, solutions: {}, len: {}".format(solutions, len(solutions)))
    lam10, lam20, lam11, lam21, objective = min(solutions, key=lambda x: x[-1])
    # logging.info("solve_isotropic_covariance, lam10: {}, lam20: {}, lam21: {}, lam11: {}, type_lam10: {}, type_lam21: {}, type_lam11: {}, type_lam20: {}".format(lam10, lam20, lam21, lam11, type(lam10), type(lam21), type(lam11), type(lam20)))

    # print('sum', p * lam11 + p*(d-1)*lam21 + (1-p) * lam10 + (1-p)*(d-1)*lam20)

    return (lam10, lam20, lam11, lam21, objective)


def solve_zero_uv(g_norm_square, p, P):
    C = P
    E = np.float32(math.sqrt((C + (np.float32(1.0) - p) * g_norm_square) / (C + p * g_norm_square)))
    tau = np.float32(max((P / p) / (E + (np.float32(1.0) - p)/p), np.float32(0.0)))
    # print('tau', tau)
    # logging.info("solve_zero_uv, C: {}, E: {}, tau: {}, type_C: {}, type_E: {}, type_tau: {}".format(C, E, tau, type(C), type(E), type(tau)))
    if 0 <= tau and tau <= P / (np.float32(1.0) - p):
        # print('A')
        lam10 = tau
        lam11 = np.float32(max(P / p - (np.float32(1.0) - p) * tau / p, np.float32(0.0)))
        # logging.info("solve_zero_uv, branch_1, lam10: {}, lam11: {}, type_lam10: {}, type_lam11:{}".format(lam10, lam11, type(lam10), type(lam11)))
    else:
        # print('B')
        lam10_case1, lam11_case1 = np.float32(0.0), max(P/p, np.float32(0.0))
        lam10_case2, lam11_case2 = np.float32(max(P/(np.float32(1.0)-p), np.float32(0.0))), np.float32(0.0)
        objective1 = symKL_objective_zero_uv(lam10=lam10_case1,lam11=lam11_case1,
                                             g_norm_square=g_norm_square)
        objective2 = symKL_objective_zero_uv(lam10=lam10_case2,lam11=lam11_case2,
                                             g_norm_square=g_norm_square)
        if objective1 < objective2:
            lam10, lam11 = lam10_case1, lam11_case1
        else:
            lam10, lam11 = lam10_case2, lam11_case2

        # logging.info("solve_zero_uv, branch_2, lam10: {}, lam11: {}, type_lam10: {}, type_lam11:{}".format(lam10, lam11, type(lam10), type(lam11)))

    objective = symKL_objective_zero_uv(lam10=lam10, lam11=lam11, g_norm_square=g_norm_square)
    # logging.info("solve_zero_uv, objective {},  type: {}".format(objective, type(objective)))

    # here we subtract d = 1 because the distribution is essentially one-dimensional
    return (lam10, np.float32(0.0), lam11, np.float32(0.0), np.float32(np.float32(0.5) * objective - np.float32(1.0)))


def solve_small_neg(u, v, d, g_norm_square, p, P, lam10=None, lam20=None, lam11=None):
    """[When u < v]
    """
    # some intialization to start the alternating optimization
    LAM21 = np.float32(0.0)
    i = 0
    objective_value_list = []

    if lam20:
        ordering = [0, 1, 2]
    elif lam11:
        ordering = [1, 0, 2]
    else:
        ordering = [1, 2, 0]
    # print(ordering)

    while True:
        if i % 3 == ordering[0]: # fix lam20
            D = np.float32(P - (np.float32(1.0) - p) * (d - np.float32(1.0)) * lam20)
            C = np.float32(D + p * v + (np.float32(1.0) - p) * u)

            E = np.float32(math.sqrt((C + (np.float32(1.0) - p) * g_norm_square) / (C + p * g_norm_square)))
            tau = np.float32(max((D / p + v - E * u) / (E + (np.float32(1.0) - p)/p), np.float32(0.0)))
            # print('tau', tau)
            if lam20 <= tau and tau <= np.float32(P / (np.float32(1.0) - p) - (d - np.float32(1.0)) * lam20):
                # print('A')
                lam10 = tau
                lam11 = np.float32(max(D / p - (np.float32(1.0) - p) * tau / p, np.float32(0.0)))
            else:
                # print('B')
                lam10_case1, lam11_case1 = lam20, np.float32(max(P/p - (np.float32(1.0)-p)*d*lam20/p, np.float32(0.0)))
                lam10_case2, lam11_case2 = np.float32(max(P/(np.float32(1.0)-p) - (d-np.float32(1.0))*lam20, np.float32(0.0))), np.float32(0.0)
                objective1 = symKL_objective(lam10=lam10_case1,lam20=lam20,lam11=lam11_case1,lam21=LAM21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square)
                objective2 = symKL_objective(lam10=lam10_case2,lam20=lam20,lam11=lam11_case2,lam21=LAM21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square)
                if objective1 < objective2:
                    lam10, lam11 = lam10_case1, lam11_case1
                else:
                    lam10, lam11 = lam10_case2, lam11_case2

        elif i % 3 == ordering[1]: # fix lam11
            D = np.float32(max((P - p * lam11) / (np.float32(1.0)- p), np.float32(0.0)))
            f = lambda x: symKL_objective(lam10=D - (d-np.float32(1.0))*x, lam20=x, lam11=lam11, lam21=LAM21,
                                          u=u, v=v, d=d, g_norm_square=g_norm_square)
            # f_prime = lambda x: (d-1)/v - (d-1)/(lam11+v) - (d-1)*v/((x+u)**2) + (lam11 + v + g)*(d-1)/((D-(d-1)*x+u)**2)
            f_prime = lambda x: (d-np.float32(1.0))/v - (d-np.float32(1.0))/(lam11+v) - (d-np.float32(1.0))/(x+u)*(v/(x+u)) + (lam11 + v + g_norm_square)/(D-(d-np.float32(1.0))*x+u) * ((d-np.float32(1.0))/(D-(d-np.float32(1.0))*x+u))
            # print('D/d', D/d)
            lam20 = convex_min_1d(xl=np.float32(0.0), xr=D/d, f=f, f_prime=f_prime)
            lam10 = np.float32(max(D - (d-np.float32(1.0)) * lam20, np.float32(0.0)))

        else: # fix lam10
            D = np.float32(max(P - (np.float32(1.0) - p) * lam10, np.float32(0.0))) # avoid negative due to numerical error
            f = lambda x: symKL_objective(lam10=lam10, lam20=x, lam11=D/p - (np.float32(1.0)-p)*(d-np.float32(1.0))*x/p, lam21=LAM21,
                                          u=u, v=v, d=d, g_norm_square=g_norm_square)
            # f_prime = lambda x: (d-1)/v - (1-p)*(d-1)/(lam10 + u)/p - (d-1)*v/((x+u)**2) + (lam10+u+g)*(1-p)*(d-1)/p/((D/p - (1-p)*(d-1)*x/p + v)**2)
            f_prime = lambda x: (d-np.float32(1.0))/v - (np.float32(1.0)-p)*(d-np.float32(1.0))/(lam10 + u)/p - (d-np.float32(1.0))/(x+u)*(v/(x+u)) + (lam10+u+g_norm_square)/(D/p - (np.float32(1.0)-p)*(d-np.float32(1.0))*x/p + v) * (1-p) * (d-1) / p / (D/p - (1-p)*(d-1)*x/p + v)
            # print('lam10', 'D/((1-p)*(d-1)', lam10, D/((1-p)*(d-1)))
            lam20 = convex_min_1d(xl=np.float32(0.0), xr=min(D/((np.float32(1.0)-p)*(d-np.float32(1.0))), lam10), f=f, f_prime=f_prime)
            lam11 = np.float32(max(D/p - (np.float32(1.0)-p)*(d-np.float32(1.0))*lam20/p, np.float32(0.0)))

        # if lam10 <0 or lam20 < 0 or lam11 <0 or LAM21 <0: # check to make sure no negative values
        #     assert False, i

        objective_value_list.append(symKL_objective(lam10=lam10,lam20=lam20,lam11=lam11,lam21=LAM21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square))
        # print(i)
        # print(objective_value_list[-1])
        # print(lam10, lam20, lam11, LAM21, objective_value_list[-1])
        # print('sum', p * lam11 + p*(d-1)*LAM21 + (1-p) * lam10 + (1-p)*(d-1)*lam20)
        # logging.info("solve_small_neg, iter: {}, objective_value_list[-1]: {}".format(i, objective_value_list[-1]))
        if (i>=3 and objective_value_list[-4] - objective_value_list[-1] < OBJECTIVE_EPSILON) or i >= 100:
            # print(i)
            # logging.info("solve_small_neg, iter: {}, terminated".format(i))
            return (lam10, lam20, lam11, LAM21, np.float32(0.5) * objective_value_list[-1] - d)

        i += 1


def solve_small_pos(u, v, d, g_norm_square, p, P, lam10=None, lam11=None, lam21=None):
    """[When u > v] lam20 = 0.0 and will not change throughout the optimization
    """
    # some intialization to start the alternating optimization
    LAM20 = np.float32(0.0)
    i = 0
    objective_value_list = []
    if lam21:
        ordering = [0, 1, 2]
    elif lam11:
        ordering = [1, 0, 2]
    else:
        ordering = [1, 2, 0]
    # print(ordering)
    while True:
        if i % 3 == ordering[0]: # fix lam21
            D = np.float32(P - p * (d - np.float32(1.0)) * lam21)
            C = np.float32(D + p * v + (np.float32(1.0) - p) * u)

            E = np.float32(math.sqrt((C + (np.float32(1.0) - p) * g_norm_square) / (C + p * g_norm_square)))
            tau = np.float32(max((D / p + v - E * u) / (E + (np.float32(1.0) - p)/p), np.float32(0.0)))
            # print('tau', tau)
            if np.float32(0.0) <= tau and tau <= (P - p*d*lam21)/(np.float32(1.0)-p):
                # print('A')
                lam10 = tau
                lam11 = np.float32(max(D / p - (np.float32(1.0) - p) * tau / p, np.float32(0.0)))
            else:
                # print('B')
                lam10_case1, lam11_case1 = np.float32(0), np.float32(max(P/p - (d-np.float32(1.0))*lam21, np.float32(0.0)))
                lam10_case2, lam11_case2 =  np.float32(max((P - p*d*lam21)/(np.float32(1.0)-p), np.float32(0.0))), lam21
                objective1 = symKL_objective(lam10=lam10_case1,lam20=LAM20,lam11=lam11_case1,lam21=lam21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square)
                objective2 = symKL_objective(lam10=lam10_case2,lam20=LAM20,lam11=lam11_case2,lam21=lam21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square)
                if objective1 < objective2:
                    lam10, lam11 = lam10_case1, lam11_case1
                else:
                    lam10, lam11 = lam10_case2, lam11_case2
            # logging.info("solve_small_pos, branch: 0, lam10: {}, lam11: {}".format(lam10, lam11))
        elif i % 3 == ordering[1]: # fix lam11
            D =  np.float32(max(P - p * lam11, np.float32(0.0)))
            f = lambda x: symKL_objective(lam10=(D - p*(d-1)*x)/(np.float32(1.0)-p), lam20=LAM20, lam11=lam11, lam21=x,
                                          u=u, v=v, d=d, g_norm_square=g_norm_square)
            # f_prime = lambda x: (d-1)/u - p*(d-1)/(lam11+v)/(1-p) - (d-1)*u/((x+v)**2) + (lam11 + v + g)*p*(d-1)/(1-p)/(((D - p*(d-1)*x)/(1-p) + u)**2)
            f_prime = lambda x: (d-np.float32(1.0))/u - p*(d-np.float32(1.0))/(lam11+v)/(np.float32(1.0)-p) - (d-1)/(x+v)*(u/(x+v)) + (lam11 + v + g_norm_square) / ((D - p*(d-1)*x)/(np.float32(1.0)-p) + u) * p * (d-np.float32(1.0)) / (np.float32(1.0)-p) /((D - p*(d-np.float32(1.0))*x)/(np.float32(1.0)-p) + u)

            # print('lam11', 'D/p/(d-1)', lam11, D/p/(d-1))
            lam21 = convex_min_1d(xl=np.float32(0.0), xr=min(D/p/(d-np.float32(1.0)), lam11), f=f, f_prime=f_prime)
            lam10 =  np.float32(max((D - p*(d-1)*lam21)/(np.float32(1.0)-p), np.float32(0.0)))
            # logging.info("solve_small_pos, branch: 1, lam10: {}, lam21: {}".format(lam10, lam21))

        else: # fix lam10
            D =  np.float32(max((P - (1 - p) * lam10) / p, np.float32(0.0)))
            f = lambda x: symKL_objective(lam10=lam10, lam20=LAM20, lam11=D - (d-np.float32(1.0))*x, lam21=x,
                                          u=u, v=v, d=d, g_norm_square=g_norm_square)
            # f_prime = lambda x: (d-1)/u - (d-1)/(lam10+u) - (d-1)*u/((x+v)**2) + (lam10 + u + g)*(d-1)/((D-(d-1)*x+v)**2)
            f_prime = lambda x: (d-np.float32(1.0))/u - (d-np.float32(1.0))/(lam10+u) - (d-np.float32(1.0))/(x+v)*(u/(x+v)) + (lam10 + u + g_norm_square)/(D-(d-np.float32(1.0))*x+v) * (d-np.float32(1.0)) / (D-(d-np.float32(1.0))*x+v)
            # def f_prime(x):
            #     print('x', x)
            #     print('d, u, v, g', d, u, v, g)
            #     print('(d-1)/u', (d-1)/u)
            #     print('(d-1)/(lam10+u)', (d-1)/(lam10+u))
            #     print('(d-1)*u/((x+v)**2)', (d-1)*u/((x+v)**2))
            #     print('(lam10 + u + g)*(d-1)/((D-(d-1)*x+v)**2)', (lam10 + u + g)*(d-1)/((D-(d-1)*x+v)**2))

            #     return (d-1)/u - (d-1)/(lam10+u) - (d-1)*u/((x+v)**2) + (lam10 + u + g)*(d-1)/((D-(d-1)*x+v)**2)
            # print('D/d', D/d)
            lam21 = convex_min_1d(xl=np.float32(0.0), xr=D/d, f=f, f_prime=f_prime)
            lam11 = np.float32(max(D - (d-np.float32(1.0)) * lam21, np.float32(0.0)))
            # logging.info("solve_small_pos, branch: 2, lam11: {}, lam21: {}".format(lam11, lam21))

        # if lam10 <0 or LAM20 <0 or lam11 <0 or lam21 <0:
        #     assert False, i

        objective_value_list.append(symKL_objective(lam10=lam10,lam20=LAM20,lam11=lam11,lam21=lam21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square))
        # print(i)
        # print(objective_value_list[-1])
        # print(lam10, LAM20, lam11, lam21)
        # print('sum', p * lam11 + p*(d-1)*lam21 + (1-p) * lam10 + (1-p)*(d-1)*LAM20)
        logging.info("solve_small_pos, iter: {}, objective_value_list[-1]: {}".format(i, objective_value_list[-1]))

        if (i>=3 and objective_value_list[-4] - objective_value_list[-1] < OBJECTIVE_EPSILON) or i >= 100:
            # logging.info("solve_small_pos, iter: {}, terminated".format(i))
            return (lam10, LAM20, lam11, lam21,  np.float32(np.float32(0.5) * objective_value_list[-1] - d))

        i += 1


def convex_min_1d(xl, xr, f, f_prime):
    # print('xl, xr', xl, xr)
    # assert xr <= np.float32(1e5)
    # assert xl <= xr, (xl, xr)
    xm = np.float32((xl + xr) / np.float32(2.0))
    # print('xl', xl, f(xl), f_prime(xl))
    # print('xr', xr, f(xr), f_prime(xr))
    # logging.info("convex_min_1d, xl: {}, xr: {}, xm: {}, type_xl: {}, type_xr: {}, type_xm: {}".format(xl, xr, xm, type(xl), type(xr), type(xm)))
    if abs(xl - xr) <= CONVEX_EPSILON or abs(xl - xm) <= CONVEX_EPSILON or abs(xm - xr) <= CONVEX_EPSILON:
        return np.float32(min((f(x), x) for x in [xl, xm, xr])[1])
    if f_prime(xl) <=0 and f_prime(xr) <= 0:
        return np.float32(xr)
    elif f_prime(xl) >=0 and f_prime(xr) >= 0:
        return np.float32(xl)
    if f_prime(xm) > 0:
        return convex_min_1d(xl=xl, xr=xm, f=f, f_prime=f_prime)
    else:
        return convex_min_1d(xl=xm, xr=xr, f=f, f_prime=f_prime)


def small_neg_problem_string(u, v, d, g_norm_square, p, P):
    return 'minimize ({2}-1)*(z + {0})/{1} + ({2}-1)*{1}/(z+{0})+(x+{0}+{3})/(y+{1}) + (y+{1}+{3})/(x+{0}) subject to x>=0, y>=0, z>=0, z<=x, {4}*y+(1-{4})*x+(1-{4})*({2}-1)*z={5}'.format(u,v,d,g_norm_square,p,P)

def small_pos_problem_string(u, v, d, g_norm_square, p, P):
    return 'minimize ({2}-1)*{0}/(z+{1}) + ({2}-1)*(z + {1})/{0} + (x+{0}+{3})/(y+{1}) + (y+{1}+{3})/(x+{0}) subject to x>=0, y>=0, z>=0, z<=y, {4}*y+(1-{4})*x+{4}*({2}-1)*z={5}'.format(u,v,d,g_norm_square,p,P)

def zero_uv_problem_string(g_norm_square, p, P):
    return 'minimize (x+{0})/y + (y+{0})/x subject to x>=0, y>=0, {1}*y+(1-{1})*x={2}'.format(g_norm_square,p,P)

if __name__ == '__main__':
    import random
    import time
    from collections import Counter

    test_neg = False
    
    u = 3.229033590534426e-15
    v = 3.0662190349955726e-15
    d = 128.0
    g_norm_square = 5.015613264502392e-10
    p = 0.253936767578125
    P = 2328365.0213796967

    print('u={0},v={1},d={2},g={3},p={4},P={5}'.format(u,v,d,g_norm_square,p,P))
    start = time.time()
    lam10, lam20, lam11, lam21, sumKL = solve_isotropic_covariance(u=u, v=v, d=d, g_norm_square=g_norm_square, p=p, P=P)
    print(lam10, lam20, lam11, lam21, sumKL)
    print('time', time.time() - start)
    if u < v:
        print(small_neg_problem_string(u=u,v=v,d=d,g_norm_square=g_norm_square,p=p,P=P))
    else:
        print(small_pos_problem_string(u=u,v=v,d=d,g_norm_square=g_norm_square,p=p,P=P))

    start = time.time()
    print(solve_isotropic_covariance(u=u, v=v, d=d, g_norm_square=g_norm_square, p=p, P=P + 10, 
                                     lam10_init=lam10, lam20_init=lam20,
                                     lam11_init=lam11, lam21_init=lam21))
    print('time', time.time() - start) 
```

### Acknowledgements 

We have filed patents for both protection methods. 

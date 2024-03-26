import math
import random
import numpy as np
import tensorflow.compat.v1 as tf
import logging
import time
import sys

sys.setrecursionlimit(100000)

OBJECTIVE_EPSILON = np.float32(1e-16)
CONVEX_EPSILON = np.float32(1e-20)
NUM_CANDIDATE = 1
ZERO_REPLACE = 1e-3

@tf.function
def KL_gradient_perturb(g, batch_y, sumKL_threshold=0.25):
    uv_choice = "uv"  # "uv"
    init_scale = 1.0

    p_frac = 'pos_frac'
    dynamic = True
    error_prob_lower_bound = None
    # sumKL_threshold= 0.25 #0.25 #0.81 #0.64#0.16 #0.64

    if dynamic and (error_prob_lower_bound is not None):
        sumKL_threshold = (2 - 4 * error_prob_lower_bound) ** 2
    # elif dynamic:
    #     print('using sumKL_threshold', sumKL_threshold)

        # start = time.time()
    y = tf.reshape(tf.cast(batch_y, dtype=tf.float32), [-1, 1])
    # pos_g = g[y==1]
    pos_g = tf.boolean_mask(g, tf.tile(tf.cast(y, dtype=tf.int32), [1, tf.shape(g)[1]]))
    pos_g = tf.reshape(pos_g, [-1, tf.shape(g)[1]])

    pos_g_mean = tf.math.reduce_mean(pos_g, axis=0, keepdims=True)  # shape [1, d]
    pos_coordinate_var = tf.reduce_mean(tf.math.square(pos_g - pos_g_mean), axis=0)  # use broadcast

    # neg_g = g[y==0]
    neg_g = tf.boolean_mask(g, tf.tile(1 - tf.cast(y, dtype=tf.int32), [1, tf.shape(g)[1]]))
    neg_g = tf.reshape(neg_g, [-1, tf.shape(g)[1]])

    neg_g_mean = tf.math.reduce_mean(neg_g, axis=0, keepdims=True)  # shape [1, d]
    neg_coordinate_var = tf.reduce_mean(tf.math.square(neg_g - neg_g_mean), axis=0)

    avg_pos_coordinate_var = tf.reduce_mean(pos_coordinate_var)
    avg_neg_coordinate_var = tf.reduce_mean(neg_coordinate_var)

    if tf.math.is_nan(avg_pos_coordinate_var) or tf.math.is_nan(
             avg_neg_coordinate_var):
        return g

    g_diff = pos_g_mean - neg_g_mean

    g_diff_norm = tf.norm(tensor=g_diff)

    if tf.math.is_nan(g_diff_norm):
        return g

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
        logging.info(
            "gradient pos_g_norm: {}, neg_g_norm: {}".format(np.linalg.norm(pos_g_mean), np.linalg.norm(neg_g_mean)))
        logging.info("gradient g_diff_mean: {}, g_diff_min: {}, g_diff_max: {}, g_diff_norm: {}".format(np.mean(g_diff),
                                                                                                        np.amin(g_diff),
                                                                                                        np.amax(g_diff),
                                                                                                        np.linalg.norm(
                                                                                                            g_diff)))

    def compute_lambdas(u, v, scale, d, g_norm_square, p, sumKL_threshold, pos_g_mean, neg_g_mean, g_diff):
        # u = np.float32(u.numpy().item())
        # v = np.float32(v.numpy().item())
        # scale = np.float32(scale.numpy().item())
        # d = np.float32(d.numpy().item())
        # g_norm_square = np.float32(g_norm_square.numpy().item())
        # p = np.float32(p.numpy().item())
        # sumKL_threshold = np.float32(sumKL_threshold.numpy().item())

        # kl_obj = symKL_objective(np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(0.0), u, v, d,
        #                          g_norm_square)
        # logging.info("u: {}, v:{}, scale:{}, d:{}, g_diff_norm_square:{}, p:{}, sumKL_threshold:{}, current_kl: {}".format(u, v, scale, d, g_norm_square, p, sumKL_threshold, kl_obj))

        # if kl_obj < sumKL_threshold:
        #     # logging.info("lam10: {}, lam20: {}, lam11:{}, lam21:{}, sumKL:{}".format(0.0, 0.0, 0.0, 0.0, kl_obj))
        #     return np.float32(0.0), np.float32(0.0), np.float32(0.0), np.float32(0.0), kl_obj

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

            scale *= np.float32(1.5)  # loosen the power constraint

        # logging.info('solve_isotropic_covariance solving time: {}'.format(time.time() - start))

        return lam10, lam20, lam11, lam21, sumKL

    # lam10, lam20, lam11, lam21, sumKL = tf.py_function(compute_lambdas,
    #                                                [u, v, scale, d, g_norm_square, p, sumKL_threshold, pos_g_mean,
    #                                                 neg_g_mean, g_diff],
    #                                                [tf.float32, tf.float32, tf.float32, tf.float32, tf.float32])
    lam10, lam20, lam11, lam21, sumKL = tf.py_function(compute_lambdas,
                                                       [u, v, scale, d, g_norm_square, p, sumKL_threshold, pos_g_mean,
                                                        neg_g_mean, g_diff],
                                                       [tf.float32, tf.float32, tf.float32, tf.float32, tf.float32])
    lam10, lam20, lam11, lam21, sumKL = tf.reshape(lam10, shape=[1]), tf.reshape(lam20, shape=[1]), \
                                        tf.reshape(lam11,shape=[1]), tf.reshape(lam21, shape=[1]), \
                                        tf.reshape(sumKL, shape=[1])

    perturbed_g = g
    y_float = tf.cast(y, dtype=tf.float32)

    div_g = g_diff_norm
    if div_g == 0.:
        div_g = ZERO_REPLACE

    noise_1 = tf.reshape(tf.multiply(x=tf.random.normal(shape=tf.shape(y)), y=y_float), shape=(-1, 1)) * g_diff * (
                tf.math.sqrt(tf.math.abs(lam11 - lam21)) / div_g)
    noise_1 = tf.debugging.check_numerics(noise_1, "noise_1 ERROR", name="noise_1_debugging")

    noise_2 = tf.random.normal(shape=tf.shape(g)) * tf.reshape(y_float, shape=(-1, 1)) * tf.math.sqrt(
        tf.math.maximum(lam21, 0.0))
    noise_2 = tf.debugging.check_numerics(noise_2, "noise_2 ERROR", name="noise_2_debugging")

    noise_3 = tf.reshape(tf.multiply(x=tf.random.normal(shape=tf.shape(y)), y=1 - y_float), shape=(-1, 1)) * g_diff * (
                tf.math.sqrt(tf.math.abs(lam10 - lam20)) / div_g)
    noise_3 = tf.debugging.check_numerics(noise_3, "noise_3 ERROR", name="noise_3_debugging")

    noise_4 = tf.random.normal(shape=tf.shape(g)) * tf.reshape(1 - y_float, shape=(-1, 1)) * tf.math.sqrt(
        tf.math.maximum(lam20, 0.0))
    noise_4 = tf.debugging.check_numerics(noise_4, "noise_4 ERROR", name="noise_4_debugging")

    perturbed_g += (noise_1 + noise_2 + noise_3 + noise_4)
    perturbed_g = tf.debugging.check_numerics(perturbed_g, "perturbed_g ERROR", name="perturbed_g_debugging")

    return perturbed_g


# solver
def symKL_objective(lam10, lam20, lam11, lam21, u, v, d, g_norm_square):
    div1 = lam21 + v
    div2 = lam20 + u
    div3 = lam11 + v
    div4 = lam10 + u
    if div1 == 0.:
        div1 = ZERO_REPLACE
    if div2 == 0.:
        div2 = ZERO_REPLACE
    if div3 == 0.:
        div3 = ZERO_REPLACE
    if div4 == 0.:
        div4 = ZERO_REPLACE
    objective = np.float32((d - np.float32(1)) * (lam20 + u) / (div1) \
                           + (d - np.float32(1)) * (lam21 + v) / (div2) \
                           + (lam10 + u + g_norm_square) / (div3) \
                           + (lam11 + v + g_norm_square) / (div4))

    # logging.info("symKL_objective, objective: {}, type: {}".format(objective, type(objective)))
    return objective


def symKL_objective_zero_uv(lam10, lam11, g_norm_square):
    if lam11 == 0.:
        lam11 = ZERO_REPLACE
    if lam10 == 0.:
        lam10 = ZERO_REPLACE
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
    div1 = np.float32(1.0) - p
    if div1 == 0.:
        div1 = ZERO_REPLACE
    div2 = d
    if div2 == 0.:
        div2 = ZERO_REPLACE
    div3 = p
    if div3 == 0.:
        div3 = ZERO_REPLACE
    if u <= v:
        # logging.info("solve_isotropic_covariance, u<=v")
        for i in range(NUM_CANDIDATE):
            if i % 3 == ordering[0]:
                # print('a')
                if lam20_init:  # if we pass an initialization
                    lam20 = lam20_init
                    # print('here')
                else:
                    lam20 = np.float32(random.random() * P / div1 / div2)
                lam10, lam11 = None, None
                # print('lam21', lam21)
            elif i % 3 == ordering[1]:
                # print('b')
                if lam11_init:
                    lam11 = lam11_init
                else:
                    lam11 = np.float32(random.random() * P / div3)
                lam10, lam20 = None, None
                # print('lam11', lam11)
            else:
                # print('c')
                if lam10_init:
                    lam10 = lam10_init
                else:
                    lam10 = np.float32(random.random() * P / div1)
                lam11, lam20 = None, None
                # print('lam10', lam10)
            # logging.info("solve_isotropic_covariance, u<=v_iter_{}, lam10: {}, lam20: {}, lam11: {}, type_lam10: {}, type_lam20: {}, type_lam11: {}".format(i, lam10, lam20, lam11, type(lam10), type(lam20), type(lam11)))
            solutions.append(
                solve_small_neg(u=u, v=v, d=d, g_norm_square=g_norm_square, p=p, P=P, lam10=lam10, lam11=lam11,
                                lam20=lam20))

    else:
        # logging.info("solve_isotropic_covariance, u>v")
        for i in range(NUM_CANDIDATE):
            if i % 3 == ordering[0]:
                if lam21_init:
                    lam21 = lam21_init
                else:
                    lam21 = np.float32(random.random() * P / div3 / div2)
                lam10, lam11 = None, None
                # print('lam21', lam21)
            elif i % 3 == ordering[1]:
                if lam11_init:
                    lam11 = lam11_init
                else:
                    lam11 = np.float32(random.random() * P / div3)
                lam10, lam21 = None, None
                # print('lam11', lam11)
            else:
                if lam10_init:
                    lam10 = lam10_init
                else:
                    lam10 = np.float32(random.random() * P / div1)
                lam11, lam21 = None, None
                # print('lam10', lam10)
            # logging.info("solve_isotropic_covariance, u>v_iter_{}, lam10: {}, lam21: {}, lam11: {}, type_lam10: {}, type_lam21: {}, type_lam11: {}".format(i, lam10, lam21, lam11, type(lam10), type(lam21), type(lam11)))
            solutions.append(
                solve_small_pos(u=u, v=v, d=d, g_norm_square=g_norm_square, p=p, P=P, lam10=lam10, lam11=lam11,
                                lam21=lam21))

    # print(solutions)
    # logging.info("solve_isotropic_covariance, solutions: {}, len: {}".format(solutions, len(solutions)))
    lam10, lam20, lam11, lam21, objective = min(solutions, key=lambda x: x[-1])
    # logging.info("solve_isotropic_covariance, lam10: {}, lam20: {}, lam21: {}, lam11: {}, type_lam10: {}, type_lam21: {}, type_lam11: {}, type_lam20: {}".format(lam10, lam20, lam21, lam11, type(lam10), type(lam21), type(lam11), type(lam20)))

    # print('sum', p * lam11 + p*(d-1)*lam21 + (1-p) * lam10 + (1-p)*(d-1)*lam20)

    return (lam10, lam20, lam11, lam21, objective)


def solve_zero_uv(g_norm_square, p, P):
    C = P
    div1 = C + p * g_norm_square
    if div1 == 0.:
        div1 = ZERO_REPLACE
    E = np.float32(math.sqrt((C + (np.float32(1.0) - p) * g_norm_square) / div1))
    div2 = p
    if div2 == 0.:
        div2 = ZERO_REPLACE
    div3 = E + (np.float32(1.0) - p) / div2
    if div3 == 0.:
        div3 = ZERO_REPLACE
    tau = np.float32(max((P / div2) / div3, np.float32(0.0)))
    # print('tau', tau)
    # logging.info("solve_zero_uv, C: {}, E: {}, tau: {}, type_C: {}, type_E: {}, type_tau: {}".format(C, E, tau, type(C), type(E), type(tau)))
    div4 = np.float32(1.0) - p
    if div4 == 0.:
        div4 = ZERO_REPLACE
    if 0 <= tau and tau <= P / div4:
        # print('A')
        lam10 = tau
        lam11 = np.float32(max(P / div2 - (np.float32(1.0) - p) * tau / div2, np.float32(0.0)))
        # logging.info("solve_zero_uv, branch_1, lam10: {}, lam11: {}, type_lam10: {}, type_lam11:{}".format(lam10, lam11, type(lam10), type(lam11)))
    else:
        # print('B')
        lam10_case1, lam11_case1 = np.float32(0.0), max(P / div2, np.float32(0.0))
        lam10_case2, lam11_case2 = np.float32(max(P / div4, np.float32(0.0))), np.float32(0.0)
        objective1 = symKL_objective_zero_uv(lam10=lam10_case1, lam11=lam11_case1,
                                             g_norm_square=g_norm_square)
        objective2 = symKL_objective_zero_uv(lam10=lam10_case2, lam11=lam11_case2,
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


def prime1(x, d, v, lam11, u, g_norm_square, D):
    div11 = v
    if div11 == 0.:
        div11 = ZERO_REPLACE
    div12 = lam11 + v
    if div12 == 0.:
        div12 = ZERO_REPLACE
    div13 = x + u
    if div13 == 0.:
        div13 = ZERO_REPLACE
    div14 = (D - (d - np.float32(1.0)) * x + u)
    if div14 == 0.:
        div14 = ZERO_REPLACE
    return (d - np.float32(1.0)) / div11 - (d - np.float32(1.0)) / div12 - (
            d - np.float32(1.0)) / div13 * (v / div13) + (lam11 + v + g_norm_square) / div14 * (
                   (d - np.float32(1.0)) / div14)


def prime2(x, d, v, p, lam10, u, g_norm_square, D):
    div21 = v
    if div21 == 0.:
        div21 = ZERO_REPLACE
    div22 = lam10 + u
    if div22 == 0.:
        div22 = ZERO_REPLACE
    div23 = p
    if div23 == 0.:
        div23 = ZERO_REPLACE
    div24 = x + u
    if div24 == 0.:
        div24 = ZERO_REPLACE
    div25 = (D / div23 - (np.float32(1.0) - p) * (d - np.float32(1.0)) * x / div23 + v)
    if div25 == 0.:
        div25 = ZERO_REPLACE
    div26 = (D / div23 - (1 - p) * (d - 1) * x / div23 + v)
    if div26 == 0.:
        div26 = ZERO_REPLACE
    return (d - np.float32(1.0)) / div21 - (np.float32(1.0) - p) * (d - np.float32(1.0)) / div22 / div23 - (
                d - np.float32(1.0)) / div24 * (v / div24) + (
                   lam10 + u + g_norm_square) / div25 * (1 - p) * (d - 1) / div23 / div26

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
        if i % 3 == ordering[0]:  # fix lam20
            D = np.float32(P - (np.float32(1.0) - p) * (d - np.float32(1.0)) * lam20)
            C = np.float32(D + p * v + (np.float32(1.0) - p) * u)

            div1 = C + p * g_norm_square
            if div1 == 0.:
                div1 = ZERO_REPLACE
            E = np.float32(math.sqrt((C + (np.float32(1.0) - p) * g_norm_square) / div1))

            div2 = p
            if div2 == 0.:
                div2 = ZERO_REPLACE

            div_x = (E + (np.float32(1.0) - p) / div2)
            if div_x == 0.:
                div_x = ZERO_REPLACE
            tau = np.float32(max((D / div2 + v - E * u) / div_x, np.float32(0.0)))
            # print('tau', tau)
            div3 = np.float32(1.0) - p
            if div3 == 0.:
                div3 = ZERO_REPLACE

            if lam20 <= tau and tau <= np.float32(P / div3 - (d - np.float32(1.0)) * lam20):
                # print('A')
                lam10 = tau
                lam11 = np.float32(max(D / div2 - (np.float32(1.0) - p) * tau / div2, np.float32(0.0)))
            else:
                # print('B')
                lam10_case1, lam11_case1 = lam20, np.float32(
                    max(P / div2 - (np.float32(1.0) - p) * d * lam20 / div2, np.float32(0.0)))
                lam10_case2, lam11_case2 = np.float32(
                    max(P / div3 - (d - np.float32(1.0)) * lam20, np.float32(0.0))), np.float32(0.0)
                objective1 = symKL_objective(lam10=lam10_case1, lam20=lam20, lam11=lam11_case1, lam21=LAM21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square)
                objective2 = symKL_objective(lam10=lam10_case2, lam20=lam20, lam11=lam11_case2, lam21=LAM21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square)
                if objective1 < objective2:
                    lam10, lam11 = lam10_case1, lam11_case1
                else:
                    lam10, lam11 = lam10_case2, lam11_case2

        elif i % 3 == ordering[1]:  # fix lam11
            div1 = np.float32(1.0) - p
            if div1 == 0.:
                div1 = ZERO_REPLACE
            D = np.float32(max((P - p * lam11) / div1, np.float32(0.0)))
            f = lambda x: symKL_objective(lam10=D - (d - np.float32(1.0)) * x, lam20=x, lam11=lam11, lam21=LAM21,
                                          u=u, v=v, d=d, g_norm_square=g_norm_square)

            f_prime = lambda x: prime1(x=x, d=d, v=v, lam11=lam11, u=u, g_norm_square=g_norm_square, D=D)

            # f_prime = lambda x: (d - np.float32(1.0)) / v - (d - np.float32(1.0)) / (lam11 + v) - (
            #             d - np.float32(1.0)) / (x + u) * (v / (x + u)) + (lam11 + v + g_norm_square) / (
            #                                 D - (d - np.float32(1.0)) * x + u) * (
            #                                 (d - np.float32(1.0)) / (D - (d - np.float32(1.0)) * x + u))

            div2 = d
            if div2 == 0.:
                div2 = ZERO_REPLACE
            lam20 = convex_min_1d(xl=np.float32(0.0), xr=D / div2, f=f, f_prime=f_prime)
            lam10 = np.float32(max(D - (d - np.float32(1.0)) * lam20, np.float32(0.0)))

        else:  # fix lam10
            D = np.float32(
                max(P - (np.float32(1.0) - p) * lam10, np.float32(0.0)))  # avoid negative due to numerical error

            div1 = p
            if div1 == 0.:
                div1 = ZERO_REPLACE
            f = lambda x: symKL_objective(lam10=lam10, lam20=x,
                                          lam11=D / div1 - (np.float32(1.0) - p) * (d - np.float32(1.0)) * x / div1,
                                          lam21=LAM21,
                                          u=u, v=v, d=d, g_norm_square=g_norm_square)

            f_prime = lambda x: prime2(x=x, d=d, v=v, p=p, lam10=lam10, u=u, g_norm_square=g_norm_square, D=D)

            # f_prime = lambda x: (d - np.float32(1.0)) / v - (np.float32(1.0) - p) * (d - np.float32(1.0)) / (
            #             lam10 + u) / p - (d - np.float32(1.0)) / (x + u) * (v / (x + u)) + (
            #                                 lam10 + u + g_norm_square) / (
            #                                 D / p - (np.float32(1.0) - p) * (d - np.float32(1.0)) * x / p + v) * (
            #                                 1 - p) * (d - 1) / p / (D / p - (1 - p) * (d - 1) * x / p + v)

            div2 = (np.float32(1.0) - p) * (d - np.float32(1.0))
            if div2 == 0.:
                div2 = ZERO_REPLACE
            lam20 = convex_min_1d(xl=np.float32(0.0),
                                  xr=min(D / div2, lam10), f=f,
                                  f_prime=f_prime)
            lam11 = np.float32(max(D / div1 - (np.float32(1.0) - p) * (d - np.float32(1.0)) * lam20 / div1, np.float32(0.0)))

        # if lam10 <0 or lam20 < 0 or lam11 <0 or LAM21 <0: # check to make sure no negative values
        #     assert False, i

        objective_value_list.append(symKL_objective(lam10=lam10, lam20=lam20, lam11=lam11, lam21=LAM21,
                                                    u=u, v=v, d=d, g_norm_square=g_norm_square))
        # print(i)
        # print(objective_value_list[-1])
        # print(lam10, lam20, lam11, LAM21, objective_value_list[-1])
        # print('sum', p * lam11 + p*(d-1)*LAM21 + (1-p) * lam10 + (1-p)*(d-1)*lam20)
        # logging.info("solve_small_neg, iter: {}, objective_value_list[-1]: {}".format(i, objective_value_list[-1]))
        if (i >= 3 and objective_value_list[-4] - objective_value_list[-1] < OBJECTIVE_EPSILON) or i >= 100:
            # print(i)
            # logging.info("solve_small_neg, iter: {}, terminated".format(i))
            return (lam10, lam20, lam11, LAM21, np.float32(0.5) * objective_value_list[-1] - d)

        i += 1


def prime3(x, d, u, lam11, v, p, g_norm_square, D):
    div31 = u
    if div31 == 0.:
        div31 = ZERO_REPLACE
    div32 = lam11 + v
    if div32 == 0.:
        div32 = ZERO_REPLACE
    div33 = (np.float32(1.0) - p)
    if div33 == 0.:
        div33 = ZERO_REPLACE
    div34 = x + v
    if div34 == 0.:
        div34 = ZERO_REPLACE
    div35 = (D - p * (d - np.float32(1.0)) * x) / div33 + u
    if div35 == 0.:
        div35 = ZERO_REPLACE
    return (d - np.float32(1.0)) / div31 - p * (d - np.float32(1.0)) / div32 / div33 - (d - 1) / div34 * (u / div34) \
                                + (lam11 + v + g_norm_square) / div35 * p * (d - np.float32(1.0)) / div33 / div35


def prime4(x, d, u, lam10, v, g_norm_square, D):
    div41 = u
    if div41 == 0.:
        div41 = ZERO_REPLACE
    div42 = lam10 + u
    if div42 == 0.:
        div42 = ZERO_REPLACE
    div43 = x + v
    if div43 == 0.:
        div43 = ZERO_REPLACE
    div44 = (D - (d - np.float32(1.0)) * x + v)
    if div44 == 0.:
        div44 = ZERO_REPLACE
    return (d - np.float32(1.0)) / div41 - (d - np.float32(1.0)) / div42 - (
            d - np.float32(1.0)) / div43 * (u / div43) + (lam10 + u + g_norm_square) / div44 * (d - np.float32(1.0)) / div44


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
        if i % 3 == ordering[0]:  # fix lam21
            D = np.float32(P - p * (d - np.float32(1.0)) * lam21)
            C = np.float32(D + p * v + (np.float32(1.0) - p) * u)

            div1 = (C + p * g_norm_square)
            if div1 == 0.:
                div1 = ZERO_REPLACE
            E = np.float32(math.sqrt((C + (np.float32(1.0) - p) * g_norm_square) / div1))
            div2 = p
            if div2 == 0.:
                div2 = ZERO_REPLACE
            div3 = (E + (np.float32(1.0) - p) / div2)
            if div3 == 0.:
                div3 = ZERO_REPLACE
            tau = np.float32(max((D / div2 + v - E * u) / div3, np.float32(0.0)))
            # print('tau', tau)
            div4 = (np.float32(1.0) - p)
            if div4 == 0.:
                div4 = ZERO_REPLACE
            if np.float32(0.0) <= tau and tau <= (P - p * d * lam21) / div4:
                # print('A')
                lam10 = tau
                lam11 = np.float32(max(D / div2 - (np.float32(1.0) - p) * tau / div2, np.float32(0.0)))
            else:
                # print('B')
                lam10_case1, lam11_case1 = np.float32(0), np.float32(
                    max(P / div2 - (d - np.float32(1.0)) * lam21, np.float32(0.0)))
                lam10_case2, lam11_case2 = np.float32(
                    max((P - p * d * lam21) / div4, np.float32(0.0))), lam21
                objective1 = symKL_objective(lam10=lam10_case1, lam20=LAM20, lam11=lam11_case1, lam21=lam21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square)
                objective2 = symKL_objective(lam10=lam10_case2, lam20=LAM20, lam11=lam11_case2, lam21=lam21,
                                             u=u, v=v, d=d, g_norm_square=g_norm_square)
                if objective1 < objective2:
                    lam10, lam11 = lam10_case1, lam11_case1
                else:
                    lam10, lam11 = lam10_case2, lam11_case2
            # logging.info("solve_small_pos, branch: 0, lam10: {}, lam11: {}".format(lam10, lam11))
        elif i % 3 == ordering[1]:  # fix lam11
            D = np.float32(max(P - p * lam11, np.float32(0.0)))
            div1 = np.float32(1.0) - p
            if div1 == 0.:
                div1 = ZERO_REPLACE
            f = lambda x: symKL_objective(lam10=(D - p * (d - 1) * x) / div1, lam20=LAM20, lam11=lam11,
                                          lam21=x,
                                          u=u, v=v, d=d, g_norm_square=g_norm_square)

            f_prime = lambda x: prime3(x=x, d=d, u=v, lam11=lam11, v=v, p=p, g_norm_square=g_norm_square, D=D)
            # f_prime = lambda x: (d - np.float32(1.0)) / u - p * (d - np.float32(1.0)) / (lam11 + v) / (
            #             np.float32(1.0) - p) - (d - 1) / (x + v) * (u / (x + v)) + (lam11 + v + g_norm_square) / (
            #                                 (D - p * (d - 1) * x) / (np.float32(1.0) - p) + u) * p * (
            #                                 d - np.float32(1.0)) / (np.float32(1.0) - p) / (
            #                                 (D - p * (d - np.float32(1.0)) * x) / (np.float32(1.0) - p) + u)

            div2 = p
            if div2 == 0.:
                div2 = ZERO_REPLACE
            div3 = d - np.float32(1.0)
            if div3 == 0.:
                div3 = ZERO_REPLACE
            lam21 = convex_min_1d(xl=np.float32(0.0), xr=min(D / div2 / div3, lam11), f=f,
                                  f_prime=f_prime)
            lam10 = np.float32(max((D - p * (d - 1) * lam21) / div1, np.float32(0.0)))
            # logging.info("solve_small_pos, branch: 1, lam10: {}, lam21: {}".format(lam10, lam21))

        else:  # fix lam10
            div1 = p
            if div1 == 0.:
                div1 = ZERO_REPLACE
            D = np.float32(max((P - (1 - p) * lam10) / div1, np.float32(0.0)))
            f = lambda x: symKL_objective(lam10=lam10, lam20=LAM20, lam11=D - (d - np.float32(1.0)) * x, lam21=x,
                                          u=u, v=v, d=d, g_norm_square=g_norm_square)

            f_prime = lambda x: prime4(x=x, d=d, u=u, lam10=lam10, v=v, g_norm_square=g_norm_square, D=D)
            # f_prime = lambda x: (d - np.float32(1.0)) / u - (d - np.float32(1.0)) / (lam10 + u) - (
            #             d - np.float32(1.0)) / (x + v) * (u / (x + v)) + (lam10 + u + g_norm_square) / (
            #                                 D - (d - np.float32(1.0)) * x + v) * (d - np.float32(1.0)) / (
            #                                 D - (d - np.float32(1.0)) * x + v)

            div2 = d
            if div2 == 0.:
                div2 = ZERO_REPLACE
            lam21 = convex_min_1d(xl=np.float32(0.0), xr=D / div2, f=f, f_prime=f_prime)
            lam11 = np.float32(max(D - (d - np.float32(1.0)) * lam21, np.float32(0.0)))

        objective_value_list.append(symKL_objective(lam10=lam10, lam20=LAM20, lam11=lam11, lam21=lam21,
                                                    u=u, v=v, d=d, g_norm_square=g_norm_square))

        if (i >= 3 and objective_value_list[-4] - objective_value_list[-1] < OBJECTIVE_EPSILON) or i >= 100:
            # logging.info("solve_small_pos, iter: {}, terminated".format(i))
            return (lam10, LAM20, lam11, lam21, np.float32(np.float32(0.5) * objective_value_list[-1] - d))

        i += 1


def convex_min_1d(xl, xr, f, f_prime):
    xm = np.float32((xl + xr) / np.float32(2.0))
    if abs(xl - xr) <= CONVEX_EPSILON or abs(xl - xm) <= CONVEX_EPSILON or abs(xm - xr) <= CONVEX_EPSILON:
        return np.float32(min((f(x), x) for x in [xl, xm, xr])[1])
    if f_prime(xl) <= 0 and f_prime(xr) <= 0:
        return np.float32(xr)
    elif f_prime(xl) >= 0 and f_prime(xr) >= 0:
        return np.float32(xl)
    if f_prime(xm) > 0:
        return convex_min_1d(xl=xl, xr=xm, f=f, f_prime=f_prime)
    else:
        return convex_min_1d(xl=xm, xr=xr, f=f, f_prime=f_prime)


def small_neg_problem_string(u, v, d, g_norm_square, p, P):
    return 'minimize ({2}-1)*(z + {0})/{1} + ({2}-1)*{1}/(z+{0})+(x+{0}+{3})/(y+{1}) + (y+{1}+{3})/(x+{0}) subject to x>=0, y>=0, z>=0, z<=x, {4}*y+(1-{4})*x+(1-{4})*({2}-1)*z={5}'.format(
        u, v, d, g_norm_square, p, P)


def small_pos_problem_string(u, v, d, g_norm_square, p, P):
    return 'minimize ({2}-1)*{0}/(z+{1}) + ({2}-1)*(z + {1})/{0} + (x+{0}+{3})/(y+{1}) + (y+{1}+{3})/(x+{0}) subject to x>=0, y>=0, z>=0, z<=y, {4}*y+(1-{4})*x+{4}*({2}-1)*z={5}'.format(
        u, v, d, g_norm_square, p, P)


def zero_uv_problem_string(g_norm_square, p, P):
    return 'minimize (x+{0})/y + (y+{0})/x subject to x>=0, y>=0, {1}*y+(1-{1})*x={2}'.format(g_norm_square, p, P)

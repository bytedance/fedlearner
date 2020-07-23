#!/usr/bin/env python
# coding: utf-8
import sys
import os
import argparse
import datetime
import random
import numpy as np
import tensorflow as tf
from tensorflow.keras.datasets import fashion_mnist

parser = argparse.ArgumentParser()
parser.add_argument("--batch_size", type=int, default=300)
parser.add_argument('--gpu_option', action='store_true')
parser.add_argument("--num_epochs", type=int, default=1)
parser.add_argument("--num_outputs", type=int, default=2)
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()

gpu_option = args.gpu_option

if gpu_option:
    gpus = tf.config.experimental.list_physical_devices('GPU')
    print("Num GPUs Available: ", len(gpus))
    if gpus:
        # Restrict TensorFlow to only use the first GPU
        try:
            tf.config.experimental.set_visible_devices(gpus[0], 'GPU')
            tf.config.experimental.set_memory_growth(gpus[0], True)
        except RuntimeError as e:
            print(e)
else:
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

print("current available GPUs: {}".format(
    len(tf.config.experimental.list_physical_devices('GPU'))))

# batch_size = args.batch_size
batch_size_test = 200
is_shuffle = True

(x_train, y_train), (x_test, y_test) = fashion_mnist.load_data()
x_train = tf.cast(x_train, tf.float32) / 255
x_test = tf.cast(x_test, tf.float32) / 255

total_training_instances = len(x_train)
total_test_instances = len(x_test)
num_batchs = total_training_instances / args.batch_size

print(
    "total_training_instances: {}, total_test_instances: {}, num_batchs: {}".format(
        total_training_instances,
        total_test_instances,
        num_batchs))

def change_label(y, ratio=10):
    def condition(x):
        if x == 1:
            if random.randint(0, ratio) <= 1:
                return 1
        return 0
    l = [1 if i == 1 else 0 for i in y]
    res = np.array(list(map(lambda x: condition(x), l)))
    print("positive ratio: {}".format(sum(res) / len(l)))
    return res

if args.num_outputs == 2:
    y_train = change_label(y_train)
    y_test = change_label(y_test)
    # is_shuffle = False

if is_shuffle:
    train_ds_iter = tf.data.Dataset.from_tensor_slices((x_train, y_train)).shuffle(
        total_training_instances + 1, reshuffle_each_iteration=True).batch(args.batch_size)
    test_ds_iter = tf.data.Dataset.from_tensor_slices((x_test, y_test)).shuffle(
        total_test_instances + 1, reshuffle_each_iteration=True).batch(batch_size_test)
else:
    train_ds_iter = tf.data.Dataset.from_tensor_slices(
        (x_train, y_train)).batch(args.batch_size)
    test_ds_iter = tf.data.Dataset.from_tensor_slices(
        (x_test, y_test)).batch(batch_size_test)

def get_fashion_mnist_labels(labels):
    text_labels = ['t-shirt', 'trouser', 'pullover', 'dress', 'coat',
                   'sandal', 'shirt', 'sneaker', 'bag', 'ankle boot']
    return [text_labels[int(i)] for i in labels]

if sys.platform.startswith('win'):
    num_workers = 0
else:
    num_workers = 4

num_inputs = 784

if args.debug:
    hidden_outputs_1 = 6
    hidden_outputs_2 = 4
else:
    hidden_outputs_1 = 128
    hidden_outputs_2 = 32

num_outputs = 1

W = tf.Variable(
    tf.random.normal(
        shape=(
            num_inputs,
            hidden_outputs_1),
        mean=0,
        stddev=0.01,
        dtype=tf.float32))
W1 = tf.Variable(
    tf.random.normal(
        shape=(
            hidden_outputs_1,
            hidden_outputs_2),
        mean=0,
        stddev=0.01,
        dtype=tf.float32))
W2 = tf.Variable(
    tf.random.normal(
        shape=(
            hidden_outputs_2,
            num_outputs),
        mean=0,
        stddev=0.01,
        dtype=tf.float32))

b = tf.Variable(tf.zeros(hidden_outputs_1, dtype=tf.float32))
b1 = tf.Variable(tf.zeros(hidden_outputs_2, dtype=tf.float32))
b2 = tf.Variable(tf.zeros(num_outputs, dtype=tf.float32))


def softmax(logits, axis=-1):
    return tf.nn.softmax(logits, axis=axis)


def cross_entropy(y_hat, y):
    # return tf.nn.softmax_cross_entropy_with_logits(y, y_hat)
    y = tf.cast(tf.reshape(y, shape=[-1, 1]), dtype=tf.int32)
    y = tf.one_hot(y, depth=y_hat.shape[-1])
    y = tf.cast(tf.reshape(y, shape=[-1, y_hat.shape[-1]]), dtype=tf.int32)
    return -tf.math.log(tf.boolean_mask(y_hat, y) + 1e-8)


def sigmoid_cross_entropy(y_hat, y):
    y = tf.cast(tf.reshape(y, shape=[-1, 1]), dtype=tf.float32)
    loss = tf.nn.sigmoid_cross_entropy_with_logits(labels=y, logits=y_hat)
    return loss


train_auc = tf.keras.metrics.AUC()
leakage_auc_baseline = tf.keras.metrics.AUC(num_thresholds=1000)
leakage_auc_baseline_all = tf.keras.metrics.AUC(num_thresholds=1000)
leakage_auc_masked_hiddenlayer_1 = tf.keras.metrics.AUC(num_thresholds=1000)
leakage_auc_masked_hiddenlayer_1_all = tf.keras.metrics.AUC(
    num_thresholds=1000)
leakage_auc_masked_hiddenlayer_2 = tf.keras.metrics.AUC(num_thresholds=1000)
leakage_auc_not_masked_hiddenlayer_2 = tf.keras.metrics.AUC(
    num_thresholds=1000)


def normalized_norm(vector):
    norm_g = tf.norm(vector, axis=-1, keepdims=False)
    norm_g = norm_g / tf.math.reduce_max(norm_g)
    return norm_g


def label_leakge_auc(y, predicted_value, m_auc):
    predicted_value = tf.math.abs(predicted_value)
    val_max = tf.math.reduce_max(predicted_value)
    val_min = tf.math.reduce_min(predicted_value)
    pred = (predicted_value - val_min) / (val_max - val_min + 1e-12)
    m_auc.update_state(tf.reshape(y, [-1, 1]), tf.reshape(pred, [-1, 1]))


@tf.custom_gradient
def gradient_masking_2(x):
    # add scalar noise with aligning the maximum norm (positive instance)
    global _Batch_Labels
    _Batch_Labels = tf.reshape(
        tf.cast(_Batch_Labels, dtype=tf.float32), [-1, 1])

    def grad_fn(g):
        g_norm = tf.reshape(tf.norm(g, axis=1, keepdims=True), [-1, 1])
        max_norm = tf.reduce_max(g_norm * _Batch_Labels)
        stds = tf.sqrt(tf.maximum(max_norm ** 2 /
                                  (g_norm ** 2 + 1e-32) - 1.0, 0.0))
        standard_gaussian_noise = tf.random.normal(
            tf.shape(_Batch_Labels), mean=0.0, stddev=1.0)
        gaussian_noise = standard_gaussian_noise * stds
        res = g * (1 + gaussian_noise)
        return res
    return x, grad_fn


@tf.custom_gradient
def gradient_masking(x):
    # add scalar noise to align with the maximum norm in the batch
    def grad_fn(g):
        g_norm = tf.reshape(tf.norm(g, axis=1, keepdims=True), [-1, 1])
        max_norm = tf.reduce_max(g_norm)
        stds = tf.sqrt(tf.maximum(max_norm ** 2 /
                                  (g_norm ** 2 + 1e-32) - 1.0, 0.0))
        standard_gaussian_noise = tf.random.normal(
            shape=(tf.shape(g)[0], 1), mean=0.0, stddev=1.0)
        gaussian_noise = standard_gaussian_noise * stds
        res = g * (1 + gaussian_noise)
        return res
    return x, grad_fn


def compute_gradient_norm(gradient, label):
    g_norm = tf.reshape(tf.norm(gradient, axis=1, keepdims=True), [-1])
    label = tf.cast(tf.reshape(label, [-1]), dtype=tf.float32)
    pos_g_norm = tf.boolean_mask(g_norm, label)
    neg_label = tf.cast(label < 1.0, dtype=tf.float32)
    neg_g_norm = tf.boolean_mask(g_norm, neg_label)
    print("g_norm: {}".format(g_norm))
    print("pos_norm: {}".format(pos_g_norm))
    print("neg_norm: {}".format(neg_g_norm))
    return g_norm, pos_g_norm, neg_g_norm


def middle_attack(gradient, label, select_positive=True):
    g_norm = tf.reshape(tf.norm(gradient, axis=1, keepdims=True), [-1])
    label = tf.cast(tf.reshape(label, [-1]), dtype=tf.float32)
    indices = tf.argsort(
        g_norm,
        axis=-1,
        direction="ASCENDING",
        stable=True,
        name="middle_attack_arg_sort")
    if not select_positive:
        # select negative instances
        label = tf.cast(label < 1.0, dtype=tf.float32)
    g_norm_label = g_norm * label
    norm_label = tf.gather(g_norm_label, indices)
    zero = tf.constant(0, dtype=tf.float32)
    mask = tf.not_equal(norm_label, zero)
    res = tf.where(mask)
    # res = tf.sort(res, axis = -1, direction = "DESCENDING")
    # print("positive_instances: {}, # instances: {},  norm rank indices:
    # mean: {}, min: {}, max: {}".format(select_positive, res.shape,
    # tf.reduce_mean(res), tf.reduce_min(res), tf.reduce_max(res)))
    return res


def train(
        train_iter,
        test_iter,
        loss,
        num_epochs,
        params=None,
        trainer=None,
        regularization_weight=0.1):
    best_test_auc = 0
    best_epoch = 0
    global _Batch_Labels, _Batch_Positive_Predicted_Probabilities
    for epoch in range(num_epochs):
        train_l_sum, train_acc_sum, n = 0.0, 0.0, 0
        leakage_auc_baseline.reset_states()
        leakage_auc_baseline_all.reset_states()

        leakage_auc_masked_hiddenlayer_1.reset_states()
        leakage_auc_masked_hiddenlayer_2.reset_states()
        leakage_auc_masked_hiddenlayer_1_all.reset_states()

        leakage_auc_not_masked_hiddenlayer_2.reset_states()
        train_auc.reset_states()

        e_s = datetime.datetime.now()

        gradient_list = []
        gradient_list_1 = []
        gradient_list_2 = []
        gradient_list_3 = []
        label_list = []
        for (idx, (X, y)) in enumerate(train_iter):

            batch_size = X.shape[0]
            b_s = datetime.datetime.now()
            _Batch_Labels = y
            _Batch_Positive_Predicted_Probabilities = tf.math.sigmoid(
                predict(X))
            # print("update: _Batch_Labels: {}".format(_Batch_Labels))
            # print("update _Batch_Positive_Predicted_Probabilities: {}".format(_Batch_Positive_Predicted_Probabilities))
            with tf.GradientTape(persistent=False) as tape:
                hidden_logits = tf.nn.relu(
                    tf.matmul(tf.reshape(X, shape=(-1, W.shape[0])), W) + b)
                hidden_logits_2 = tf.nn.relu(tf.matmul(tf.reshape(
                    hidden_logits, shape=(-1, W1.shape[0])), W1) + b1)
                hidden_logits_2_masking = gradient_masking(hidden_logits_2)
                logits = tf.matmul(tf.reshape(
                    hidden_logits_2_masking, shape=(-1, W2.shape[0])), W2) + b2
                l = tf.reduce_sum(loss(logits, y)) + regularization_weight * \
                    (tf.norm(W) ** 2 + tf.norm(W2) ** 2 + tf.norm(W1) ** 2)

            grads = tape.gradient(l,
                                  params + [hidden_logits,
                                            hidden_logits_2,
                                            hidden_logits_2_masking,
                                            logits])
            y = tf.cast(y, dtype=tf.float32)

            for i, param in enumerate(params):
                trainer.apply_gradients([(grads[i] / batch_size, param)])
            if args.num_outputs == 2:
                try:
                    label_leakge_auc(y, tf.norm(
                        grads[-1], axis=-1, keepdims=False), leakage_auc_baseline)
                    label_leakge_auc(y,
                                     tf.norm(grads[-2],
                                             axis=-1,
                                             keepdims=False),
                                     leakage_auc_not_masked_hiddenlayer_2)
                    label_leakge_auc(y,
                                     tf.norm(grads[-3],
                                             axis=-1,
                                             keepdims=False),
                                     leakage_auc_masked_hiddenlayer_2)
                    label_leakge_auc(y,
                                     tf.norm(grads[-4],
                                             axis=-1,
                                             keepdims=False),
                                     leakage_auc_masked_hiddenlayer_1)

                    gradient_list.append(grads[-1])
                    gradient_list_1.append(grads[-2])
                    gradient_list_2.append(grads[-3])
                    gradient_list_3.append(grads[-4])

                    label_list.append(tf.reshape(y, [-1, 1]))
                    if epoch == num_epochs - 1 and False:
                        _Batch_Labels = tf.cast(
                            _Batch_Labels, dtype=tf.float32)
                        pos_p_min = tf.cond(
                            tf.reduce_sum(_Batch_Labels) <= 0.0,
                            lambda: 1.0,
                            lambda: tf.reduce_min(
                                tf.boolean_mask(
                                    _Batch_Positive_Predicted_Probabilities,
                                    _Batch_Labels)))
                        pos_p_mean = tf.cond(
                            tf.reduce_sum(_Batch_Labels) <= 0.0,
                            lambda: 1.0,
                            lambda: tf.reduce_mean(
                                tf.boolean_mask(
                                    _Batch_Positive_Predicted_Probabilities,
                                    _Batch_Labels)))
                        pos_p_max = tf.cond(
                            tf.reduce_sum(_Batch_Labels) <= 0.0,
                            lambda: 1.0,
                            lambda: tf.reduce_max(
                                tf.boolean_mask(
                                    _Batch_Positive_Predicted_Probabilities,
                                    _Batch_Labels)))
                        print(
                            "pos prob: min: {}, mean: {}, max: {}".format(
                                pos_p_min, pos_p_mean, pos_p_max))
                        negs = tf.cast(
                            _Batch_Labels < 1.0,
                            dtype=tf.float32) * _Batch_Positive_Predicted_Probabilities
                        print("neg prob:  max:{}".format(tf.reduce_max(negs)))
                        # print("predicted_prob: {}".format(tf.reshape(_Batch_Positive_Predicted_Probabilities,[-1])))
                        # print("loss/logits norm: {}".format(tf.norm(grads[-1], axis = -1, keepdims= False)))
                except Exception as e:
                    print("Train Exception: {}".format(e))
            train_l_sum += l.numpy()
            try:
                train_auc.update_state(tf.reshape(
                    y, [-1, 1]), tf.reshape(tf.math.sigmoid(logits), [-1, 1]))
            except Exception as e:
                print("Train_AUC Exception: {}".format(e))
                return
            n += y.shape[0]
            b_e = datetime.datetime.now()

        gradients_stack = tf.concat(gradient_list, axis=0)
        gradients_stack_1 = tf.concat(gradient_list_1, axis=0)
        gradients_stack_2 = tf.concat(gradient_list_2, axis=0)
        gradients_stack_3 = tf.concat(gradient_list_3, axis=0)

        labels_stack = tf.concat(label_list, axis=0)
        # print("gradients_stack.shape: {}, gradients_stack_1.shape: {},labels.shape: {}".format(gradients_stack.shape, gradients_stack_1.shape, labels_stack.shape))
        pos_norm_ranking_order_baseline = middle_attack(
            gradients_stack, labels_stack)
        neg_norm_ranking_order_baseline = middle_attack(
            gradients_stack, labels_stack, select_positive=False)
        label_leakge_auc(
            labels_stack,
            tf.norm(
                gradients_stack,
                axis=-1,
                keepdims=False),
            leakage_auc_baseline_all)
        label_leakge_auc(
            labels_stack,
            tf.norm(
                gradients_stack_2,
                axis=-1,
                keepdims=False),
            leakage_auc_masked_hiddenlayer_1_all)
        pos_norm_ranking_order_non_masking = middle_attack(
            gradients_stack_1, labels_stack)
        pos_norm_ranking_order_masking_1 = middle_attack(
            gradients_stack_2, labels_stack)
        neg_norm_ranking_order_masking_1 = middle_attack(
            gradients_stack_2, labels_stack, select_positive=False)
        pos_norm_ranking_order_masking_2 = middle_attack(
            gradients_stack_3, labels_stack)

        gradients_stack_2_n, gradients_stack_2_pos_n, gradients_stack_2_neg_n = compute_gradient_norm(
            gradients_stack_2, labels_stack)
        gradients_stack_baseline_n, gradients_stack_baseline_pos_n, gradients_stack_baseline_neg_n = compute_gradient_norm(
            gradients_stack_1, labels_stack)

        e_e = datetime.datetime.now()
        print(
            "epoch: {}, loss: {}, train auc: {},  , # instances: {}, time used: {}".
                format(
                epoch,
                train_l_sum /
                n,
                train_auc.result(),
                n,
                e_e -
                e_s))
        if args.num_outputs == 2:
            print(
                "epoch {}, label leakage: baseline auc:{},  non_masking hidden layer: {}, masking hidden layer 1:{}, masking hidden layer 2: {}".
                    format(
                    epoch,
                    leakage_auc_baseline.result(),
                    leakage_auc_not_masked_hiddenlayer_2.result(),
                    leakage_auc_masked_hiddenlayer_1.result(),
                    leakage_auc_masked_hiddenlayer_2.result()))
            print("epoch: {}, leak_auc_baseline_all: {}, leakage_auc_masked_hiddenlayer_1_all: {}".format(
                epoch, leakage_auc_baseline_all.result(), leakage_auc_masked_hiddenlayer_1_all.result()))
        test_loss, test_auc = test(test_iter, loss)

        with writer.as_default():
            tf.summary.scalar('train_loss', train_l_sum / n, step=epoch)
            tf.summary.scalar('train_auc', train_auc.result(), step=epoch)
            # tf.summary.scalar('train_auc', train_acc_sum / n, step=epoch)
            if args.num_outputs == 2:
                tf.summary.scalar(
                    'leakage_auc_baseline',
                    leakage_auc_baseline.result(),
                    step=epoch)
                tf.summary.scalar(
                    'leakage_auc_not_masked_hiddenlayer_2',
                    leakage_auc_not_masked_hiddenlayer_2.result(),
                    step=epoch)
                tf.summary.scalar(
                    'leakage_auc_masked_hiddenlayer_1',
                    leakage_auc_masked_hiddenlayer_1.result(),
                    step=epoch)
                tf.summary.scalar(
                    'leakage_auc_masked_hiddenlayer_2',
                    leakage_auc_masked_hiddenlayer_2.result(),
                    step=epoch)
                tf.summary.histogram(
                    "pos_norm_ranking_order_non_masking",
                    pos_norm_ranking_order_non_masking / n,
                    step=epoch)
                tf.summary.histogram(
                    "pos_norm_ranking_order_baseline",
                    pos_norm_ranking_order_baseline / n,
                    step=epoch)
                tf.summary.histogram(
                    "pos_norm_ranking_order_masking_1",
                    pos_norm_ranking_order_masking_1 / n,
                    step=epoch)
                tf.summary.histogram(
                    "pos_norm_ranking_order_masking_2",
                    pos_norm_ranking_order_masking_2 / n,
                    step=epoch)
                tf.summary.histogram(
                    "neg_norm_ranking_order_baseline",
                    neg_norm_ranking_order_baseline / n,
                    step=epoch)
                tf.summary.histogram(
                    "neg_norm_ranking_order_masking_1",
                    neg_norm_ranking_order_masking_1 / n,
                    step=epoch)
                tf.summary.histogram(
                    "gradients_layer_2_norm",
                    gradients_stack_2_n,
                    step=epoch)
                tf.summary.histogram(
                    "gradients_layer_2_pos_norm",
                    gradients_stack_2_pos_n,
                    step=epoch)
                tf.summary.histogram(
                    "gradients_layer_2_neg_norm",
                    gradients_stack_2_neg_n,
                    step=epoch)
                tf.summary.histogram(
                    "gradients_norm_baseline_n",
                    gradients_stack_baseline_n,
                    step=epoch)
                tf.summary.histogram(
                    "gradients_norm_baseline_pos_n",
                    gradients_stack_baseline_pos_n,
                    step=epoch)
                tf.summary.histogram(
                    "gradients_norm_baseline_neg_n",
                    gradients_stack_baseline_neg_n,
                    step=epoch)

            tf.summary.scalar('test_loss', test_loss, step=epoch)
            tf.summary.scalar('test_auc', test_auc, step=epoch)

        if test_auc > best_test_auc:
            best_test_auc = max(test_auc, best_test_auc)
            best_epoch = epoch
            print("current best test auc: {}".format(best_test_auc))
            print("current best epoch: {}".format(best_epoch))

    print("best test auc: {}".format(best_test_auc))
    print("best epoch: {}".format(best_epoch))


def predict(X):
    hidden_logits = tf.nn.relu(
        tf.matmul(tf.reshape(X, shape=(-1, W.shape[0])), W) + b)
    hidden_logits_2 = tf.nn.relu(tf.matmul(tf.reshape(
        hidden_logits, shape=(-1, W1.shape[0])), W1) + b1)
    logits = tf.matmul(tf.reshape(
        hidden_logits_2, shape=(-1, W2.shape[0])), W2) + b2
    return logits


def test(test_iter, loss):
    test_l_sum, test_acc_sum, n = 0.0, 0.0, 0
    test_auc = tf.keras.metrics.AUC()
    test_auc.reset_states()
    for (idx, (X, y)) in enumerate(test_iter):
        logits = predict(X)
        l = tf.reduce_sum(loss(logits, y))
        y = tf.cast(y, dtype=tf.float32)
        test_l_sum += l.numpy()
        try:
            test_auc.update_state(tf.reshape(
                y, [-1, 1]), tf.reshape(tf.math.sigmoid(logits), [-1, 1]))
        except Exception as e:
            print("Test Exception: {}".format(e))
            return
        n += y.shape[0]
    print("test loss: {}, test auc: {}".format(
        test_l_sum / n, test_auc.result()))
    return test_l_sum / n, test_auc.result()


# Set up logging.
stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
logdir = 'logs/%s' % stamp
writer = tf.summary.create_file_writer(logdir)

# num_epochs, debug = args.num_epochs, args.debug
regularization_weight = 0.5
activation = "relu"
ada_gra_lr = 0.01
trainer = tf.keras.optimizers.Adagrad(learning_rate=ada_gra_lr)

t_s = datetime.datetime.now()
print(
    "gpu_option: {}, train_batch_size: {}, regularization_weight: {}, ada_gra_lr: {}".format(
        gpu_option,
        args.batch_size,
        regularization_weight,
        ada_gra_lr))
train(
    train_ds_iter,
    test_ds_iter,
    sigmoid_cross_entropy,
    args.num_epochs,
    params=[
        W,
        b,
        W1,
        b1,
        W2,
        b2],
    trainer=trainer,
    regularization_weight=regularization_weight)
print(
    "gpu_option: {}, train_batch_size: {}, regularization_weight: {},  ada_gra_lr: {}".
        format(
        gpu_option,
        args.batch_size,
        regularization_weight,
        ada_gra_lr))
t_e = datetime.datetime.now()
print(
    "total_training_instances: {}, total_test_instances: {}, num_batchs: {}, training used: {}".
        format(
        total_training_instances,
        total_test_instances,
        num_batchs,
        t_e -
        t_s))

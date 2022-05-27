import argparse
import datetime
import time
import tensorflow.compat.v1 as tf
from tensorflow.keras import layers
from tensorflow.keras.datasets import fashion_mnist

parser = argparse.ArgumentParser()
parser.add_argument("--batch_size", type=int, default=200)
parser.add_argument('--gpu_option', action='store_true')
parser.add_argument('--gpu_id', type=int, default=3)

parser.add_argument("--num_epochs", type=int, default=100)

parser.add_argument("--reconstruction_loss_weight", type=float, default=1.0)
parser.add_argument("--distance_correlation_weight", type=float, default=0.0)
parser.add_argument("--log_distance_correlation", action='store_true')
parser.add_argument("--reconstruction_stablizer_noise_weight", type=float,
                    default=0.0)
parser.add_argument("--grl", type=float, default=0.0)

parser.add_argument("--no_reshuffle", action='store_true')

parser.add_argument("--dis_kernel_regularizer", type=float, default=0.001)
parser.add_argument("--rec_kernel_regularizer", type=float, default=0.001)
# using sigmoid at the reconstructor
parser.add_argument("--sigmoid", action='store_true')

parser.add_argument("--rec_lr", type=float, default=1e-3)
parser.add_argument("--rec_beta1", type=float, default=0.9)
parser.add_argument("--dis_lr", type=float, default=1e-3)
parser.add_argument("--dis_beta1", type=float, default=0.9)

# only for the gradient reversal layer
parser.add_argument("--clip_norm", type=float, default=0.0)
parser.add_argument("--clip_norm_adam", type=float, default=0.0)
# for all network parameters
parser.add_argument("--clip_global_norm_adam", type=float, default=0.0)
parser.add_argument("--clip_global_value_adam", type=float, default=0.0)
parser.add_argument("--clip_value", type=float, default=0.0)
parser.add_argument("--clip_value_adam", type=float, default=0.0)

# standard deviation of Gaussian noise added to the split layer
parser.add_argument("--noise_stddev", type=float, default=0.0)
parser.add_argument('--debug', action='store_true')

args = parser.parse_args()

if args.gpu_option:
    gpus = tf.config.experimental.list_physical_devices('GPU')
    print("Num GPUs Available: ", len(gpus))
    if gpus:
        # Restrict TensorFlow to only use the first GPU
        try:
            tf.config.experimental.set_visible_devices(gpus[args.gpu_id], 'GPU')
            tf.config.experimental.set_memory_growth(gpus[args.gpu_id], True)
            print("Using GPU: {}".format(args.gpu_id))
        except RuntimeError as e:
            # Visible devices must be set at program startup
            print(e)
else:
    import os
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

batch_size = args.batch_size
print("batch_size: {}, reconstruction_loss_weight: {}, grl: {}".format(
    batch_size, args.reconstruction_loss_weight, args.grl))


def make_discriminator_model_passive():
    model = tf.keras.Sequential()
    output_size = 784
    model.add(layers.Dense(output_size, use_bias=False, input_shape=(784,),
                           kernel_regularizer=tf.keras.regularizers.l2(
        args.dis_kernel_regularizer)))
    return model


def generate_gaussian_noise(input_emb, stddev=1):
    noise = tf.random.normal(shape=tf.shape(input_emb),
                             mean=0, stddev=stddev, dtype=tf.float32)
    return noise


def make_reconstruction_model():
    model = tf.keras.Sequential()
    input_size, output_size = 784, 784
    if args.sigmoid:
        model.add(layers.Dense(output_size, use_bias=False,
                               input_shape=(input_size,),
                               kernel_regularizer=tf.keras.regularizers.l2(
                                   args.rec_kernel_regularizer),
                               activation=tf.nn.sigmoid))
    else:
        model.add(layers.Dense(output_size, use_bias=False,
                               input_shape=(input_size,),
                               kernel_regularizer=tf.keras.regularizers.l2(
                                   args.rec_kernel_regularizer)))
    return model


def make_discriminator_model_active():
    model = tf.keras.Sequential()
    model.add(layers.Dense(256, use_bias=True, input_shape=(784,),
                           kernel_regularizer=tf.keras.regularizers.l2(
        args.dis_kernel_regularizer)))
    model.add(layers.LeakyReLU())
    model.add(layers.Dropout(0.2))
    model.add(layers.Dense(10, kernel_regularizer=tf.keras.regularizers.l2(
        args.dis_kernel_regularizer)))
    return model

# cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits=True)
# cross_entropy = tf.keras.losses.sparse_categorical_crossentropy(
#                                                         from_logits = True)

def cross_entropy_loss(prediction_logits, labels):
    prediction_logits = tf.cast(tf.reshape(prediction_logits, shape=[-1, 10]),
                                dtype=tf.float32)
    labels = tf.cast(tf.reshape(labels, shape=[-1, 1]), dtype=tf.float32)
    cro_ent = tf.reduce_sum(tf.keras.losses.sparse_categorical_crossentropy(
        labels, prediction_logits, from_logits=True))
    return cro_ent


def discriminator_loss(prediction_logits, labels, reconstructed_emb,
                       reconstructed_emb_for_noise,
                       reconstructed_emb_independent_attacker,
                       protected_emb, raw_emb,
                       reconstruction_loss_weight,
                       distance_correlation_weight,
                       reconstruction_stablizer_noise_weight=0.0,
                       log_distance_correlation=False):
    dist_cov, dist_cor = tf_distance_cov_cor(raw_emb, protected_emb,
                                             debug=False)
    dis_loss = cross_entropy_loss(prediction_logits, labels)
    rec_loss = reconstruction_loss(reconstructed_emb, raw_emb)
    rec_noise_loss = reconstruction_stablizer_noise(reconstructed_emb_for_noise)
    total_loss = dis_loss + rec_loss * reconstruction_loss_weight

    independent_attacker_rec_loss = reconstruction_loss(
        reconstructed_emb_independent_attacker,
        raw_emb)
    total_loss += independent_attacker_rec_loss

    if log_distance_correlation:
        total_loss += distance_correlation_weight * tf.math.log(dist_cor)
    else:
        total_loss += distance_correlation_weight * dist_cor
    return total_loss, dis_loss, rec_loss, (dist_cov, dist_cor), \
        rec_noise_loss, independent_attacker_rec_loss


def reconstruction_stablizer_quad(reconstructed_emb, protected_emb):
    return tf.reduce_sum(tf.math.square(tf.reduce_sum(tf.math.square(
        tf.reshape(protected_emb, shape=tf.shape(reconstructed_emb))
        - reconstructed_emb), axis=-1)))


def reconstruction_stablizer_noise(reconstructed_emb,
                                   noise_type="uniform",
                                   normal_mu=1.0,
                                   normal_std=1.0,
                                   uniform_min=0.0,
                                   uniform_max=1.0):
    if noise_type == "uniform":
        noise = tf.random.uniform(
            shape=tf.shape(reconstructed_emb),
            minval=uniform_min,
            maxval=uniform_max,
            dtype=tf.float32)
    elif noise_type == "normal":
        noise = tf.random.normal(
            shape=tf.shape(reconstructed_emb),
            mean=normal_mu,
            stddev=normal_std,
            dtype=tf.float32)
    return reconstruction_loss(reconstructed_emb, noise)


def reconstruction_loss(reconstructed_emb, protected_emb):
    return tf.reduce_sum(tf.reshape(tf.reduce_sum(tf.math.square(
        tf.reshape(protected_emb, shape=tf.shape(reconstructed_emb))
        - reconstructed_emb), axis=-1), shape=[-1, 1]))


@tf.custom_gradient
def stop_gradient_layer(x):
    def grad_fn(g):
        return g * 0.0
    return x, grad_fn


@tf.custom_gradient
def gradient_reversal_layer(x):
    # global _global_step

    def grad_fn(g):
        clip_norm = args.clip_norm
        clip_value = args.clip_value
        if clip_value > 0.0:
            clipped_g = tf.clip_by_value(g, clip_value_min=-1.0 * clip_value,
                                         clip_value_max=clip_value)
        else:
            clipped_g = g
        if clip_norm > 0.0:
            clipped_g = tf.clip_by_norm(clipped_g, clip_norm)
        res = args.grl * clipped_g
        # with writer.as_default():
        #     tf.summary.scalar('split_layer_gradient/original', tf.norm(g),
        #                       step=_global_step)
        #     tf.summary.scalar('split_layer_gradient/clipped', tf.norm(res),
        #                       step=_global_step)
        return res
    return x, grad_fn


def pairwise_dist(A, B):
    """
    Computes pairwise distances between each elements of A and each elements of
    B.
    Args:
        A,    [m,d] matrix
        B,    [n,d] matrix
    Returns:
        D,    [m,n] matrix of pairwise distances
    """
    # with tf.variable_scope('pairwise_dist'):
    # squared norms of each row in A and B
    na = tf.reduce_sum(tf.square(A), 1)
    nb = tf.reduce_sum(tf.square(B), 1)

    # na as a row and nb as a column vectors
    na = tf.reshape(na, [-1, 1])
    nb = tf.reshape(nb, [1, -1])

    # return pairwise euclidead difference matrix
    D = tf.sqrt(tf.maximum(na - 2 * tf.matmul(A, B, False, True) + nb + 1e-20,
                           0.0))
    return D

def tf_distance_cov_cor(input1, input2, debug=False):
    start = time.time()

    input1 = tf.debugging.check_numerics(input1, "input1 contains nan/inf")
    input2 = tf.debugging.check_numerics(input2, "input2 contains nan/inf")

    n = tf.cast(tf.shape(input1)[0], tf.float32)
    a = pairwise_dist(input1, input1)
    b = pairwise_dist(input2, input2)

    A = a - tf.reduce_mean(a,
                           axis=1) - tf.expand_dims(tf.reduce_mean(a,
                                                                   axis=0),
                                                    axis=1) + tf.reduce_mean(a)
    B = b - tf.reduce_mean(b,
                           axis=1) - tf.expand_dims(tf.reduce_mean(b,
                                                                   axis=0),
                                                    axis=1) + tf.reduce_mean(b)

    dCovXY = tf.sqrt(tf.reduce_sum(A * B) / (n ** 2))
    dVarXX = tf.sqrt(tf.reduce_sum(A * A) / (n ** 2))
    dVarYY = tf.sqrt(tf.reduce_sum(B * B) / (n ** 2))

    dCorXY = dCovXY / tf.sqrt(dVarXX * dVarYY)
    end = time.time()
    if debug:
        print(("tf distance cov: {} and cor: {}, dVarXX: {}, "
               "dVarYY:{} uses: {}").format(
            dCovXY, dCorXY,
            dVarXX, dVarYY,
            end - start))
    return dCovXY, dCorXY

# @tf.function
def train_step(X, Y, discriminator_passive, reconstruction,
               discriminator_active, independent_attacker,
               reconstruction_optimizer, discriminator_optimizer,
               step,
               idx=0,
               pre_train_discriminator_early_stopping=False,
               pre_train_reconstruction_early_stopping=False,
               update_discriminator=False,
               update_reconstruction=True):
    with tf.GradientTape() as reco_tape, tf.GradientTape() as disc_tape:
        dis_cov_cors = []
        X = tf.reshape(X, shape=(-1, 784))
        emb = discriminator_passive(X, training=True)

        if args.noise_stddev > 1e-8:
            emb += generate_gaussian_noise(emb, stddev=args.noise_stddev)

        protected_emb = emb

        logits = discriminator_active(protected_emb, training=True)

        protected_emb_GRL = gradient_reversal_layer(protected_emb)
        protected_emb_stop_g = stop_gradient_layer(protected_emb)

        reconstructed_emb = reconstruction(protected_emb_GRL, training=True)
        reconstructed_emb_for_noise = reconstruction(protected_emb,
                                                     training=True)
        reconstructed_emb_independent_attacker = independent_attacker(
            protected_emb_stop_g, training=True)
        disc_loss, cross_entropy_loss_train, reco_loss, \
            (dist_cov_X_Protected_emb, dist_cor_X_Protected_emb), \
            rec_noise_loss, independent_attacker_rec_loss = \
            discriminator_loss(logits, Y,
                               reconstructed_emb,
                               reconstructed_emb_for_noise,
                               reconstructed_emb_independent_attacker,
                               protected_emb, X,
                               reconstruction_loss_weight=
                               args.reconstruction_loss_weight,
                               distance_correlation_weight=
                               args.distance_correlation_weight,
                               log_distance_correlation=
                               args.log_distance_correlation,
                               reconstruction_stablizer_noise_weight=
                               args.reconstruction_stablizer_noise_weight)
        rec_noise_loss_w = args.reconstruction_stablizer_noise_weight \
            * rec_noise_loss

        dis_cov_cors.append((dist_cov_X_Protected_emb,
                             dist_cor_X_Protected_emb))
        dist_cov_X_Rec_emb, dist_cor_X_Rec_emb = tf_distance_cov_cor(
            X, reconstructed_emb)
        dis_cov_cors.append((dist_cov_X_Rec_emb, dist_cor_X_Rec_emb))

    gradients_of_discriminator_passive_rec_noise = reco_tape.gradient(
        rec_noise_loss_w, discriminator_passive.trainable_variables)
    gradients_of_discriminator = disc_tape.gradient(
        disc_loss,
        reconstruction.trainable_variables +
        discriminator_active.trainable_variables +
        discriminator_passive.trainable_variables +
        independent_attacker.trainable_variables)

    if args.clip_global_norm_adam > 0.0:
        gradients_of_discriminator, global_norm = tf.clip_by_global_norm(
            gradients_of_discriminator,
            clip_norm=args.clip_global_norm_adam)
        with writer.as_default():
            tf.summary.scalar('global_norm', global_norm,
                              step=step * args.batch_size + idx)

    if args.clip_global_value_adam > 0.0:
        gradients_of_discriminator = \
            [None if gradient is None else tf.clip_by_value(gradient,
                            clip_value_min=-1.0 * args.clip_global_value_adam,
                            clip_value_max=args.clip_global_value_adam)
             for gradient in gradients_of_discriminator]

    discriminator_optimizer.apply_gradients(
        zip(
            gradients_of_discriminator,
            reconstruction.trainable_variables +
            discriminator_active.trainable_variables +
            discriminator_passive.trainable_variables +
            independent_attacker.trainable_variables))
    if args.reconstruction_stablizer_noise_weight > 0.0:
        discriminator_optimizer.apply_gradients(zip(
            gradients_of_discriminator_passive_rec_noise,
            discriminator_passive.trainable_variables))
    return logits, reco_loss, disc_loss, cross_entropy_loss_train, \
        dis_cov_cors, rec_noise_loss, independent_attacker_rec_loss


def train(train_dataset, val_dataset, test_dataset, epochs):

    reconstruction_optimizer = tf.keras.optimizers.Adam(args.rec_lr,
                                                        beta_1=args.rec_beta1)

    if args.clip_norm_adam > 0.0:
        if args.clip_value_adam > 0.0:
            discriminator_optimizer = tf.keras.optimizers.Adam(args.dis_lr,
                clipnorm=args.clip_norm_adam, clipvalue=args.clip_value_adam)
        else:
            discriminator_optimizer = tf.keras.optimizers.Adam(
                args.dis_lr, clipnorm=args.clip_norm_adam)
    else:
        if args.clip_value_adam > 0.0:
            discriminator_optimizer = tf.keras.optimizers.Adam(
                args.dis_lr, clipvalue=args.clip_value_adam)
        else:
            discriminator_optimizer = tf.keras.optimizers.Adam(args.dis_lr)

    reconstruction = make_reconstruction_model()
    independent_attacker = make_reconstruction_model()
    discriminator_passive = make_discriminator_model_passive()
    discriminator_active = make_discriminator_model_active()

    train_acc = tf.keras.metrics.Accuracy()

    max_stagnation = 5  # number of epochs without improvement to tolerate
    best_val_ent_loss, best_val_epoch = None, None
    pre_train_dis_early_stopping = False

    best_val_rec_loss, best_val_rec_epoch = None, None
    pre_train_rec_early_stopping = False

    alt_update_dis, alt_update_rec = True, True

    # global _global_step

    for epoch in range(epochs):
        start = time.time()
        train_reco_noise_loss_sum, train_reco_loss_sum, train_dis_loss_sum, \
            train_ent_loss_sum, independent_attacker_rec_loss_sum, n = \
            0.0, 0.0, 0.0, 0.0, 0.0, 0
        train_reco_loss_last_batch_sum, train_dis_loss_last_batch_sum, \
            train_ent_loss_last_batch_sum, last_n = 0.0, 0.0, 0.0, 0
        dist_cov_X_Protected_emb_sum, dist_cor_X_Protected_emb_sum = 0.0, 0.0
        dist_cov_X_Rec_emb_sum, dist_cor_X_Rec_emb_sum = 0.0, 0.0

        num_batchs = 0

        train_acc.reset_states()

        for (idx, (X, Y)) in enumerate(train_dataset):
            # _global_step = epoch * args.batch_size + idx
            num_batchs += 1

            logits, reco_loss, dis_loss, cross_entropy_loss_train, \
                dis_cov_cors, \
                rec_noise_loss, independent_attacker_rec_loss = \
                train_step(X, Y,
                           discriminator_passive,
                           reconstruction,
                           discriminator_active,
                           independent_attacker,
                           reconstruction_optimizer,
                           discriminator_optimizer,
                           step=epoch,
                           idx=idx,
                           pre_train_discriminator_early_stopping=
                           pre_train_dis_early_stopping,
                           pre_train_reconstruction_early_stopping=
                           pre_train_rec_early_stopping,
                           update_discriminator=alt_update_dis,
                           update_reconstruction=alt_update_rec)
            train_acc.update_state(tf.reshape(Y, [-1, 1]), tf.argmax(
                tf.reshape(logits, [-1, 10]), axis=-1))
            train_dis_loss_sum += dis_loss
            train_reco_loss_sum += reco_loss
            train_ent_loss_sum += cross_entropy_loss_train
            train_reco_noise_loss_sum += rec_noise_loss
            independent_attacker_rec_loss_sum += independent_attacker_rec_loss
            dist_cov_X_Protected_emb_sum += dis_cov_cors[0][0]
            dist_cor_X_Protected_emb_sum += dis_cov_cors[0][1]
            dist_cov_X_Rec_emb_sum += dis_cov_cors[1][0]
            dist_cor_X_Rec_emb_sum += dis_cov_cors[1][1]

            n += Y.shape[0]

        with writer.as_default():
            tf.summary.scalar('train/acc', train_acc.result(), step=epoch)
            tf.summary.scalar('train/reconstruction_loss_mean',
                              train_reco_loss_sum / n, step=epoch)
            tf.summary.scalar('train/discriminator_loss_mean',
                              train_dis_loss_sum / n, step=epoch)
            tf.summary.scalar('train/cross_entropy_loss_mean',
                              train_ent_loss_sum / n, step=epoch)
            tf.summary.scalar('train/reconstruction_noise_loss_mean',
                              train_reco_noise_loss_sum / n, step=epoch)
            tf.summary.scalar('train/independent_attacker_rec_loss_mean',
                              independent_attacker_rec_loss_sum / n, step=epoch)
            # tf.summary.scalar('lr/decayed_dis_lr',
            #                   discriminator_optimizer._decayed_lr(tf.float32),
            #                   step=epoch)
            tf.summary.scalar("train//dcor/X_and_Protected_emb_cov",
                              dist_cov_X_Protected_emb_sum / num_batchs,
                              step=epoch)
            tf.summary.scalar("train//dcor/X_and_Protected_emb_cor",
                              dist_cor_X_Protected_emb_sum / num_batchs,
                              step=epoch)
            tf.summary.scalar("train//dcor/X_and_Rec_emb_cov",
                              dist_cov_X_Rec_emb_sum / num_batchs,
                              step=epoch)
            tf.summary.scalar("train//dcor/X_and_Rec_emb_cor",
                              dist_cor_X_Rec_emb_sum / num_batchs,
                              step=epoch)

        print(("epoch: {}, train_acc: {}, train_reconstruction_loss_mean: {},"
               " train_indepedent_attack_rec_loss_mean: {},"
               "train_discriminator_loss_mean: {}, "
               "train_cross_entropy_loss_mean: {}, "
               "reconstruction_noise_loss_mean: {}, "
               "X_and_Protected_emb_cov: {}, "
               "X_and_Protected_emb_cor: {}, "
               "X_and_Rec_emb_cov: {}, X_and_Rec_emb_cor: {}").format(
            epoch, train_acc.result(),
            train_reco_loss_sum / n,
            independent_attacker_rec_loss_sum / n,
            train_dis_loss_sum / n,
            train_ent_loss_sum / n,
            train_reco_noise_loss_sum / n,
            dist_cov_X_Protected_emb_sum / num_batchs,
            dist_cor_X_Protected_emb_sum / num_batchs,
            dist_cov_X_Rec_emb_sum / num_batchs,
            dist_cor_X_Rec_emb_sum / num_batchs))
        val_rec_loss_mean, val_ent_loss_mean, _ = test(
            test_dataset,
            discriminator_passive,
            reconstruction, independent_attacker,
            discriminator_active,
            is_validation=True, epoch=epoch)
        test(val_dataset, discriminator_passive, reconstruction,
             independent_attacker, discriminator_active,
             is_validation=False, epoch=epoch)

        rec_norm = tf.sqrt(tf.reduce_sum(
            [tf.norm(w)**2 for w in reconstruction.trainable_variables]))
        dis_passive_norm = tf.sqrt(tf.reduce_sum(
            [tf.norm(w)**2 for w in discriminator_passive.trainable_variables]))
        dis_active_norm = tf.sqrt(tf.reduce_sum(
            [tf.norm(w)**2 for w in discriminator_active.trainable_variables]))
        dis_norm = tf.sqrt(dis_active_norm ** 2 + dis_passive_norm ** 2)
        dis_rec_norm = tf.sqrt(rec_norm ** 2 + dis_norm ** 2)
        with writer.as_default():
            tf.summary.scalar('norm_kernel/rec_norm', rec_norm, step=epoch)
            tf.summary.scalar('norm_kernel/dis_passive_norm', dis_passive_norm,
                              step=epoch)
            tf.summary.scalar('norm_kernel/dis_active_norm', dis_active_norm,
                              step=epoch)
            tf.summary.scalar('norm_kernel/dis_norm', dis_norm, step=epoch)
            tf.summary.scalar('norm_kernel/dis_rec_norm', dis_rec_norm,
                              step=epoch)
        print('Time for epoch {} is {} sec, program config: {}'.format(
            epoch + 1, time.time() - start, stamp))

# @tf.function


def test(dataset, discriminator_passive, reconstruction,
         independent_attacker,
         discriminator_active,
         is_validation=True,
         epoch=1):
    test_reco_noise_loss_sum, test_reco_loss_sum, test_dis_loss_sum, \
        test_ent_loss_sum, independent_attacker_rec_loss_sum, n = \
        0.0, 0.0, 0.0, 0.0, 0.0, 0
    test_acc = tf.keras.metrics.Accuracy()
    test_acc.reset_states()

    dist_cov_X_Protected_emb_sum, dist_cor_X_Protected_emb_sum = 0.0, 0.0
    dist_cov_X_Rec_emb_sum, dist_cor_X_Rec_emb_sum = 0.0, 0.0
    num_batchs = 0

    for (X, Y) in dataset:
        X = tf.reshape(X, shape=(-1, 784))
        emb = discriminator_passive(X, training=False)
        protected_emb = emb
        logits = discriminator_active(protected_emb, training=False)

        reconstructed_emb = reconstruction(protected_emb, training=False)
        reconstructed_emb_independent_attacker = independent_attacker(
            protected_emb, training=False)
        disc_loss, cross_entropy_loss_test, reco_loss, \
            (dist_cov_X_Protected_emb, dist_cor_X_Protected_emb), \
            rec_noise_loss, independent_attacker_rec_loss = \
            discriminator_loss(
                logits, Y,
                reconstructed_emb,
                reconstructed_emb,
                reconstructed_emb_independent_attacker,
                protected_emb, X,
                reconstruction_loss_weight=args.reconstruction_loss_weight,
                distance_correlation_weight=args.distance_correlation_weight,
                log_distance_correlation=args.log_distance_correlation,
                reconstruction_stablizer_noise_weight=
                args.reconstruction_stablizer_noise_weight)
        n += Y.shape[0]
        test_reco_loss_sum += reco_loss
        test_dis_loss_sum += disc_loss
        test_ent_loss_sum += cross_entropy_loss_test
        test_reco_noise_loss_sum += rec_noise_loss
        independent_attacker_rec_loss_sum += independent_attacker_rec_loss
        test_acc.update_state(tf.reshape(Y, [-1, 1]),
                              tf.argmax(tf.reshape(logits, [-1, 10]), axis=-1))

        dist_cov_X_Rec_emb, dist_cor_X_Rec_emb = tf_distance_cov_cor(
            X, reconstructed_emb)

        dist_cov_X_Protected_emb_sum += dist_cov_X_Protected_emb
        dist_cor_X_Protected_emb_sum += dist_cor_X_Protected_emb
        dist_cov_X_Rec_emb_sum += dist_cov_X_Rec_emb
        dist_cor_X_Rec_emb_sum += dist_cor_X_Rec_emb
        num_batchs += 1

    with writer.as_default():
        if is_validation:
            prefix = "val/"
        else:
            prefix = "test/"
        tf.summary.scalar(prefix + 'acc', test_acc.result(), step=epoch)
        tf.summary.scalar(prefix + 'reconstruction_loss_mean',
                          test_reco_loss_sum / n, step=epoch)
        tf.summary.scalar(prefix + 'reconstruction_noise_loss_mean',
                          independent_attacker_rec_loss_sum / n, step=epoch)
        tf.summary.scalar(prefix + 'discriminator_loss_mean',
                          test_dis_loss_sum / n, step=epoch)
        tf.summary.scalar(prefix + 'cross_entropy_loss_mean',
                          test_ent_loss_sum / n, step=epoch)
        tf.summary.scalar(prefix + 'independent_attacker_rec_loss_mean',
                          test_ent_loss_sum / n, step=epoch)
        tf.summary.scalar(prefix + '/dcor/dist_cov_X_Protected_emb',
                          dist_cov_X_Protected_emb_sum / num_batchs, step=epoch)
        tf.summary.scalar(prefix + '/dcor/dist_cor_X_Protected_emb',
                          dist_cor_X_Protected_emb_sum / num_batchs, step=epoch)
        tf.summary.scalar(prefix + '/dcor/dist_cov_X_Rec_emb',
                          dist_cov_X_Rec_emb_sum / num_batchs, step=epoch)
        tf.summary.scalar(prefix + '/dcor/dist_cor_X_Rec_emb',
                          dist_cor_X_Rec_emb_sum / num_batchs, step=epoch)

    if is_validation:
        print(("epoch: {}, val_acc: {}, val_reconstruction_loss_mean: {}, "
               "val_reconstruction_noise_loss_mean: {}, "
               "val_discriminator_loss_mean: {}, "
               "val_cross_entropy_loss_mean: {}").format(
            epoch, test_acc.result(), test_reco_loss_sum / n,
            test_reco_noise_loss_sum / n, test_dis_loss_sum / n,
            test_ent_loss_sum / n))
    else:
        print(("epoch: {}, test_acc: {}, test_reconstruction_loss_mean: {},"
               "test_reconstruction_noise_loss_mean: {},"
               "test_discriminator_loss_mean: {}, "
               "test_cross_entropy_loss_mean: {}").format(
            epoch, test_acc.result(), test_reco_loss_sum / n,
            test_reco_noise_loss_sum / n, test_dis_loss_sum / n,
            test_ent_loss_sum / n))
    return test_reco_loss_sum / n, test_ent_loss_sum / n, test_dis_loss_sum / n


(x_train, y_train), (x_test, y_test) = fashion_mnist.load_data()
x_train = tf.cast(x_train, tf.float32) / 255
x_test = tf.cast(x_test, tf.float32) / 255

x_train = tf.reshape(x_train, shape=[-1, 28, 28, 1])
x_test = tf.reshape(x_test, shape=[-1, 28, 28, 1])

# Reserve 10,000 samples for validation
x_val = x_train[-10000:]
y_val = y_train[-10000:]
x_train = x_train[:-10000]
y_train = y_train[:-10000]

input_shape = (28, 28, 1)

total_training_instances = len(x_train)
total_val_instances = len(x_val)
total_test_instances = len(x_test)
print(("total_training_instances: {}, total_test_instances: {}, "
       "num_batchs: {}").format(total_training_instances, total_test_instances,
                                total_training_instances // batch_size))
if not args.no_reshuffle:
    train_iter = tf.data.Dataset.from_tensor_slices((x_train, y_train)).shuffle(
        total_training_instances + 1, reshuffle_each_iteration=True).batch(
        batch_size)
    val_iter = tf.data.Dataset.from_tensor_slices((x_val, y_val)).shuffle(
        total_val_instances + 1, reshuffle_each_iteration=True).batch(
        batch_size)
    test_iter = tf.data.Dataset.from_tensor_slices((x_test, y_test)).shuffle(
        total_test_instances + 1, reshuffle_each_iteration=True).batch(
        batch_size)
else:
    train_iter = tf.data.Dataset.from_tensor_slices((x_train, y_train)).batch(
        batch_size)
    val_iter = tf.data.Dataset.from_tensor_slices((x_val, y_val)).batch(
        batch_size)
    test_iter = tf.data.Dataset.from_tensor_slices((x_test, y_test)).batch(
        batch_size)

# Set up logging.
if args.debug:
    stamp = "debug_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
else:
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

stamp += "_bs_" + str(args.batch_size) + "_es_" + str(args.num_epochs) + \
    "_rec_loss_w_" + str(args.reconstruction_loss_weight) + \
    "_dcor_weight_" + str(args.distance_correlation_weight)
stamp += "_rec_noise_loss_w_" + str(args.reconstruction_stablizer_noise_weight)

if args.log_distance_correlation:
    stamp += "_logdcor"

stamp += str("_dis_lr_") + str(args.dis_lr)
stamp += "_grl_" + str(args.grl)

if args.clip_norm > 0.0:
    stamp += "_clip_norm_" + str(args.clip_norm)

if args.clip_norm_adam > 0.0:
    stamp += "_clip_norm_adam_" + str(args.clip_norm_adam)

if args.clip_value > 0.0:
    stamp += "_clip_value_" + str(args.clip_value)
if args.clip_value_adam > 0.0:
    stamp += "_clip_value_adam_" + str(args.clip_value_adam)

if args.clip_global_value_adam > 0.0:
    stamp += "_clip_global_value_adam_" + str(args.clip_global_value_adam)

if args.clip_global_norm_adam > 0.0:
    stamp += "_clip_global_norm_adam_" + str(args.clip_global_norm_adam)

if args.noise_stddev >= 1e-8:
    stamp += "_noise_stddev_" + str(args.noise_stddev)

if args.sigmoid:
    stamp += "_sigmoid"
else:
    stamp += "_linear"

logdir = 'logs/%s' % stamp
writer = tf.summary.create_file_writer(logdir)
train(train_iter, val_iter, test_iter, epochs=args.num_epochs)

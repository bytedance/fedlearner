import tensorflow as tf
import logging
import time

class DisCorLoss(tf.keras.losses.Loss):
    def __init__(self, **kwargs):
        super(DisCorLoss, self).__init__(**kwargs)
    
    def _pairwise_dist(self, A, B):
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

    def tf_distance_cor(self, embeddings, labels, debug=False):
        start = time.time()

        embeddings = tf.debugging.check_numerics(embeddings, "embeddings contains nan/inf")
        labels = tf.debugging.check_numerics(labels, "labels contains nan/inf")
        labels = tf.expand_dims(labels, 1)

        n = tf.cast(tf.shape(embeddings)[0], tf.float32)
        a = self._pairwise_dist(embeddings, embeddings)
        b = self._pairwise_dist(labels, labels)

        A = a - tf.reduce_mean(a,
                            axis=1) - tf.expand_dims(tf.reduce_mean(a,
                                                                    axis=0),
                                                        axis=1) + tf.reduce_mean(a)
        B = b - tf.reduce_mean(b,
                            axis=1) - tf.expand_dims(tf.reduce_mean(b,
                                                                    axis=0),
                                                        axis=1) + tf.reduce_mean(b)

        dCovXY = tf.sqrt(tf.abs(tf.reduce_sum(A * B) / (n ** 2)))
        dVarXX = tf.sqrt(tf.abs(tf.reduce_sum(A * A) / (n ** 2)))
        dVarYY = tf.sqrt(tf.abs(tf.reduce_sum(B * B) / (n ** 2)))

        dCorXY = dCovXY / tf.sqrt(dVarXX * dVarYY)
        end = time.time()
        if debug:
            print(("tf distance cov: {} and cor: {}, dVarXX: {}, "
                "dVarYY:{} uses: {}").format(
                dCovXY, dCorXY,
                dVarXX, dVarYY,
                end - start))
        return dCorXY
            
            

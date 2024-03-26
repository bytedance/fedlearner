import tensorflow as tf
import logging
import time

# DisCorLoss论文详见：https://arxiv.org/abs/2203.01451

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

        # X = x - x的行均值 - x的列均值 + x的总均值
        A = a - tf.reduce_mean(a,
                            axis=1) - tf.expand_dims(tf.reduce_mean(a,
                                                                    axis=0),
                                                        axis=1) + tf.reduce_mean(a)
        B = b - tf.reduce_mean(b,
                            axis=1) - tf.expand_dims(tf.reduce_mean(b,
                                                                    axis=0),
                                                        axis=1) + tf.reduce_mean(b)
        # 计算协方差
        dCovXY = tf.sqrt(tf.abs(tf.reduce_sum(A * B) / (n ** 2)))
        # 计算方差
        dVarXX = tf.sqrt(tf.abs(tf.reduce_sum(A * A) / (n ** 2)))
        dVarYY = tf.sqrt(tf.abs(tf.reduce_sum(B * B) / (n ** 2)))
        # 计算相关性
        dCorXY = dCovXY / tf.sqrt(dVarXX * dVarYY)
        end = time.time()
        if debug:
            print(("tf distance cov: {} and cor: {}, dVarXX: {}, "
                "dVarYY:{} uses: {}").format(
                dCovXY, dCorXY,
                dVarXX, dVarYY,
                end - start))
        return dCorXY
            
            

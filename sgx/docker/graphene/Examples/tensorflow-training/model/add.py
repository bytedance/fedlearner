import tensorflow as tf

x = tf.Variable(3, tf.int16)
y = tf.Variable(5, tf.int16)
z = tf.add(x,y)
init = tf.global_variables_initializer()
with tf.Session() as sess:
    sess.run(init)
    print(sess.run(z))

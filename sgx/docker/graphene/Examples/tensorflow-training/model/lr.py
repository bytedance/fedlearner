import numpy as np
import tensorflow.compat.v1 as tf
 
num_points = 1000
vectors_set = []
for i in range (num_points):
    x1 = np.random.normal (0.0, 0.6)
    y1 = x1*0.5+0.3+np.random.normal(0.0,0.3)
    vectors_set.append([x1,y1])
x_data = [v[0] for v in vectors_set]
y_data = [v[1] for v in vectors_set]

W = tf.Variable(tf.random_uniform([1],-1.0,1.0),name='W')
b = tf.Variable(tf.zeros([1]),name='b')
y = W*x_data+b


loss = tf.reduce_mean(tf.square(y-y_data),name='loss')
optimizer = tf.train.GradientDescentOptimizer(0.5)
train = optimizer.minimize(loss,name='train')

with tf.Session() as sess:
    init = tf.global_variables_initializer()
    sess.run(init)

    for seg in range (100):
        sess.run(train)

    print ('W=', sess.run(W), 'b=', sess.run(b),'loss=', sess.run(loss))

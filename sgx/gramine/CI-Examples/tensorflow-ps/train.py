import os
import numpy as np
import tensorflow.compat.v1 as tf
tf.disable_eager_execution() 

# Configuration of cluster 
ps_hosts = [ "localhost:60001"]
worker_hosts = [ "localhost:61001"]

tf.app.flags.DEFINE_string("job_name", "worker", "One of 'ps', 'worker'")
tf.app.flags.DEFINE_integer("task_index", 0, "Index of task within the job")

cluster = tf.train.ClusterSpec({"ps": ps_hosts, "worker": worker_hosts})

FLAGS = tf.app.flags.FLAGS

def main(_):
    server = tf.train.Server(cluster,
            job_name=FLAGS.job_name,
            task_index=FLAGS.task_index)
    if FLAGS.job_name == "ps":
        server.join()
    elif FLAGS.job_name == "worker":
        with tf.device(tf.train.replica_device_setter(
            worker_device="/job:worker/task:%d" % FLAGS.task_index,
            cluster=cluster)):
            
            x_data = tf.placeholder(tf.float32, [100])
            y_data = tf.placeholder(tf.float32, [100])

            W = tf.Variable(tf.random_uniform([1], -1.0, 1.0))
            b = tf.Variable(tf.zeros([1]))
            y = W * x_data + b
            loss = tf.reduce_mean(tf.square(y - y_data))
            
            global_step = tf.train.get_or_create_global_step();
            optimizer = tf.train.GradientDescentOptimizer(0.1)
            train_op = optimizer.minimize(loss, global_step=global_step)
            
            tf.summary.scalar('cost', loss)
            summary_op = tf.summary.merge_all()
            init_op = tf.global_variables_initializer()
        # The StopAtStepHook handles stopping after running given steps.
        hooks = [ tf.train.StopAtStepHook(last_step=1000)]
        # The MonitoredTrainingSession takes care of session initialization,
        # restoring from a checkpoint, saving to a checkpoint, and closing when done
        # or an error occurs.
        config = tf.ConfigProto(intra_op_parallelism_threads=2, inter_op_parallelism_threads=2);
        with tf.train.MonitoredTrainingSession(master="grpc://" + worker_hosts[FLAGS.task_index],
                                               is_chief=(FLAGS.task_index==0), # 我们制定task_index为0的任务为主任务，用于负责变量初始化、做checkpoint、保存summary和复原
                                               checkpoint_dir="model",
                                               save_checkpoint_secs=None,
                                               config=config,
                                               hooks=hooks) as mon_sess:
            while not mon_sess.should_stop():
                # Run a training step asynchronously.
                # See `tf.train.SyncReplicasOptimizer` for additional details on how to
                # perform *synchronous* training.
                # mon_sess.run handles AbortedError in case of preempted PS.
                train_x = np.random.rand(100).astype(np.float32)
                train_y = train_x * 0.1 + 0.3
                _, step, loss_v, weight, biase = mon_sess.run([train_op, global_step, loss, W, b], feed_dict={x_data: train_x, y_data: train_y})
                if step % 100 == 0:
                    print("step: %d, weight: %f, biase: %f, loss: %f" %(step, weight, biase, loss_v))
            print("Optimization finished.")

if __name__ == "__main__":
    tf.app.run()

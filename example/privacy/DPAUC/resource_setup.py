import os
import tensorflow as tf


def setup_gpu(gpu_option, device_number=0):
    if gpu_option:
        
        # """
        # Level | Level for Humans | Level Description
        # -------|------------------|------------------------------------
        # 0     | DEBUG            | [Default] Print all messages
        # 1     | INFO             | Filter out INFO messages
        # 2     | WARNING          | Filter out INFO & WARNING messages
        # 3     | ERROR            | Filter out all messages
        # """

        #remove tensorflow INFO messages
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  
        gpus = tf.config.experimental.list_physical_devices('GPU')
        print("Num GPUs Available: ", len(gpus))
        if gpus:
            # Restrict TensorFlow to only use the first GPU
            try:
                tf.config.experimental.set_visible_devices(
                    gpus[device_number], 'GPU')
                tf.config.experimental.set_memory_growth(
                    gpus[device_number], True)

            except RuntimeError as e:
                # Visible devices must be set at program startup
                print(e)
    else:
        print('Using CPU')
        os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
        tf.config.experimental.set_visible_devices([], 'GPU')

    print("using GPUs:")
    print(tf.config.experimental.get_visible_devices('GPU'))

    return tf.config.experimental.get_visible_devices('GPU')

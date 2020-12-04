## Introduction

Here, we show how to use our embedding protection framework with FMNIST as an example.
Technical details can be seen in our technical report.

## Usage 
### Requirements
* Tensorflow 2.x
* Python 3.x

### Important parameters

* ```reconstruction_loss_weight```: adversarial reconstructor weight
* ```log_distance_correlation```: log distance correlation or not
* ```distance_correlation_weight```: distance correlation weight
* ```reconstruction_stablizer_noise_weight```: noise regularization weight
* ```grl```: grl weight
* ```sigmoid```: use sigmoid as activation at the last layer
* ```noise_stddev```: standard deviation of the Gaussian noise added to the split layer

#### Baseline: Without any Protection

* ```python FMNIST_Embedding_Protection_Framework_Demo.py --reconstruction_loss_weight 1.0 --distance_correlation_weight 0.0 --reconstruction_stablizer_noise_weight 0.0 --grl 0.0  --batch_size 200  --dis_lr 1e-4 --gpu_option --gpu_id 0 --sigmoid --num_epochs 10```

#### Baseline: Adding Gaussian Noise to the Split Layer

* set ```--grl 0.0``` and ```--noise_stddev 100.0```
* ```python FMNIST_Embedding_Protection_Framework_Demo.py  --reconstruction_loss_weight 1.0 --grl 0.0 --noise_stddev 10.0 --batch_size 200 --num_epochs 10 --dis_lr 1e-4 --gpu_option --gpu_id 3 --sigmoid```

#### Minimizing Distance Correlation Module

##### Use log distance correlation

* set ```--distance_correlation_weight 100.0 --log_distance_correlation --grl 0.0```
* ```python FMNIST_Embedding_Protection_Framework_Demo.py --reconstruction_loss_weight 1.0 --distance_correlation_weight 100.0 --log_distance_correlation --grl 0.0  --batch_size 200  --dis_lr 1e-4 --gpu_option --gpu_id 0 --sigmoid --num_epochs 10```

##### Use distance correlation

* set ```--distance_correlation_weight 100.0 --grl 0.0```
* ```python FMNIST_Embedding_Protection_Framework_Demo.py --reconstruction_loss_weight 1.0 --distance_correlation_weight 100.0  --grl 0.0  --batch_size 200  --dis_lr 1e-4 --gpu_option --gpu_id 0 --sigmoid --num_epochs 10```

#### Noise Regularization Module 

* set ```--grl 0.0``` and ```--reconstruction_stablizer_noise_weight 1.0```

* ```python FMNIST_Embedding_Protection_Framework_Demo.py --reconstruction_loss_weight 1.0 --reconstruction_stablizer_noise_weight 1.0 --distance_correlation_weight 0.0 --grl 0.0  --batch_size 200  --dis_lr 1e-4 --gpu_option --gpu_id 6 --num_epochs 10 --sigmoid```

##### Adversarial Reconstructor

##### With clippling gradient norm of the GRL 

* set ```--grl -1.0  --clip_norm 0.1```
* ```python FMNIST_Embedding_Protection_Framework_Demo.py --reconstruction_loss_weight 1.0 --distance_correlation_weight 0.0 --grl -1.0  --reconstruction_stablizer_noise_weight 1.0 --clip_norm 0.1 --batch_size 200  --dis_lr 1e-4 --gpu_option --gpu_id 0 --sigmoid --num_epochs 10```

##### without clippling gradient norm of the GRL 

* set ```--grl -1.0```
* ```python FMNIST_Embedding_Protection_Framework_Demo.py --reconstruction_loss_weight 1.0 --distance_correlation_weight 0.0 --grl -1.0  --reconstruction_stablizer_noise_weight 0.0  --batch_size 200  --dis_lr 1e-4 --gpu_option --gpu_id 0 --sigmoid --num_epochs 10```

#### Adversarial Reconstructor and Noise Regularization Module

* set ```--grl -1.0``` and ```--reconstruction_stablizer_noise_weight 1.0```
* ```python FMNIST_Embedding_Protection_Framework_Demo.py --reconstruction_loss_weight 1.0 --reconstruction_stablizer_noise_weight 1.0 --distance_correlation_weight 0.0 --grl -1.0  --batch_size 200  --dis_lr 1e-4 --gpu_option --gpu_id 6 --num_epochs 10 --sigmoid```

#### Adversarial Reconstructor, Noise Regularization, and Distance Correlation Module
* set ```--grl -1.0```, ```--reconstruction_stablizer_noise_weight 1.0```, and ```--distance_correlation_weight 100.0```
* ```python FMNIST_Embedding_Protection_Framework_Demo.py --reconstruction_loss_weight 1.0 --reconstruction_stablizer_noise_weight 1.0 --distance_correlation_weight 1000.0 --grl -1.0  --batch_size 200  --dis_lr 1e-4 --gpu_option --gpu_id 6 --num_epochs 10 --sigmoid```
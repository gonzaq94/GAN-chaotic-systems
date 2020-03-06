# GAN-chaotic-systems

GAN - Steps to follow:

1) Implement the GAN to generate series of length 100 for the three coordinates (total length 3*100) with just noise as an input. The initial condition is not set and we just use Dense layers.
2) For adding the fact that the output is actually a temporal series, we add LSTM layers to the model.
3) Add the constraint that the generated series should start at a given initial condition. Idea: just have as input of the networkk the initial condition and hardcode it as first value of the output of the network. As we are using LSTMs, this value will be taken into account for the series generation.

Sparse regression

1) Perform the local regression

Evaluation 

1) Fin evaluation metrics that are specific for chaotic systems.

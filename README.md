<h1>GANs for chaotic systems</h1>


In this repository you will find the application of Generative Adversarial Networks (GANs) for the generation of data coming from the Loretnz-63 model, a chatoic model used to describe atmospheric convection. This generated data could be used after for training machine learning models.

Regression methods are also applied for characterizing the model (retrieving its parameters) and reproducing realistic data. 

__Authors: Gonzalo Quintana, Gustavo Rodrigues dos Reis and Santiago Agudelo.__

### Files and folders:

`CNN GAN.ipynb`: contains the final GAN architecture using CNNs

`GAN FC and LSTM.ipynb`: GANs implementing fully connected layers and LSTMs. They didn't result in good performances.

`DSG.ipynb`: Problem introduction, data generation and simple and local linear regression.

`FirstPartRegression.ipynb`: more sophisticated regression methods (Ridge, Lasso, etc.) and Lyapunov exponent (characterization of a dynamic system).

`Experiments`: contains experiments with CNN GANs that didn't result in better performances.

`Models`: trained generator and discriminator that reached the best performances.

### CNN GAN architecture:

![](images/GAN_architecture.png)

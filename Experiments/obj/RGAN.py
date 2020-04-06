#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from keras import backend
from .model_utils import save_model
from keras.models import Model
from keras.optimizers import Adam
from keras.constraints import max_norm
from keras.layers import Dense, Activation, Reshape
from keras.layers import LSTM, CuDNNLSTM, Input, Bidirectional
from keras.layers import BatchNormalization, LeakyReLU, Dropout, UpSampling2D
from .spec_norm.SpectralNormalizationKeras import ConvSN2D, DenseSN
from keras.backend.tensorflow_backend import clear_session

class RGAN():
    """ Class definition for RGAN """
    def __init__(self,latent_dim=100,im_dim=28,epochs=100,batch_size=256,
                 learning_rate=0.0004,g_factor=0.25,droprate=0.25,
                 momentum=0.8,alpha=0.2,saving_rate=10):
        """
        Initialize RGAN with model parameters

        Args:
            latent_dim (int): latent dimensions of generator
            im_dim (int): square dimensionality of images
            epochs (int): maximum number of training epochs
            batch_size (int): batch size for stochastic gradient descent
            learning_rate (float): learning rate for stochastic gradient descent,
            particularly for the discriminator
            g_factor (float): learning rate for generator =
            g_factor*learning_rate, which is defined above
            droprate (float): dropout-rate used within the model
            momentum (float): momentum used in batch normalization
            alpha (float): alpha used in leaky relu
            saving_rate (int): epoch interval when model is saved
        """
        # define and store local variables
        clear_session()
        self.latent_dim = latent_dim
        self.im_dim = im_dim
        self.epochs = epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate
        self.g_factor = g_factor
        self.optimizer_d = Adam(self.learning_rate)
        self.optimizer_g = Adam(self.learning_rate*self.g_factor)
        self.droprate = droprate
        self.momentum = momentum
        self.alpha = alpha
        self.saving_rate = saving_rate
        # define and compile discriminator
        self.discriminator = self.getDiscriminator(self.im_dim,self.droprate,
                                                   self.momentum,self.alpha)
        self.discriminator.compile(loss=['binary_crossentropy'],
                                   optimizer=self.optimizer_d)
        # define generator
        self.generator = self.getGenerator(self.latent_dim,self.momentum,
                                           self.alpha)
        self.discriminator.trainable = False
        # define combined network with partial gradient application
        z = Input(shape=(self.latent_dim,))
        img = self.generator(z)
        validity = self.discriminator(img)
        self.combined = Model(z, validity)
        self.combined.compile(loss=['binary_crossentropy'],
                              optimizer=self.optimizer_g)

    def getGenerator(self,latent_dim,momentum,alpha):
        """
        Initialize generator model

        Args:
            latent_dim (int): latent dimensions of generator
            momentum (float): momentum used in batch normalization
            alpha (float): alpha used in leaky relu

        Returns:
            (keras.models.Model): keras model for generator
        """
        in_data = Input(shape=(latent_dim,))
        # block 1: upsampling using dense layers
        out = DenseSN(128*64*3)(in_data)
        print(out.shape)
        out = LeakyReLU(alpha=alpha)(out)
        out = Reshape((8,8,128*3))(out)
        
        print(out.shape)
        # block 2: convolution
        out = ConvSN2D(256*3, kernel_size=3, padding="same")(out)
        out = BatchNormalization(momentum=momentum)(out)
        out = LeakyReLU(alpha=alpha)(out)
        print(out.shape)

        # block 3: upsampling and convolution
        out = UpSampling2D()(out)
        out = ConvSN2D(128*3, kernel_size=3, padding="same")(out)
        out = BatchNormalization(momentum=momentum)(out)
        out = LeakyReLU(alpha=alpha)(out)
        print(out.shape)

        # block 4: upsampling and convolution
        out = UpSampling2D()(out)
        out = ConvSN2D(64*3, kernel_size=4, padding="same")(out)
        out = BatchNormalization(momentum=momentum)(out)
        out = LeakyReLU(alpha=alpha)(out)
        print(out.shape)
        

        # block 5: flatten and enrich string features using LSTM
        out = Reshape((32*32,64*3))(out)
        if len(backend.tensorflow_backend._get_available_gpus()) > 0:
            out = CuDNNLSTM(32*3,return_sequences=True,
                       kernel_constraint=max_norm(3),
                       recurrent_constraint=max_norm(3),
                            bias_constraint=max_norm(3))(out)
        else:
            out = LSTM(32*3,return_sequences=True,
                       kernel_constraint=max_norm(3),
                       recurrent_constraint=max_norm(3),
                       bias_constraint=max_norm(3))(out)
        print(out.shape)
        out = Reshape((32,32,32*3))(out)

        # block 6: continuous convolutions for smoother features
        out = ConvSN2D(32*3, kernel_size=3, padding="same")(out)
        out = BatchNormalization(momentum=momentum)(out)
        print(out.shape)
        
        out = ConvSN2D(32*3, kernel_size=3, padding="same")(out)
        out = BatchNormalization(momentum=momentum)(out)
        print(out.shape)
        
        out = ConvSN2D(1*3, kernel_size=3, padding="same")(out)
        out = BatchNormalization(momentum=momentum)(out)
        out = LeakyReLU(alpha=alpha)(out)
        print(out.shape)
        
        out = Reshape((32,32,3))(out)
        print(out.shape)
        return Model(inputs=in_data,outputs=out)

    def getDiscriminator(self,im_dim,droprate,momentum,alpha):
        """
        Initialize discriminator model

        Args:
            im_dim (int): square dimensionality of images
            droprate (float): dropout-rate used within the model
            momentum (float): momentum used in batch normalization
            alpha (float): alpha used in leaky relu

        Returns:
            (keras.models.Model): keras model for discriminator
        """
        in_data = Input(shape=(im_dim,im_dim,3))
        out = Reshape((im_dim,im_dim,3))(in_data)
        out = ConvSN2D(1*3, kernel_size=3, padding="same")(out)
        out = BatchNormalization(momentum=momentum)(out)
        out = LeakyReLU(alpha=alpha)(out)
        out = Dropout(droprate)(out)
        # block 1: flatten and check sequence using LSTM
        out = Reshape((im_dim**2,3))(out)
        if len(backend.tensorflow_backend._get_available_gpus()) > 0:
            out = CuDNNLSTM(1*3,return_sequences=True,
                       kernel_constraint=max_norm(3),
                       recurrent_constraint=max_norm(3),
                            bias_constraint=max_norm(3))(out)
        else:
            out = LSTM(1*3,return_sequences=True,
                       kernel_constraint=max_norm(3),
                       recurrent_constraint=max_norm(3),
                       bias_constraint=max_norm(3))(out)
        out = Reshape((im_dim,im_dim,1*3))(out)
        # block 2: convolution with dropout
        out = ConvSN2D(256, kernel_size=3, strides=2)(out)
        out = BatchNormalization(momentum=momentum)(out)
        out = LeakyReLU(alpha=alpha)(out)
        out = Dropout(droprate)(out)
        # block 3: convolution with dropout
        out = ConvSN2D(128, kernel_size=3, strides=2)(out)
        out = BatchNormalization(momentum=momentum)(out)
        out = LeakyReLU(alpha=alpha)(out)
        out = Dropout(droprate)(out)
        # block 4: convolution with dropout
        out = ConvSN2D(64, kernel_size=3)(out)
        out = BatchNormalization(momentum=momentum)(out)
        out = LeakyReLU(alpha=alpha)(out)
        out = Dropout(droprate)(out)
        # block 5: flatten and detect final features using bi-LSTM
        out = Reshape((5*5,64))(out)
        if len(backend.tensorflow_backend._get_available_gpus()) > 0:
            out = Bidirectional(CuDNNLSTM(8,
                       kernel_constraint=max_norm(3),
                       recurrent_constraint=max_norm(3),
                                          bias_constraint=max_norm(3)))(out)
        else:
            out = Bidirectional(LSTM(8,
                       kernel_constraint=max_norm(3),
                       recurrent_constraint=max_norm(3),
                                     bias_constraint=max_norm(3)))(out)
        # block 6: map final features to dense output
        out = Dense(1)(out)
        out = Activation("sigmoid")(out)
        return Model(inputs=in_data,outputs=out)

    def _plot_figures(self,figures,direct,epoch,dim=1):
        """
        Plot a dictionary of figures, adapted from:
        https://stackoverflow.com/questions/11159436/multiple-figures-in-a-single-window

        Args:
            figures (dict): contains titles (keys) and figures (values)
            direct (str): log directory to save plot
            epoch (int): current epoch for plot
            dim (int): square dimensionality of plot
        """
        fig, axeslist = plt.subplots(ncols=dim, nrows=dim)
        for ind,title in enumerate(figures):
            axeslist.ravel()[ind].imshow(figures[title], cmap=plt.gray())
            axeslist.ravel()[ind].set_title(title)
            axeslist.ravel()[ind].set_axis_off()
        plt.tight_layout()
        fig.savefig("./pickles/"+direct+"/img/epoch"+str(epoch+1)+".png",
                    format='png', dpi=500)
        fig.clear()
        plt.close("all")

    def train(self,data,direct,sq_dim=4,check_rate=20):
        """
        Train RGAN model

        Args:
            data (numpy.ndarray): numpy array of training data
            direct (str): log-directory to store model
            sq_dim (int): square dimensionality of model plot
            check_rate (int): epoch interval to log performance
        """
        plot_samples=sq_dim**2
        data_type = re.sub(r".*_","",direct)
        dict_field = {"data":data_type}
        dict_field.update({el[0]:el[1] for el in self.__dict__.items()
                           if type(el[1]) in
                           [int,str,float,np.int64,np.float64]})
        fieldnames = list(dict_field.keys())
        # write init.csv to file for future class reconstruction
        with open("./pickles/"+direct+"/init.csv", "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(dict_field)
        fieldnames = ["epoch", "batch", "d_loss", "g_loss"]
        with open("./pickles/"+direct+"/log.csv", "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
        # generate constant noise vector for model comparisons
        np.random.seed(42)
        constant_noise = np.random.normal(size=(plot_samples,self.latent_dim,))
        np.random.seed(None)
        # label smoothing by using less-than-one value
        fake_labels = np.zeros((self.batch_size,1))
        runs = int(np.ceil(data.shape[0]/self.batch_size))
        for epoch in range(self.epochs):
            # make noisy labels per epoch
            real_labels = np.clip(np.random.normal(loc=0.90,
                                                   scale=0.005,size=
                                                   (self.batch_size,1)),None,1)
            for batch in range(runs):
                # randomize data and generate noise
                idx = np.random.randint(0,data.shape[0],self.batch_size)
                real = data[idx]
                noise = np.random.normal(size=
                                         (self.batch_size,self.latent_dim,))
                # generate fake data
                fake = self.generator.predict(noise)
                # train the discriminator
                d_loss_real = self.discriminator.train_on_batch(real,
                                                                real_labels)
                d_loss_fake = self.discriminator.train_on_batch(fake,
                                                                fake_labels)
                d_loss = 0.5 * np.add(d_loss_real, d_loss_fake)
                # generate new set of noise
                noise = np.random.normal(size=(self.batch_size,
                                               self.latent_dim,))
                # train generator while freezing discriminator
                g_loss = self.combined.train_on_batch(noise, real_labels)
                # plot the progress
                if (batch+1) % check_rate == 0:
                    print("epoch: %d [batch: %d] [D loss: %f] [G loss: %f]" %
                          (epoch+1,batch+1,d_loss,g_loss))
                    with open("./pickles/"+direct+"/log.csv", "a") as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writerow({"epoch":str(epoch+1),
                                         "batch":str(batch+1),
                                         "d_loss":str(d_loss),
                                         "g_loss":str(g_loss)})
            # at every epoch, generate images for reference
            test_img = self.generator.predict(constant_noise)
            test_img = (0.5*test_img)+0.5
            np.save("./pickles/"+direct+"/img/epoch"+str(epoch+1),test_img)

            test_img = {str(i+1):test_img[i] for i in range(test_img.shape[0])}
            self._plot_figures(test_img,direct,epoch,sq_dim)
            if (epoch+1) % self.saving_rate == 0 or (epoch+1) == self.epochs:
                # save models with defined periodicity
                save_model(self,direct)

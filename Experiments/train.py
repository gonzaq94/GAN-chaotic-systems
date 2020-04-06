#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pickle
import sys
import re
import pandas as pd
import argparse
import datetime
import numpy as np
from obj.RGAN import RGAN
from obj.RCGAN import RCGAN
from obj.model_utils import restore_model
from obj.arg_formatter import arg_metav_formatter
from keras.utils import plot_model
from keras.datasets import mnist, fashion_mnist,cifar10

def getCurrentTime():
    """
    Function to provide a date-time string for logging

    Returns:
        (str): date-time string
    """
    return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

def loadData(data,model):
    """
    Function to load data for model training

    Args:
        data (str): type of data to process, can be either "mnist",
        "fashion" or "faces"
        model (str): type of model to use, either "RGAN" or "RCGAN"

    Returns:
        X_train (numpy.ndarray): training data as numpy arrays
        y_train (numpy.ndarray): training labels as numpy arrays
    """
    if data == "faces":
        return np.load("./data/lfwcrop_grey/lfw.npy")
    elif data == "mnist":
        train_set, _ = mnist.load_data()
    elif data == "fashion":
        train_set, _ = fashion_mnist.load_data()
    elif data == "cifar10":
        train_set, _ = cifar10.load_data()
    elif data == "lorenz":
        X_train = np.load('lorenz_63_data_different_x_0.npy').astype(np.float32)
    # return data type based on model
    #X_train = ((train_set[0]-127.5)/127.5).astype(np.float32)
    #y_train = train_set[1]
    if model == "RGAN":
        return X_train
    elif model == "RCGAN":
        return X_train,y_train

def singularTrain(model_name,data,latent_dim,epochs,batch_size,learning_rate,
                  g_factor,droprate,momentum,alpha,saving_rate):
    """
    Function to train and save model

    Args:
        model_name (str): type of model to use, either "RGAN" or "RCGAN"
        data (str): type of data to process, can be either "mnist",
        "fashion" or "faces"
        latent_dim (int): latent dimensions of generator
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
    train_images = loadData(data,model_name)
    log_dir = getCurrentTime()+"_"+model_name+"_"+data
    os.makedirs("./pickles/"+log_dir)
    os.makedirs("./pickles/"+log_dir+"/img")
    if model_name == "RGAN":
        im_dim = train_images.shape[1]

        model = RGAN(latent_dim,im_dim,epochs,batch_size,learning_rate,
                     g_factor,droprate,momentum,alpha,saving_rate)
    elif model_name == "RCGAN":
        im_dim = train_images[0].shape[1]
        num_classes = np.unique(train_images[1]).shape[0]
        model = RCGAN(num_classes,latent_dim,im_dim,epochs,
                      batch_size,learning_rate,
                      g_factor,droprate,momentum,alpha,saving_rate)
    model.train(train_images,log_dir)

def continueTrain(direct,arguments):
    """
    Function to continue training a saved model, and later re-save it

    Args:
        direct (str): base directory containing model
        arguments (dict): dictionary containing keys with names of arguments
        above in "singularTrain", values for keys are determined via
        command-line parser
    """
    direct = re.sub(r"(\/)?$","",direct)
    direct = re.sub(r"(\.\/)?pickles\/","",direct)
    directLong = "./pickles/"+direct
    if not os.path.isdir(directLong):
        sys.exit(directLong +" does not exist")
    model_name = re.sub(r".*(R(C)?GAN).*","\g<1>",direct)
    # read init.csv and return construction parameters
    meta = pd.read_csv(directLong+"/init.csv")
    # remove "until" in case file is a combined type
    toParse = set(meta.columns)-set(arguments.keys())-{"until"}
    # add arguments given as variables in memory
    globals().update(arguments)
    # read remaining variables which must be parsed
    # read from last row of init.csv in case file has been combined
    rem = {el:meta.iloc[-1][el] for el in toParse}
    # add arguments parsed into memory
    globals().update(rem)
    train_set = loadData(data,model_name)
    # create new log directory depending on left-off training state
    if "_" not in re.sub(r".*_R(C)?GAN_","",direct):
        log_dir = re.sub(r"(R(C)?GAN_)","\g<1>"+getCurrentTime()+"_",directLong)
        log_dir_pass = re.sub("./pickles/","",log_dir)
    else:
        temp = re.sub(r"(.*)(_R(C)?GAN_)(.*)(_(.*)$)","\g<4>\g<2>\g<6>",direct)
        log_dir_pass = re.sub(r"(R(C)?GAN_)","\g<1>"+getCurrentTime()+"_",temp)
        log_dir = "./pickles/"+log_dir_pass
    os.makedirs(log_dir)
    os.makedirs(log_dir+"/img")
    # create randomized model
    if model_name == "RGAN":
        model = RGAN(latent_dim,im_dim,epochs,batch_size,learning_rate,
                     g_factor,droprate,momentum,alpha,saving_rate)
    elif model_name == "RCGAN":
        model = RCGAN(num_classes,latent_dim,im_dim,epochs,
                      batch_size,learning_rate,
                     g_factor,droprate,momentum,alpha,saving_rate)
    # restore original model
    model = restore_model(model,train_set,model_name,
                          directLong,log_dir_pass)
    # resume training
    model.train(train_set,log_dir_pass)

def plot_M(model):
    """
    Function to plot model graph

    Args:
        model (str): type of model to plot, either "RGAN" or "RCGAN"
    """
    if model == "RGAN":
        model = RGAN()
    elif model == "RCGAN":
        model = RCGAN(num_classes=10)
    plot_model(model.generator,to_file="./img/gen.png",show_shapes=True)
    plot_model(model.discriminator,to_file="./img/dis.png",show_shapes=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=
                                     arg_metav_formatter)
    parser.add_argument("--model", type=str, default="RGAN",
                        help="which model to use; either RGAN or RCGAN")
    parser.add_argument("--data", type=str, default="lorenz",
                        help="which training data to use;"+
                        " either mnist, fashion or faces")
    parser.add_argument("--latent-dim", type=int, default=300,
                        help="latent dimensionality of GAN generator")
    parser.add_argument("--epochs", type=int, default=1000,
                        help="number of training epochs")
    parser.add_argument("--batch-size", type=int, default=256,
                        help="batch size for stochastic"+
                        " gradient descent optimization")
    parser.add_argument("--learning-rate", type=float, default=0.0004,
                        help="learning rate for stochastic"+
                        " gradient descent optimization")
    parser.add_argument("--g-factor", type=float, default=0.25,
                        help="factor by which generator optimizer"+
                        " scales discriminator optimizer")
    parser.add_argument("--droprate", type=float, default=0.25,
                        help="droprate used in GAN discriminator"+
                        " for generalization/robustness")
    parser.add_argument("--momentum", type=float, default=0.8,
                        help="momentum used across GAN batch-normalization")
    parser.add_argument("--alpha", type=float, default=0.2,
                        help="alpha parameter used in leaky relu")
    parser.add_argument("--saving-rate", type=int, default=10,
                        help="epoch period on which the model"+
                        " weights should be saved")
    parser.add_argument("--continue-train", default=False, action="store_true",
                        help="option to continue training model within log"+
                        " directory; requires --log-dir option to be defined")
    if "--continue-train" in sys.argv:
        required = parser.add_argument_group("required name arguments")
        required.add_argument("--log-dir", required=True, type=str,
                        help="log directory within ./pickles/ whose model"+
                              " should be further trained, only required when"+
                              " --continue-train option is specified")
    else:
        parser.add_argument("--log-dir", required=False, type=str,
                        help="log directory within ./pickles/ whose model"+
                            " should be further trained, only required when"+
                            " --continue-train option is specified")
    parser.add_argument("--plot-model", default=False, action="store_true",
                        help="option to plot keras model")
    args = parser.parse_args()
    assert args.data in ["faces","mnist","fashion","cifar10","lorenz"]
    assert args.model in ["RGAN","RCGAN"]
    if args.model == "RCGAN" and args.data == "faces":
        raise ValueError("Face generation not integrated with RCGAN")
    if args.plot_model:
        plot_M(args.model)
        sys.exit()
    elif args.continue_train:
        # parse specified arguments as kwargs to continueTrain
        arguments = [el for el in sys.argv[1:] if el != "--continue-train"]
        todel = [i for i in range(len(arguments))
                 if arguments[i] == "--log-dir"]
        for i in sorted(todel, reverse=True):
            del arguments[i:i+2]
        arguments = [re.sub("-","_",re.sub("--","",arguments[i]))
                     if i%2 == 0 else
                     arguments[i] for i in range(len(arguments))]
        arguments = dict(zip(arguments[::2], arguments[1::2]))
        for key in arguments.keys():
            check = str(type(getattr(args,key)))
            if "int" in check:
                arguments[key] = int(arguments[key])
            elif "str" in check:
                arguments[key] = str(arguments[key])
            elif "float" in check:
                arguments[key] = float(arguments[key])
        continueTrain(args.log_dir,arguments)
    else:
        singularTrain(args.model,args.data,args.latent_dim,args.epochs,
                      args.batch_size,args.learning_rate,args.g_factor,
                      args.droprate,args.momentum,args.alpha,args.saving_rate)

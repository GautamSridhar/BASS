#Author: Gautam Reddy Nallamala. Email: gautam_nallamala@fas.harvard.edu
#Packaged by: Gautam Sridhar, Email: gautam.sridhar@icm-institute.org

#This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. 
#To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/ or send a letter to Creative Commons, 
#PO Box 1866, Mountain View, CA 94042, USA.

# Use as example script to learn the parameters of the gmm and to visualize the bout types and their kinematics
# Datasets of multiple conditions should be of size nbouts x nfeatures
# In addition storing the tail angles can be useful in order to visualize the bout types found
# Recfactoring analyze_kinematics() to suit specific datasets can help with the visualization of the bout types 


import argparse
import sys
sys.path.append('./BASS/')
sys.path.append('./Utils/')
import os
import time
#data format library
#numpy and scipy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
#data processing functions
import data_processing_zz as dp
from GMM import GMM_model


def train(args, datasets, n_cluster,split_size=40000, savename="acid", mode = 'learn'):
    """
    Learn a GMM on datasets with a set number of clusters and save the parameters:

    Parameters:
    args: Argparse object containing general arguments
    datasets: A list of datasets over which to learn GMM. Size of list should be number of conditions/experiments
              Each dataset in the list should be num_bouts x n_features..
    n_cluster: Chosen number of clusters. default type - int
    savename: Name of the parameters to be saved/loaded
    mode: If 'learn' then train the GMM on the dataset, if 'load' then load a previously saved model.
    """

    model_fit = GMM_model(n_cluster) 
    if mode == 'learn':
        length_min = np.min([len(data) for data in datasets])
        datasets_train = np.zeros((len(datasets),split_size,datasets[0].shape[1])) # 3d array for subsampled dataset

        for s in range(len(datasets)):
            subsample = np.random.choice(len(datasets[s]),split_size)
            datasets_train[s] = datasets[s][subsample]

        model_fit.solve(datasets_train)
        model_fit._save_params(args.Out + savename)

        return model_fit

    elif mode == 'load':
        means_ = np.load(args.Out + savename + "_means.npy")
        covars_ = np.load(args.Out + savename + "_covars.npy")
        weights_ = np.load(args.Out + savename + "_weights.npy")
        model_fit._read_params(means_,covars_,weights_)

        return model_fit


def val(args, datasets,clusters,split_size,n_reps):
    """
    Train a Gaussian Mixture models and plot the log likelihood for selected range of clusters in order to select the number of clusters

    Parameters:
    args: Argparse object containing general arguments
    datasets: A list of datasets over which to learn GMM. Size of list should be number of conditions/experiments
              Each dataset in the list should be num_bouts x n_features.
    clusters: a list/numpy array of the range of clusters to test upon
    split_size: the number of training samples to choose in your dataset
    n_reps: Number of repititions to perform for error bars
    """

    np.random.seed(args.Seed)
    LLs = []
    for i in clusters:
        print('clusters = ',i)
        LLs += [[]]
        for j in range(n_reps):
            print('iter = ', j)
            model_fit = GMM_model(i)
            length_min = np.min([len(data) for data in datasets])

            datasets_train = np.zeros((len(datasets),split_size,datasets[0].shape[1])) # 3d array for subsampled dataset
            datasets_test = np.zeros((len(datasets),length_min - split_size,datasets[0].shape[1]))
            
            for s in range(len(datasets)):
                subsample = np.random.choice(len(datasets[s]),split_size)
                datasets_train[s] = datasets[s][subsample]
                datasets_test[s] = np.delete(datasets[s],subsample,axis=0)[:length_min - split_size]

            model_fit.solve(datasets_train)
            LLs[-1] += [model_fit.LL(datasets_test)]

    #Held-out log likelihood
    plt.close("all")
    fig,axis = plt.subplots(1,1,figsize = (4,3))
    for i,ll in enumerate(LLs):
        axis.errorbar(clusters[i],-np.mean(ll),fmt='ko',yerr = np.std(ll))
    
    axis.tick_params(labelsize = 18)
    axis.spines['top'].set_linewidth(1.25)
    axis.spines['left'].set_linewidth(1.25)
    axis.spines['bottom'].set_linewidth(1.25)
    axis.spines['right'].set_linewidth(1.25)

    axis.set_xlabel("Number of clusters", fontsize = 18)
    axis.set_ylabel("Held-out log likelihood", fontsize = 18)
    fig.tight_layout()
    plt.savefig(args.Out + "figure_heldout_LL.png")


def analyze_kinematics(args, datasets, tail_angles ,model_fit):
    """
    If the data was extracted from Zebrazoom, use this function to analyze average kinematics of individual bout types

    Parameters:
    args: Argparse object containing general arguments
    datasets: A list of datasets over which to learn GMM. Size of list should be number of conditions/experiments
              Each dataset in the list should be num_bouts x n_features.
    tail_angles: A list containing raw tail angles for each dataset. Size of list should be number of condition/experiments
                 Each dataset in the list should be num_bouts x num_frames x num_points
    model_fit: gmm model to be analyzed
    """

    speeds = []
    deltaheads = []
    tails = []

    ta = tail_angles[args.Condition]
    data = datasets[args.Condition]
    n_cluster = len(model_fit.means_)

    for i in range(n_cluster):
        speeds += [[]]
        deltaheads += [[]]
        tails += [[]]

    states = np.argmax(model_fit._compute_posterior(data,args.Condition),axis=0)
    for i,state in enumerate(states):
        speeds[state] += [data[i,1]]
        deltaheads[state] +=  [data[i,0]]
        tails[state] += [ta[i,:,0]]

    fig1,axis1= plt.subplots(1,1,figsize = (4,3))
    fig2,axis2= plt.subplots(1,1,figsize = (4,3))

    for state in np.arange(n_cluster):
    
        n,bins = np.histogram(speeds[state], bins = np.linspace(0,35,20), density = True)
        bins = 0.5*(bins[1:] + bins[:-1])
        axis1.plot(bins, n,'C%do-'%state, ms = 2)
        
        n,bins = np.histogram(deltaheads[state], bins = np.linspace(0,150,20), density = True)
        bins = 0.5*(bins[1:] + bins[:-1])
        axis2.plot(bins, n,'C%do-'%state, ms = 2)
    
        fg,ax=plt.subplots(1,1,figsize = (3,2))
        arr = np.array(tails[state])
        arrs_fil0 = arr[np.mean(arr,axis=1) > 0]
        arrs_fil1 = arr[np.mean(arr,axis=1) < 0]
    
        for num in range(200):
            ax.plot(np.arange(len(arrs_fil0[num]))*1e3/160.,arrs_fil0[num] * (180 / np.pi),'k-',alpha = 0.01)
        ax.plot(np.arange(len(arrs_fil0[0]))*1e3/160.,np.mean(arrs_fil0,axis=0)* (180/ np.pi),'C%d'%state,lw = 4)
 
        ax.set_ylim(-20,70)
        ax.tick_params(labelsize = 20)
        ax.spines['top'].set_linewidth(1.25)
        ax.spines['left'].set_linewidth(1.25)
        ax.spines['bottom'].set_linewidth(1.25)
        ax.spines['right'].set_linewidth(1.25)
        ax.set_xlabel("Time (ms)", fontsize = 20)
        ax.set_ylabel(r"Tail angle($^o$)", fontsize = 20)
        fg.tight_layout()
        fg.savefig(args.Out + "figure_tailangles_clusters_tailanglespca_kin_{}_condition{}.png".format(state,args.Condition))
        print(np.mean(speeds[state]),np.mean(deltaheads[state]), model_fit.weights_[:,state])

    axis1.tick_params(labelsize = 24)
    axis1.spines['top'].set_linewidth(1.25)
    axis1.spines['left'].set_linewidth(1.25)
    axis1.spines['bottom'].set_linewidth(1.25)
    axis1.spines['right'].set_linewidth(1.25)
    axis1.set_xlabel("Speed (mm/s)",fontsize = 24)
    axis1.set_ylabel("PDF",fontsize = 24)
    fig1.tight_layout()

    axis2.tick_params(labelsize = 24)
    axis2.spines['top'].set_linewidth(1.25)
    axis2.spines['left'].set_linewidth(1.25)
    axis2.spines['bottom'].set_linewidth(1.25)
    axis2.spines['right'].set_linewidth(1.25)
    axis2.set_xlabel("Delta heading (deg)",fontsize = 24)
    axis2.set_ylabel("PDF",fontsize = 24)
    fig2.tight_layout()

    fig1.savefig(args.Out + "speed_clusters_tailanglesPCA_and_kin_condition{}.png".format(args.Condition))
    fig2.savefig(args.Out + "deltahead_clusters_tailanglesPCA_and_kin_condition{}.png".format(args.Condition))


def main(args):

    datasets = []
    tail_angles = []

    datapath = args.Dataout + "data_"
    tapath = args.Dataout + "tailangles_"

    for n in range(args.Numdata):
        datasets.append(np.load(datapath + "condition{}.npy".format(n)))
        tail_angles.append(np.load(tapath + "condition{}.npy".format(n)))

    if args.Type == 'train' :
        model_fit = train(args, datasets, args.N_cluster, split_size=40000, savename = args.Savename, mode = args.Mode)

        # Comment out if using a dataset not extracted using Zebrazoom
        analyze_kinematics(args, datasets, tail_angles, model_fit)

    elif args.Type ==  'val':
        clusters = np.arange(3,11)
        val(args, datasets, clusters, split_size=40000, n_reps=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-seed','--Seed',help="Seed for data extraction", default=42,type=int)
    parser.add_argument('-numdata','--Numdata',help="Number of datasets to learn the gmm on", default=2, type=int)
    parser.add_argument('-n_cluster','--N_cluster',help="If train, set the number of clusters", default=7, type=int)
    parser.add_argument('-condition','--Condition',help= "type of experiment to run/analyze", default=0, type=int)
    parser.add_argument('-type','--Type',help="whether to train or val", default='train', type=str)
    parser.add_argument('-mode','--Mode',help="if train is true, then whether to learn the gmm or load it", default='load',type=str)
    parser.add_argument('-dataout','--Dataout',help="path to data",default='/Users/gautam.sridhar/Documents/Repos/BASS/Data/',type=str)
    parser.add_argument('-savename','--Savename',help="name of gmm to save/load", default="acid",type=str)
    parser.add_argument('-out','--Out',help="path to save",default='/Users/gautam.sridhar/Documents/Repos/BASS/GMM/',type=str)
    args = parser.parse_args()
    main(args)


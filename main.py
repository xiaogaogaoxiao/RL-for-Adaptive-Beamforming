# -*- coding: utf-8 -*-
"""
@author: Dennis Sand, Nicolai Almskou,
         Peter Fisker & Victor Nissen
"""

# %% Imports
import os

import numpy as np
import matplotlib.pyplot as plt

import classes
import helpers

# %% Global Parameters
RUN = True


# %% main
if __name__ == "__main__":

    # Number of steps in a episode
    N = 20000

    # Radius for commuication range [m]
    r_lim = 200

    # Stepsize limits [min, max]
    stepsize = [0.5, 1]

    # Number of episodes
    M = 5

    # Number of antennae
    Nt = 10  # Transmitter
    Nr = 10  # Receiver

    fc = 28e9  # Center frequncy
    lambda_ = 3e8 / fc

    # Load the data
    if not RUN:
        try:
            print("Loading data")
            data = np.load("data.npy", allow_pickle=True)
            tmp = data[0]
            pos_log = data[1]
            M = len(pos_log)

        except IOError:
            RUN = True
            print("Datafile not found")

    if RUN:
        # Run the scenario to get the simulated channel parameters
        from oct2py import octave

        print("Creating track")
        # Create the class
        track = classes.Track(r_lim, stepsize)

        # Create the tracks
        pos_log = []
        for m in range(M):
            pos_log.append(track.run(N))

        print("Creating new data")
        # Add Quadriga folder to octave path
        octave.addpath(octave.genpath(f"{os.getcwd()}/Quadriga"))
        tmp = octave.get_data(fc, pos_log)

        # Save the data
        data_tmp = []
        data_tmp.append(tmp)
        data_tmp.append(pos_log)
        data = np.empty(len(data_tmp), dtype=object)
        data[:] = data_tmp

        np.save("data.npy", data)

    # Extract data
    print("Extracting data")
    AoA = tmp[0]  # Angle of Arrival
    AoD = tmp[1]  # Angle of Depature
    coeff = tmp[2]  # Channel Coeffiecents

    print("Starts calculating")
    # Make ULA - Transmitter
    r_r = np.zeros((2, Nr))
    r_r[0, :] = np.linspace(0, (Nr - 1) * lambda_ / 2, Nr)

    # Make ULA - Receiver
    r_t = np.zeros((2, Nt))
    r_t[0, :] = np.linspace(0, (Nt - 1) * lambda_ / 2, Nt)

    # Empty arrays
    beam_t = np.zeros(np.shape(AoA)[0])
    beam_r = np.zeros(np.shape(AoA)[0])
    R = np.zeros((Nt, Nr, np.shape(AoA)[0]))

    # print("Calculating R")
    F = np.zeros((Nt, Nt), dtype=np.complex128)
    W = np.zeros((Nr, Nr), dtype=np.complex128)

    for p in range(Nt):
        F[p, :] = (1 / np.sqrt(Nt)) * np.exp(-1j * np.pi * np.arange(Nt) * ((2 * p - Nt) / Nt))

    for q in range(Nr):
        W[q, :] = (1 / np.sqrt(Nr)) * np.exp(-1j * np.pi * np.arange(Nr) * ((2 * q - Nr) / Nr))

    for j in range(np.shape(AoA)[0]):
        # print("Calculating H")
        alpha_rx = helpers.steering_vectors2d(dir=-1, theta=AoA[j, :], r=r_r, lambda_=lambda_)
        alpha_tx = helpers.steering_vectors2d(dir=1, theta=AoD[j, :], r=r_t, lambda_=lambda_)
        beta = coeff[j, :]

        H = np.zeros((Nr, Nt), dtype=np.complex128)
        for i in range(len(beta)):
            H += beta[i] * (alpha_rx[i].T @ np.conjugate(alpha_tx[i]))
        H = H*np.sqrt(Nr * Nt)

        for p in range(Nt):
            for q in range(Nr):
                R[p, q, j] = np.linalg.norm(np.sqrt(100000)*np.conjugate(W[q, :]).T @ H @ F[p, :])**2

        # print("Calculating Angles")
        index = np.unravel_index(np.argmax(R[:, :, j], axis=None), (Nt, Nr))

        # Equation 9 & 10 in "A Deep Learning Approach to Locatio"
        # Page 8
        beam_t[j] = np.arccos((2*index[0]-Nt)/Nt)*180/np.pi
        beam_r[j] = 180 - np.arccos((2*index[1]-Nr)/Nr)*180/np.pi
        # OLD: np.arccos(1-(2*index[1]/(Nr-1)))*180/np.pi

        # print(f"Reiver beam dir: {beam_r}\nTransmitter beam dir: {beam_t}")

    print("Done")

    # %% PLOT

    # Plot the directivity
    helpers.plot_directivity(W, 1000, "Receiver")
    helpers.plot_directivity(F, 1000, "Transmitter")

    # Plot the beam direction for the receiver and transmitter
    plt.figure()
    plt.title("Receiver")
    plt.plot(beam_r)

    plt.figure()
    plt.title("Transmitter")
    plt.plot(beam_t)

    fig, ax = plt.subplots()
    ax.set_title("Kunst")
    ax.add_patch(plt.Circle((0, 0), r_lim, color='r', alpha=0.1))
    for m in range(M):
        ax.plot(pos_log[m][0, :], pos_log[m][1, :])

    ax.set_xlim([-r_lim, r_lim])
    ax.set_ylim([-r_lim, r_lim])

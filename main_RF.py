# -*- coding: utf-8 -*-
"""
@author: Dennis Sand, Nicolai Almskou,
         Peter Fisker & Victor Nissen
"""

# %% Imports
from time import time

import matplotlib.pyplot as plt

import numpy as np

import helpers
import classes

# %% Global Parameters
RUN = False
ENGINE = "MATLAB"  # "octave" OR "MATLAB"
METHOD = "Q-LEARNING"  # "simple", "SARSA" OR "Q-LEARNING
ADJ = False
ORI = True  # Include the orientiation in the state

# %% main
if __name__ == "__main__":

    # Number of steps in a episode
    N = 20000

    # Radius for communication range [m]
    r_lim = 200

    # Stepsize limits [m] [min, max]
    stepsize = [0.5, 1]

    # Number of episodes
    M = 5

    # Number of antennae
    Nt = 4  # Transmitter
    Nr = 4  # Receiver

    # Number of beams
    Nbt = 8  # Transmitter
    Nbr = 8  # Receiver

    fc = 28e9  # Center frequency
    lambda_ = 3e8 / fc  # Wave length
    P_t = 10000  # Transmission power

    # Possible scenarios for Quadriga simulations
    scenarios = ['3GPP_38.901_UMi_LOS']  # '3GPP_38.901_UMi_NLOS'

    t_start = time()
    # Load or create the data
    tmp, pos_log = helpers.get_data(RUN, ENGINE,
                                    "data_pos.mat", "data.mat",
                                    [fc, N, M, r_lim, stepsize, scenarios])
    print(f"Took: {time() - t_start}")

    # Re-affirm that "M" matches data
    M = len(pos_log)

    # Extract data from Quadriga simulation
    print("Extracting data")
    AoA_Global = tmp[0][0]  # Angle of Arrival in Global coord. system
    AoD_Global = tmp[1][0]  # Angle of Departure in Global coord. system
    coeff = tmp[2][0]  # Channel Coefficients
    Orientation = tmp[3][0]  # Orientation in Global coord. system

    print("Starts calculating")
    # Make ULA antenna positions - Transmitter
    r_r = np.zeros((2, Nr))
    r_r[0, :] = np.linspace(0, (Nr - 1) * lambda_ / 2, Nr)

    # Make ULA antenna positions - Receiver
    r_t = np.zeros((2, Nt))
    r_t[0, :] = np.linspace(0, (Nt - 1) * lambda_ / 2, Nt)

    # Preallocate empty arrays
    beam_t = np.zeros((M, N))
    beam_r = np.zeros((M, N))
    AoA_Local = []
    F = np.zeros((Nbt, Nt), dtype=np.complex128)
    W = np.zeros((Nbr, Nr), dtype=np.complex128)

    # Calculate DFT-codebook - Transmitter
    for p in range(Nbt):
        F[p, :] = ((1 / np.sqrt(Nt)) * np.exp(-1j * np.pi * np.arange(Nt) * ((2 * p - Nbt) / (Nbt))))

    # Calculate DFT-codebook - Receiver
    for q in range(Nbr):
        W[q, :] = (1 / np.sqrt(Nr)) * np.exp(-1j * np.pi * np.arange(Nr) * ((2 * q - Nbr) / (Nbr)))

    for episode in range(M):
        AoA_Local.append(helpers.get_local_angle(AoA_Global[episode][0], Orientation[episode][0][2, :]))

    Env = classes.Environment(AoA_Local[0], AoD_Global[0][0], coeff[0][0],
                              W, F, Nt, Nr,
                              r_r, r_t, fc, P_t)

    action_space = np.arange(Nbr)
    Agent = classes.Agent(action_space, eps=0.1)

    if ORI:
        State = classes.State([[0, 1, 0], 0])
        ori_discrete = helpers.disrete_ori(Orientation[0][0][2, :], Nbr)
    else:
        State = classes.State([0, 1, 0])
        ori_discrete = None

    # RUN
    action_log = np.zeros([N, 1])
    action = 0
    for n in range(N):
        if ORI:
            ori = int(ori_discrete[n])
        else:
            ori = None

        if ADJ:
            action = Agent.e_greedy_adj(State.get_state(), action)
        else:
            action = Agent.e_greedy(State.get_state())

        R = Env.take_action(n, action)

        if METHOD == "simple":
            Agent.update(State, action, R)
        elif METHOD == "SARSA":
            if ADJ:
                next_action = Agent.e_greedy_adj(State.get_nextstate(action, ori), action)
            else:
                next_action = Agent.e_greedy(State.get_nextstate(action, ori))
            Agent.update_sarsa(R, State, action,
                               next_action, ori)
        else:
            Agent.update_Q_learning(R, State, action, ori, adj=ADJ)

        State.update_state(action, ori)
        action_log[n] = action

    print("Done")
    # beam_r = 180 - np.arccos((2 * action_log - Nr) / Nr) * 180 / np.pi

    # %% PLOT

    # Plot the beam direction for the receiver and transmitter
    # Caculate the Line Of Sight angle for transmitter in GLOBAL coordinate system
    AoA_LOS_t = np.abs(np.arctan2(pos_log[0][1], pos_log[0][0]) * 180 / np.pi)

    # Caculate the Line Of Sight angle for receiver in GLOBAL coordinate system
    AoA_LOS_r_GLOBAL = np.arctan2(-pos_log[0][1], -pos_log[0][0])
    AoA_LOS_r_GLOBAL.shape = (N, 1)

    # Caculate the Line Of Sight angle for receiver in LOCAL coordinate system
    AoA_LOS_r_LOCAL = np.abs(helpers.get_local_angle(AoA_LOS_r_GLOBAL[0][0], Orientation[0][0][2, :]) * 180 / np.pi)

    beam_LOS = helpers.angle_to_beam(AoA_LOS_r_LOCAL, W)

    NN = 1000

    if NN > 50:
        MM = 50
    else:
        MM = NN
    plt.figure()
    plt.title("Receiver - beam")

    plt.scatter(np.arange(MM), action_log[-MM:], label="Beam")
    plt.scatter(np.arange(MM), beam_LOS[-MM:], label="LOS")
    plt.legend()
    plt.show()

    ACC = np.sum(beam_LOS[-NN:] == action_log[-NN:])/NN
    print(f"METHOD: {METHOD}, ACC: {ACC}, AJD: {ADJ}, ORI: {ORI}")

    """
    plt.figure()
    plt.title("Receiver - angle")
    plt.plot(beam_r[-100:], label="Beam")
    plt.plot(AoA_LOS_r_LOCAL[-100:], label="LOS")
    plt.legend()
    plt.show()
    """

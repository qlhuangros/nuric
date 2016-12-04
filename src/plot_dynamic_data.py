#!/usr/bin/env python

import rospy
import sys
import numpy as np 
import matplotlib.pyplot as plt 

def plot_data():
    
    data = np.genfromtxt('/home/abhi/nuric_ws/src/nuric_wheelchair_model_02/src/data.csv', names=['x', 'y', 'th', 'l_caster', 'r_caster'])
    dataEst = np.genfromtxt('/home/abhi/nuric_ws/src/nuric_wheelchair_model_02/src/data_est.csv', names=['x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6'])
    dataUkf = np.genfromtxt('/home/abhi/nuric_ws/src/nuric_wheelchair_model_02/src/data_ukf.csv', names=['x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6'])


    line_width = 3.0
    alpha_value = 0.6

    plt.figure(1)
    plt.subplot(221)
    plt.plot(data['l_caster'], linewidth=line_width, alpha=alpha_value, label='Actual')
    plt.plot(dataEst['x5'], linewidth=line_width, alpha=alpha_value, label='Estimated')
    plt.plot(dataUkf['x5'], linewidth=line_width, alpha=alpha_value, label='UKF')
    plt.legend()

    plt.subplot(222)
    plt.plot(data['r_caster'], linewidth=line_width, alpha=alpha_value, label='Actual')
    plt.plot(dataEst['x6'], linewidth=line_width, alpha=alpha_value, label='Estimated')
    plt.plot(dataUkf['x6'], linewidth=line_width, alpha=alpha_value, label='UKF')
    plt.legend()

    plt.subplot(223)
    plt.plot(data['l_caster']-dataUkf['x5'], linewidth=line_width, alpha=alpha_value)

    plt.subplot(224)
    plt.plot(data['r_caster']-dataUkf['x6'],  linewidth=line_width, alpha=alpha_value)

    plt.figure(2)
    plt.subplot(231)
    plt.plot(data['x'], linewidth=line_width, alpha=alpha_value, label='Actual')
    plt.plot(dataEst['x3'], linewidth=line_width, alpha=alpha_value, label='Estimated')
    plt.plot(dataUkf['x3'], linewidth=line_width, alpha=alpha_value, label='UKF')
    plt.legend()

    plt.subplot(232)
    plt.plot(data['y'], linewidth=line_width, alpha=alpha_value, label='Actual')
    plt.plot(dataEst['x2'], linewidth=line_width, alpha=alpha_value, label='Estimated')
    plt.plot(dataUkf['x2'], linewidth=line_width, alpha=alpha_value, label='UKF')
    plt.legend()

    plt.subplot(233)
    plt.plot(data['th'], linewidth=line_width, alpha=alpha_value, label='Actual')
    plt.plot(dataEst['x4'], linewidth=line_width, alpha=alpha_value, label='Estimated')
    plt.plot(dataUkf['x4'], linewidth=line_width, alpha=alpha_value, label='UKF')
    plt.legend()

    plt.subplot(234)
    plt.plot(data['x']-dataUkf['x3'], linewidth=line_width, alpha=alpha_value)

    plt.subplot(235)
    plt.plot(data['y']-dataUkf['x2'], linewidth=line_width, alpha=alpha_value)

    plt.subplot(236)
    plt.plot(data['th']-dataUkf['x4'], linewidth=line_width, alpha=alpha_value)



    plt.show()


if __name__ == '__main__':

    try:
        plot_data()
    except rospy.ROSInterruptException:
        pass
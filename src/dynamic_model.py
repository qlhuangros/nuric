#!/usr/bin/env python
import rospy
import sys
from nuric_wheelchair_model_02.msg import FloatArray
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import random
import matplotlib.pyplot as plt
from math import sin, cos, atan2
import numpy as np
from scipy.integrate import odeint
from tf.transformations import euler_from_quaternion

class SolveDynamicModel:
    def __init__(self):
        rospy.init_node('solve_dynamic_model')

        rospy.on_shutdown(self.shutdown)
        self.wheel_cmd = Twist()

        self.wheel_cmd.linear.x = -0.3
        self.wheel_cmd.angular.z = -0.3

        self.move_time = 4.0
        self.rate = 100

        self.pose_x_data = []
        self.pose_y_data = []
        self.pose_th_data = []

        self.solx = []
        self.soly = []
        self.solth = []

        # constants for ode equations
        # (approximations)
        self.Iz = 5.0
        self.mu = .01
        self.ep = 0.5
        self.m = 5.0
        self.g = 9.81
        self.pi = 3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348


        self.save = 0
        self.get_caster_data = 0
        self.get_pose = 0

        self.actual_pose = rospy.Subscriber('/odom', Odometry, self.actual_pose_callback)

        self.caster_joints = rospy.Subscriber('/caster_joints', FloatArray, self.caster_joints_callback)

        self.pub_twist = rospy.Publisher('/cmd_vel', Twist, queue_size=20)

        self.r = rospy.Rate(self.rate)

        self.move_wheelchair()

        self.plot_data()


    def actual_pose_callback(self, actual_pose):
        # (roll,pitch,yaw) = euler_from_quaternion([actual_pose.pose.pose.orientation.x, actual_pose.pose.pose.orientation.y, actual_pose.pose.pose.orientation.z, actual_pose.pose.pose.orientation.w])

        # self.pose_x = actual_pose.pose.pose.position.x
        # self.pose_y = actual_pose.pose.pose.position.y
        # self.pose_th = yaw

        if self.save:
            (_,_,yaw) = euler_from_quaternion([actual_pose.pose.pose.orientation.x, actual_pose.pose.pose.orientation.y, actual_pose.pose.pose.orientation.z, actual_pose.pose.pose.orientation.w])

            self.pose_x_data.append(actual_pose.pose.pose.position.x)
            self.pose_y_data.append(actual_pose.pose.pose.position.y)
            self.pose_th_data.append(yaw)

        if self.get_pose:
            (_,_,yaw) = euler_from_quaternion([actual_pose.pose.pose.orientation.x, actual_pose.pose.pose.orientation.y, actual_pose.pose.pose.orientation.z, actual_pose.pose.pose.orientation.w])

            self.pose_x = actual_pose.pose.pose.position.x
            self.pose_y = actual_pose.pose.pose.position.y
            self.pose_th = yaw
        # print self.pose_x, self.pose_y

    def caster_joints_callback(self, caster_joints):       
        if self.get_caster_data:            
            self.l_caster_angle, self.r_caster_angle = caster_joints.data[0], caster_joints.data[1]


    def move_wheelchair(self):

        self.get_caster_data = 1
        self.get_pose = 1
        self.r.sleep()
        while rospy.get_time() == 0.0:
            continue
        start = rospy.get_time()
        self.get_caster_data = 0
        self.get_pose = 0

        rospy.loginfo("Moving robot...")
        while (rospy.get_time() - start < self.move_time) and not rospy.is_shutdown():
            self.save = 1
            self.pub_twist.publish(self.wheel_cmd)        
            # self.r.sleep()

        # Stop the robot
        self.pub_twist.publish(Twist())
        self.save = 0
        
        

        rospy.sleep(1)

    # def save_data(self):
    #     self.pose_x_data.append(self.pose_x)
    #     self.pose_y_data.append(self.pose_y)
    #     self.pose_th_data.append(self.pose_th)

    def solvr(self, q, t):

        N = self.m*self.g

        F1u = self.mu*self.ep*N/2.
        F1w = 0.0      
        F2u = self.mu*self.ep*N/2.
        F2w = 0.0
        F3u = self.mu*(1-self.ep)*N/2.
        F3w = 0.0
        F4u = self.mu*(1-self.ep)*N/2.
        F4w = 0.0

        d = 0.0
        L = 0.58
        Rr = 0.27*2
        s = 0.0

        delta2 = self.pi - self.l_caster_angle
        delta1 = self.pi - self.r_caster_angle


        omega1 = (F3u*cos(delta1)) + (F3w*sin(delta1)) + F1u + F2u + (F4u*cos(delta2)) + (F4w*sin(delta2))
        omega2 = F1w - (F3u*sin(delta1)) + (F3w*cos(delta1)) - (F4u*sin(delta2)) + (F4w*cos(delta2)) + F2w
        omega3 = (F2u*(Rr/2.-s))-(F1u*(Rr/2.-s))-((F2w+F1w)*d)+((F4u*cos(delta2)+F4w*sin(delta2))*(Rr/2.-s))-((F3u*cos(delta1)-F3w*sin(delta1))*(Rr/2.+s))+((F4w*cos(delta2)-F4u*sin(delta2)+F3w*cos(delta1)-F3u*sin(delta1))*(L-d))


        eq1 = omega3/self.Iz
        eq2 = ((-omega1*sin(q[4]) + omega2*cos(q[4]))/self.m) - 0.*q[0]*q[2]
        eq3 = ((-omega1*cos(q[4]) - omega2*sin(q[4]))/self.m) + q[0]*q[1]
        eq4 = q[1]*sin(q[4]) - 0.*q[2]*cos(q[4])
        eq5 = -q[1]*cos(q[4]) - 0.*q[2]*sin(q[4])
        eq6 = q[0]

        return [eq1, eq2, eq4, eq5, eq6]


    def ode_int(self):

        a_t = np.arange(0.0, self.move_time, 1./self.rate)
        # ini_val = [self.wheel_cmd.angular.z, self.wheel_cmd.linear.x, 0.0, self.pose_x, self.pose_y, self.pose_z]
        ini_val = [self.wheel_cmd.angular.z, -self.wheel_cmd.linear.x, -self.pose_y, self.pose_x, self.pose_th]

        asol = odeint(self.solvr, ini_val, a_t)
        # self.sol = [item for sublist in asol.tolist() for item in sublist]  
        print len(asol)
        for i in xrange(int(self.move_time*self.rate)):
            self.solx.append(asol[i][3])
            self.soly.append(-asol[i][2])
            self.solth.append(asol[i][4])
        
        # print self.solx      


    def plot_data(self):
        self.ode_int()
        plt.figure(1)
        plt.title("Estimated pose of robot")
        plt.plot(self.solx, label="x")
        plt.plot(self.soly, label="y")
        plt.plot(self.solth, label="th")
        plt.legend()

        plt.figure(2)
        plt.title("Actual pose of robot")
        plt.plot(self.pose_x_data, label="x")
        plt.plot(self.pose_y_data, label="y")
        plt.plot(self.pose_th_data, label="th")
        plt.legend()

        plt.show()


    def shutdown(self):
        # Stop the robot when shutting down the node.
        rospy.loginfo("Stopping the robot...")
        self.pub_twist.publish(Twist())
        rospy.sleep(1)

if __name__ == '__main__':

    try:
        SolveDynamicModel()
    except rospy.ROSInterruptException:
        pass
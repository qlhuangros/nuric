#!/usr/bin/env python
import rospy
from nuric_wheelchair_model_02.msg import FloatArray
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import numpy as np
from tf.transformations import euler_from_quaternion
from ukf_helper import normalize_angle, al_to_th, th_to_al, rK7

class ModelWheelchair:

    def __init__(self):
        rospy.init_node('model_wheelchair')

        rospy.on_shutdown(self.shutdown)
        self.wheel_cmd = Twist()

        self.wheel_cmd.linear.x = -0.3 # Driving back w/o turn and a non-zero caster orientation
        self.wheel_cmd.angular.z = 0.2

        self.move_time = 6.0
        self.rate = 50
        self.dt = 1./self.rate        

        self.pose_x_data = []
        self.pose_y_data = []
        self.pose_th_data = []
        self.l_caster_data = []
        self.r_caster_data = []

        self.normalize_angle = normalize_angle
        self.al_to_th = al_to_th
        self.th_to_al = th_to_al
        self.rK7 = rK7

        # constants for ode equations
        # (approximations)
        self.Iz = 15.0
        self.mu = .01
        self.ep = 0.2
        self.m = 5.0
        self.g = 9.81/50.

        # wheelchair constants
        self.wh_consts = [0.58, 0.19, 0.06]

        self.count = 0

        self.actual_pose = rospy.Subscriber('/odom', Odometry, self.actual_pose_callback)
        self.caster_joints = rospy.Subscriber('/caster_joints', FloatArray, self.caster_joints_callback)
        self.pub_twist = rospy.Publisher('/cmd_vel', Twist, queue_size=20)

        self.r = rospy.Rate(self.rate)

        self.move_wheelchair()
        self.save_data()

       
    def actual_pose_callback(self, actual_pose):
        
        (_,_,yaw) = euler_from_quaternion([actual_pose.pose.pose.orientation.x, actual_pose.pose.pose.orientation.y, actual_pose.pose.pose.orientation.z, actual_pose.pose.pose.orientation.w])

        self.pose_x = actual_pose.pose.pose.position.x
        self.pose_y = actual_pose.pose.pose.position.y
        self.pose_th = yaw

    def caster_joints_callback(self, caster_joints):       
 
        self.l_caster_angle, self.r_caster_angle = caster_joints.data[0], caster_joints.data[1]

    def move_wheelchair(self):
                
        while rospy.get_time() == 0.0:
            continue
        start = rospy.get_time()

        rospy.sleep(1)
        
        self.ini_val = [self.wheel_cmd.angular.z, -self.wheel_cmd.linear.x, -self.pose_y, self.pose_x, self.pose_th, self.th_to_al(self.l_caster_angle), self.th_to_al(self.r_caster_angle)]

        count = 0
        rospy.loginfo("Moving robot...")
        while (rospy.get_time() - start < self.move_time) and not rospy.is_shutdown():
            
            self.pub_twist.publish(self.wheel_cmd)                

            self.pose_x_data.append(self.pose_x)
            self.pose_y_data.append(self.pose_y)
            self.pose_th_data.append(self.pose_th)
            self.l_caster_data.append(self.l_caster_angle)
            self.r_caster_data.append(self.r_caster_angle)

            count += 1

            self.r.sleep()


        # Stop the robot
        self.pub_twist.publish(Twist())
        self.count = count
        rospy.sleep(1)


    def solve_est(self):
        count=0

        x0=np.array(self.ini_val)
        sol = np.reshape(x0, (1,7))

        while count < self.count-1:

            sol1 = self.ode2(x0, self.dt)
            x0 = sol1
            sol1 = np.reshape(sol1, (1,7))
            sol = np.append(sol, sol1, axis=0)
             
            count += 1

        return sol

    def save_data(self):
        np.savetxt('data_model.csv', np.c_[self.pose_x_data, self.pose_y_data, self.pose_th_data, self.l_caster_data, self.r_caster_data])

        sol = self.solve_est()
        sol[:,2] = -sol[:,2]
        sol[:,5] = self.al_to_th(sol[:,5])
        sol[:,6] = self.al_to_th(sol[:,6])
        np.savetxt('data_est_model.csv', sol)


    def ode2(self, x0, dt):

        self.dl = self.wh_consts[0]
        self.df = self.wh_consts[1]
        self.dc = self.wh_consts[2]

        x0 = np.array(x0)

        a, b, c, d, e, f, g = x0.tolist()

        def fa(a, b, c, d, e, f, g):
            omega3 = self.omegas(self.delta(f),self.delta(g))[2]
            return omega3/self.Iz

        def fb(a, b, c, d, e, f, g):
            omega1 = self.omegas(self.delta(f),self.delta(g))[0]
            omega2 = self.omegas(self.delta(f),self.delta(g))[1]
            return ((-omega1*np.sin(e) + omega2*np.cos(e))/self.m)

        def fc(a, b, c, d, e, f, g):
            return b*np.sin(e)

        def fd(a, b, c, d, e, f, g):
            return -b*np.cos(e)

        def fe(a, b, c, d, e, f, g):
            return a

        def ff(a, b, c, d, e, f, g):
            return (a*(self.dl*np.cos(f) - (self.df*np.sin(f)/2) - self.dc)/self.dc) - (b*np.sin(f)/self.dc)

        def fg(a, b, c, d, e, f, g):
            return (a*(self.dl*np.cos(g) + (self.df*np.sin(g)/2) - self.dc)/self.dc) - (b*np.sin(g)/self.dc)

        return np.array(self.rK7(a, b, c, d, e, f, g, fa, fb, fc, fd, fe, ff, fg, dt))


    def rK7(self, a, b, c, d, e, f, g, fa, fb, fc, fd, fe, ff, fg, hs):

        a1 = fa(a, b, c, d, e, f, g)*hs
        b1 = fb(a, b, c, d, e, f, g)*hs
        c1 = fc(a, b, c, d, e, f, g)*hs
        d1 = fd(a, b, c, d, e, f, g)*hs
        e1 = fe(a, b, c, d, e, f, g)*hs
        f1 = ff(a, b, c, d, e, f, g)*hs
        g1 = fg(a, b, c, d, e, f, g)*hs

        ak = a + a1*0.5
        bk = b + b1*0.5
        ck = c + c1*0.5
        dk = d + d1*0.5
        ek = e + e1*0.5
        fk = f + f1*0.5
        gk = g + g1*0.5

        a2 = fa(ak, bk, ck, dk, ek, fk, gk)*hs
        b2 = fb(ak, bk, ck, dk, ek, fk, gk)*hs
        c2 = fc(ak, bk, ck, dk, ek, fk, gk)*hs
        d2 = fd(ak, bk, ck, dk, ek, fk, gk)*hs
        e2 = fe(ak, bk, ck, dk, ek, fk, gk)*hs
        f2 = ff(ak, bk, ck, dk, ek, fk, gk)*hs
        g2 = fg(ak, bk, ck, dk, ek, fk, gk)*hs

        ak = a + a2*0.5
        bk = b + b2*0.5
        ck = c + c2*0.5
        dk = d + d2*0.5
        ek = e + e2*0.5
        fk = f + f2*0.5
        gk = g + g2*0.5

        a3 = fa(ak, bk, ck, dk, ek, fk, gk)*hs
        b3 = fb(ak, bk, ck, dk, ek, fk, gk)*hs
        c3 = fc(ak, bk, ck, dk, ek, fk, gk)*hs
        d3 = fd(ak, bk, ck, dk, ek, fk, gk)*hs
        e3 = fe(ak, bk, ck, dk, ek, fk, gk)*hs
        f3 = ff(ak, bk, ck, dk, ek, fk, gk)*hs
        g3 = fg(ak, bk, ck, dk, ek, fk, gk)*hs

        ak = a + a3
        bk = b + b3
        ck = c + c3
        dk = d + d3
        ek = e + e3
        fk = f + f3
        gk = g + g3

        a4 = fa(ak, bk, ck, dk, ek, fk, gk)*hs
        b4 = fb(ak, bk, ck, dk, ek, fk, gk)*hs
        c4 = fc(ak, bk, ck, dk, ek, fk, gk)*hs
        d4 = fd(ak, bk, ck, dk, ek, fk, gk)*hs
        e4 = fe(ak, bk, ck, dk, ek, fk, gk)*hs
        f4 = ff(ak, bk, ck, dk, ek, fk, gk)*hs
        g4 = fg(ak, bk, ck, dk, ek, fk, gk)*hs

        a = a + (a1 + 2*(a2 + a3) + a4)/6
        b = b + (b1 + 2*(b2 + b3) + b4)/6
        c = c + (c1 + 2*(c2 + c3) + c4)/6
        d = d + (d1 + 2*(d2 + d3) + d4)/6
        e = e + (e1 + 2*(e2 + e3) + e4)/6
        f = f + (f1 + 2*(f2 + f3) + f4)/6
        g = g + (g1 + 2*(g2 + g3) + g4)/6

        return [a, b, c, d, e, f, g]


    def omegas(self, delta1, delta2):

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

        omega1 = (F3u*cos(delta1)) + (F3w*sin(delta1)) + F1u + F2u + (F4u*cos(delta2)) + (F4w*sin(delta2))
        omega2 = F1w - (F3u*sin(delta1)) + (F3w*cos(delta1)) - (F4u*sin(delta2)) + (F4w*cos(delta2)) + F2w
        omega3 = (F2u*(Rr/2.-s))-(F1u*(Rr/2.-s))-((F2w+F1w)*d)+((F4u*cos(delta2)+F4w*sin(delta2))*(Rr/2.-s))-((F3u*cos(delta1)-F3w*sin(delta1))*(Rr/2.+s))+((F4w*cos(delta2)-F4u*sin(delta2)+F3w*cos(delta1)-F3u*sin(delta1))*(L-d))

        return [omega1, omega2, omega3]


    def delta(self, alpha):
        return -alpha

    
    def shutdown(self):
        # Stop the robot when shutting down the node.
        rospy.loginfo("Stopping the robot...")
        self.pub_twist.publish(Twist())
        rospy.sleep(1)

if __name__ == '__main__':

    try:
        ModelWheelchair()
    except rospy.ROSInterruptException:
        pass
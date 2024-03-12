# coding: utf-8
""" demo on dynamic eit using JAC method """
# Copyright (c) Benyuan Liu. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
from __future__ import absolute_import, division, print_function

import matplotlib.pyplot as plt
import numpy as np
import pyeit.eit.jac as jac
import pyeit.mesh as mesh
from pyeit.eit.fem import EITForward
from pyeit.eit.interp2d import sim2pts
from pyeit.mesh.shape import thorax, unit_circle
import pyeit.eit.protocol as protocol
from pyeit.mesh.wrapper import PyEITAnomaly_Circle

import serial
from datetime import datetime
import time
from matplotlib.animation import FuncAnimation
from matplotlib.colors import TwoSlopeNorm

import argparse
import os
""" -3. CLI """
def parse_args():
    parser = argparse.ArgumentParser(description="University of Engineering and Technology VNU - Electronic Impedance Tomography")
    parser.add_argument("--port", type=str, required=True, help="Serial port for Arduino.")
    parser.add_argument("--ref", help="Measure ref_data.", default = False, action="store_true")
    parser.add_argument("--h0", type = float, help="Mesh size.", default = 0.065)
    parser.add_argument("--p", type = float, help="Value p in Jacobian.", default = 0.8)
    parser.add_argument("--lamb", type = float, help="Value lambda in Jacobian.", default = 0.5)
    parser.add_argument("--perm", type = float, help="Value permittivity.", default = 10)
    parser.add_argument("--norm", type = str, help="Normalized center value for 0 in colorbar.", default = None)
    parser.add_argument("--truth", help="Plot the truth image.", default = False, action = 'store_true')

    parser.add_argument("--static", help="Reconstructed 1 frame.", default = False, action="store_true")
    parser.add_argument("--name", type = str, help="Specific a name for figure. Format h0_p_lambda__\{name\} (for static and ref mode).")
    parser.add_argument("--realtime", help="Run realtime.", default = False, action="store_true")
    parser.add_argument("--interval", type=int, default=50, help="Animation interval in milliseconds (for realtime mode).")
    return parser.parse_args()

def main():

    arg = parse_args()
    check = 0
    if arg.ref == True:
        check +=1
    if arg.static == True:
        check +=1
    if arg.realtime == True:
        check +=1
    if check > 1:
        print("Chỉ có thể chạy một trong các chức năng cùng lúc: ref, realtime, static. Hãy thử lại.")
        return
    if (check == 0):
        print("Hãy chọn một trong các chức năng: ref, static, realtime.")
        return
    
    if not os.path.exists("images"):
        os.makedirs("images")
        print("Đã tạo fodler images")
    if not os.path.exists("data"):
        os.makedirs("data")
        print("Đã tạo folder data")

    
    """-2. Initial vars """
    arduino = serial.Serial(arg.port, 115200 ,timeout=4)
    fig, ax = plt.subplots(constrained_layout=True)
    n_el = 16

    if(arg.ref == False):
        try:
            v0 = np.loadtxt('data/ref_data.txt')
            average_ref = np.average(v0) * arg.perm / 10

        except Exception as e:
            print("Không tìm thấy dữ liệu tham chiếu ref.txt. Hãy sử dụng --ref để thu thập giá trị tham chiếu hoặc kiểm tra lại đường dẫn")
            return
    # Filter positive values using boolean indexing

    """-1. Functions """

    '''To read data from Arduino via COM port

    Each frame is 16 lines, each line has 13 value, 
    in total there are 208 values representing the voltage measured from electrodes. 
    '''

    def readfromArduino():
        while(True):
            try:
                data = arduino.readline().decode('ascii')
                print("data: ", data)
                break
            except UnicodeDecodeError:
                print("UnicodeDecodeError found! Retrying...")
                continue
        return data

    def get_difference_img_array(n_el = n_el, NewFrameSearchFlag = 1, idx = 0):
        difference_image_array = ''
        # Read the voltage data:
        while idx < n_el:
            data = readfromArduino()
            #Skip until the header (which is a single charactẻ 's') is found
            while(NewFrameSearchFlag == 1):
                if len(data) > 4:
                    print("Searching for new frame.")
                    data = readfromArduino()
                    continue
                else:
                    print("New frame found.")
                    data = readfromArduino()
                    NewFrameSearchFlag = 0
                    break
            #Start to take the data right after the header, by doing so, no loss of frame should occcured
            data=data.strip('\r\n')
            difference_image_array += data
            difference_image_array += ' '
            idx = idx + 1
            
        return difference_image_array

    #Convert data to np type
    def convert_data_in(s):
        data=s
        items=[]
        for item in data.split(' '):
            item = item.strip()
            if not item:
                continue
            try:
                items.append(float(item))
            #Handle any unexpected error regarding value so the program won't quit
            except ValueError:
                print("Value Error found! Handling...")
                items.append(float(0))
        return np.array(items)


 
    n_el = 16  # nb of electrodes
    mesh_obj = mesh.create(n_el, h0=arg.h0)

    # extract node, element, alpha
    pts = mesh_obj.node
    tri = mesh_obj.element
    x, y = pts[:, 0], pts[:, 1]

    protocol_obj = protocol.create(n_el, dist_exc=1, step_meas=1, parser_meas="fmmu")


    eit = jac.JAC(mesh_obj, protocol_obj)
    if arg.truth == True:
        arg.perm = 10
    eit.setup(p=arg.p, lamb=arg.lamb, method="kotre", perm = arg.perm, jac_normalized=True)


    def animating(i, flag):  
        s_time = time.time()
        while arduino.inWaiting()==0:
            print("waiting")
            pass

        s1 = get_difference_img_array()

        v1 = convert_data_in(s1)

        try:
            ds = eit.solve(v1, v0, normalize=True)
            ds_n = sim2pts(pts, tri, np.real(ds))
        except Exception as e:
            if flag == 1:
                ani.event_source.stop()   # Stop the current animation
                ani.event_source.start()  # Start a new animation
            else:
                print("Data error, try again!")
                return
        if arg.truth == True:
            print(arg.perm)
            average = np.average(ds_n) 
            print(ds_n)
            max_dsn = max(ds_n)
            min_dsn = min(ds_n)

            average_positive =   1 * average + (abs(max_dsn) - average)/ 2
            average_negative = - 1 * average - (abs(min_dsn) - average)/ 2
            if average_positive < 0.4:
                average_positive +=0.4
            if average_negative > -0.4:
                average_negative -=0.4
            print('avg: ',average)
            print('avg+: ',average_positive)
            print('avg-: ',average_negative)

            for i in range(len(ds_n)):
                if ds_n[i] > average_positive:
                    ds_n[i] = 10 
                elif ds_n[i] < average_negative:
                    ds_n[i] = -10 
                else:
                    ds_n[i] = 0
        # Clear the graph after each animating frame
        ax.clear()

        # Plot EIT reconstruction
        if arg.norm != None:
            if arg.norm == 'auto':
                norm = TwoSlopeNorm(vcenter=average_ref)
            else:
                try:
                    norm = TwoSlopeNorm(vcenter=float(arg.norm))
                except Exception as e:
                    print("Lỗi dữ liệu norm, hãy chắc chắn bạn nhập 'auto' hoặc một số.")
                    return
            im = ax.tripcolor(x, y, tri, ds_n, norm = norm, shading="flat", cmap=plt.cm.magma)
        else:
            im = ax.tripcolor(x, y, tri, ds_n, shading="flat", cmap=plt.cm.magma)

        for i, e in enumerate(mesh_obj.el_pos):
            ax.annotate(str(i + 1), xy=(x[e], y[e]), color="r")
        ax.set_aspect("equal")
        plt.title("p = {} | lambda = {}".format(arg.p, arg.lamb))
        if flag == 0:
             plt.colorbar(im, ax=ax)
        print("Run time = {}\n".format(time.time() - s_time))



    
    if arg.ref == True:
        while arduino.inWaiting()==0:
            print("waiting")
            time.sleep(0.5)
            pass
        s1 = get_difference_img_array()
        ref_v = ''
        with open('data/ref_data.txt', 'w') as f:
            for val in s1:
                ref_v +=val
            f.write(ref_v)
        return
    if arg.static == True:
        animating(0, flag = 0)
        print("avg_ref = ", average_ref)
        plt.savefig('./images/{}_{}_{}___{}.png'.format(str(arg.h0), str(arg.p), str(arg.lamb), arg.name), dpi=96)
        plt.show()
    if arg.realtime == True:
        ani = FuncAnimation(fig, animating, fargs=(1,), interval = arg.interval, cache_frame_data= False)
        plt.show()

if __name__ == "__main__":
    main()
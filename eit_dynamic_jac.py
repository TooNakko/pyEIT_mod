# coding: utf-8
""" demo on dynamic eit using JAC method """
# Copyright (c) Benyuan Liu. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
from __future__ import absolute_import, division, print_function

import time 
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

import numpy as np
import pyeit.eit.jac as jac
import pyeit.mesh as mesh
from pyeit.eit.fem import EITForward
from pyeit.eit.interp2d import sim2pts
from pyeit.mesh.shape import thorax, rectangle
import pyeit.eit.protocol as protocol
from pyeit.mesh.wrapper import PyEITAnomaly_Circle

""" 0. build mesh """
n_el = 16  # nb of electrodes

#the higher of p and the lower of lamb -> good shape image. Should be tunning
p = 0.8
lamb = 0.02
use_customize_shape = False

mesh_obj = mesh.create(n_el, h0=0.065)

# extract node, element, alpha
pts = mesh_obj.node
tri = mesh_obj.element
x, y = pts[:, 0], pts[:, 1]

""" 1. problem setup """
# mesh_obj["alpha"] = np.random.rand(tri.shape[0]) * 200 + 100 # NOT USED
#anomaly = PyEITAnomaly_Circle(center=[0.5, 0.5], r=0.05, perm=1000.0)
#mesh_new = mesh.set_perm(mesh_obj, anomaly=anomaly)

""" 2. FEM simulation """
# setup EIT scan conditions
protocol_obj = protocol.create(n_el, dist_exc=1, step_meas=1, parser_meas="fmmu") # use fmmu or rotate_meas

# calculate simulated data
#fwd = EITForward(mesh_obj, protocol_obj)


#v0 = fwd.solve_eit()
#v1 = fwd.solve_eit(perm=mesh_new.perm)

v0 = np.loadtxt('example_data/ref_data.txt')
v1 = np.loadtxt('example_data/diff_middle_data.txt')

""" 3. JAC solver """
# Note: if the jac and the real-problem are generated using the same mesh,
# then, data normalization in solve are not needed.
# However, when you generate jac from a known mesh, but in real-problem
# (mostly) the shape and the electrode positions are not exactly the same
# as in mesh generating the jac, then data must be normalized.
eit = jac.JAC(mesh_obj, protocol_obj)
eit.setup(p=0.75, lamb=0.02, method="kotre", perm=10000, jac_normalized=True)
ds = eit.solve(v1, v0, normalize=True, log_scale=False)
#ds = eit.solve_gs(v1, v0)
#ds = eit.jt_solve(v1, v0, normalize=True)
#ds = eit.gn(v1)
ds_n = sim2pts(pts, tri, np.real(ds))
print('ds=\n', ds_n)
# plot ground truth
fig, ax = plt.subplots(constrained_layout=True)


norm = TwoSlopeNorm(vcenter=0)
# plot EIT reconstruction
im = ax.tripcolor(x, y, tri, ds_n, shading="flat", cmap=plt.cm.magma)
for i, e in enumerate(mesh_obj.el_pos):
    ax.annotate(str(i + 1), xy=(x[e], y[e]), color="r")
ax.set_aspect("equal")

fig.colorbar(im, ax=ax, ticks = [0])

 
plt.savefig('./images/{}_{}.png'.format(str(p)[2:], str(lamb)[2:]), dpi=96)
plt.show()
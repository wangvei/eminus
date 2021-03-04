import numpy as np
from numpy.linalg import eig, det, inv
from numpy.fft import ifftn, fftn
from scipy.linalg import sqrtm
from setup import *

def O(inp):
    return det(R) * inp

def L(inp):
    inp = inp.T
    return (-det(R) * G2 * inp).T

def Linv(inp):
    out = np.zeros(inp.shape, dtype=complex)
    if inp.ndim == 1:
        out[1:] = inp[1:] / G2[1:] / -det(R)
    else:
        for i in range(len(inp)):
            out[i][1:] = inp[i][1:] / G2[1:] / -det(R)
    return out

def cI(inp):
    inp = inp.T
    if inp.ndim == 1:
        tmp = np.reshape(inp, S, order='F')
        out = ifftn(tmp).flatten(order='F')
    else:
        out = np.empty(inp.shape, dtype=complex)
        for i in range(len(inp)):
            tmp = np.reshape(inp[i], S, order='F')
            out[i] = ifftn(tmp).flatten(order='F')
    return (out * np.prod(S)).T

def cJ(inp):
    inp = inp.T
    if inp.ndim == 1:
        tmp = np.reshape(inp, S, order='F')
        out = fftn(tmp).flatten(order='F')
    else:
        out = np.empty(inp.shape, dtype=complex)
        for i in range(len(inp)):
            tmp = np.reshape(inp[i], S, order='F')
            out[i] = fftn(tmp).flatten(order='F')
    return (out / np.prod(S)).T

def cIdag(inp):
    return cJ(inp) * np.prod(S)

def cJdag(inp):
    return cI(inp) / np.prod(S)

def diagouter(A, B):
    return np.sum(A * B.conj(), axis=1)

def getE(W, Vdual):
    U = W.conj().T @ O(W)
    invU = inv(U)
    cIW = cI(W)
    n = f * diagouter(cIW @ invU, cIW)
    phi = -4 * np.pi * Linv(O(cJ(n)))
    exc = excVWN(n)
    return np.real(-f * 0.5 * np.sum(diagouter(W.conj().T, L(W @ invU).conj().T)) + Vdual.conj().T @ n + \
           0.5 * n.conj().T @ cJdag(O(phi)) + n.conj().T @ cJdag(O(cJ(exc))))

def Diagprod(a, B):
    B = B.T
    return (a * B).T

def H(W, Vdual):
    U = W.conj().T @ O(W)
    invU = inv(U)
    cIW = cI(W)
    n = f * diagouter(cIW @ invU, cIW)
    phi = -4 * np.pi * Linv(O(cJ(n)))
    exc = excVWN(n)
    excp = excpVWN(n)
    Veff = Vdual + cJdag(O(phi)) + cJdag(O(cJ(exc))) + excp * cJdag(O(cJ(n)))
    return -0.5 * L(W) + cIdag(Diagprod(Veff, cIW))

def getgrad(W, Vdual):
    U = W.conj().T @ O(W)
    invU = inv(U)
    HW = H(W, Vdual)
    return f * (HW - (O(W) @ invU) @ (W.conj().T @ HW)) @ invU

def sd(W, Vdual, Nit):
    alpha = 3e-5
    for i in range(Nit):
        W = W - alpha * getgrad(W, Vdual)
        print(f'Nit: {i}  \tE(W): {getE(W, Vdual)}')
    return W

def orth(W):
    return W @ inv(sqrtm(W.conj().T @ O(W)))

def getPsi(W, Vdual):
    Y = orth(W)
    mu = Y.conj().T @ H(Y, Vdual)
    epsilon, D = eig(mu)
    return Y @ D, np.real(epsilon)

def excVWN(n):
    X1 = 0.75 * (3 / (2 * np.pi))**(2 / 3)
    A = 0.0310907
    x0 = -0.10498
    b = 3.72744
    c = 12.9352
    Q = np.sqrt(4 * c - b * b)
    X0 = x0 * x0 + b * x0 + c
    rs = (4 * np.pi / 3 * n)**(-1/3)
    x = np.sqrt(rs)
    X = x * x + b * x + c
    out = -X1 / rs + A * (np.log(x * x / X) + 2 * b / Q * np.arctan(Q / (2 * x + b)) \
    - (b * x0) / X0 * (np.log((x - x0) * (x - x0) / X) + 2 * (2 * x0 + b) / Q * np.arctan(Q / (2 * x + b))))
    return out

def excpVWN(n):
    X1 = 0.75 * (3 / (2 * np.pi))**(2 / 3)
    A = 0.0310907
    x0 = -0.10498
    b = 3.72744
    c = 12.9352
    Q = np.sqrt(4 * c - b * b)
    X0 = x0 * x0 + b * x0 + c
    rs = (4 * np.pi / 3 * n)**(-1/3)
    x = np.sqrt(rs)
    X = x * x + b * x + c
    dx = 0.5 / x
    out = dx * (2 * X1 / (rs * x) + A * (2 / x - (2 * x + b) / X - 4 * b / (Q * Q + (2 * x + b) * (2 * x + b)) \
    - (b * x0) / X0 * (2 / (x - x0) - (2 * x + b) / X - 4 * (2 * x0 + b) / (Q * Q + (2 * x + b) * (2 * x + b)))))
    out = (-rs / (3 * n)) * out
    return out

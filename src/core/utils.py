import numpy as np
from PyQt6.QtGui import QVector3D, QVector4D, QMatrix4x4

def qvector3d_to_numpy(qvector):
    """Convert QVector3D to numpy array."""
    return np.array([qvector.x(), qvector.y(), qvector.z()])

def qvector4d_to_numpy(qvector):
    """Convert QVector4D to numpy array."""
    return np.array([qvector.x(), qvector.y(), qvector.z(), qvector.w()])

def numpy_to_qvector3d(array):
    """Convert numpy array to QVector3D."""
    return QVector3D(array[0], array[1], array[2])

def qmatrix4x4_to_numpy(qmatrix):
    """Convert QMatrix4x4 to numpy array."""
    return np.array([
        [qmatrix.row(i).x(), qmatrix.row(i).y(), qmatrix.row(i).z(), qmatrix.row(i).w()]
        for i in range(4)
    ]) 
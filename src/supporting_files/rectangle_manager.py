from minimal_ctypes_opencv import *


class AARect:
    """A rectangle (bounding box) and its running id"""

    def __init__(self, x1, y1, x2, y2, object_id):
        if x1 < x2:
            self.x1 = x1
            self.x2 = x2
        else:
            self.x1 = x2
            self.x2 = x1
        if y1 < y2:
            self.y1 = y1
            self.y2 = y2
        else:
            self.y1 = y2
            self.y2 = y1
        self.object_id = object_id

    def show(self):
        print("x1=", self.x1, "  y1=", self.y1, "  x2=", self.x2, "  y2=", self.y2, "  id=", self.object_id)


# C type matching Python type
class CAARect(ctypes.Structure):
    _fields_ = [("x1", ctypes.c_int), ("y1", ctypes.c_int), ("x2", ctypes.c_int), ("y2", ctypes.c_int),
                ("objectId", ctypes.c_int)]


# convert AARect to c_AARect
def to_c_aa_rect(r):
    return CAARect(x1=int(r.x1), y1=int(r.y1), x2=int(r.x2), y2=int(r.y2), objectId=int(r.object_id))


# convert c_AARect to AARect
def to_aa_rect(c_r):
    return AARect(c_r.x1, c_r.y1, c_r.x2, c_r.y2, c_r.objectId)

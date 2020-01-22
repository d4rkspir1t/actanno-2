#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Tkinter import Tk, Canvas, Frame, BOTH, Listbox, Toplevel, Message, Button, Entry, Scrollbar, Scale, IntVar, StringVar
from Tkinter import N, S, W, E, NW, SW, NE, SE, CENTER, END, LEFT, RIGHT, X, Y, TOP, BOTTOM, HORIZONTAL, DISABLED
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageTk
import pyscreenshot as ImageGrab
import sys
import glob
import copy
import tkMessageBox
import tkSimpleDialog
import os
import xml.etree.ElementTree as xml

import matplotlib.image as mpimg
import numpy as np

from minimal_ctypes_opencv import *
from config import cfg
from config import cfg_from_file


def mkdir_p(path):
    import errno
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


# ***************************************************************************
# Global constants
# ***************************************************************************

MAX_object_id = 999
CORNER_DIST_THR = 8
CENTER_DIST_THR = 10
CORNER_SIZE = 30
CENTER_SIZE = 30
JUMP_FRAMES = 25

TITLE = "Actanno V3.0"

# ***************************************************************************
# The data structure storing the annotations
# ***************************************************************************

# change the list below to define your own classes
classnames = ["null"]
# classnames = ["head","fullbody","right-hand","left-hand"]
# ***************************************************************************
# XML parsing helper functions
# ***************************************************************************

# Return the the given tag in the given tree, and ensure that this tag is
# present only a single time.
bindings = "\
        --------------------------------------------------------\n \
        Navigation : \n \
            <Key-Left> : prevFrame \n \
            <Key-BackSpace> : prevFrame \n \
            <Key-Right> : nextFrame \n \
            <Next> : nextFrameFar \n \
            <Prior> : prevFrameFar \n \
        ----------------------------\n \
        Save and quit : \n \
            q : quit \n \
            s : saveXML \n \
        --------------------------------------------------------\n \
        Propagation : \n \
            f : go to next frame + force propagation \n \
            p : go to next frame + force propagation of rectangle with focus \n \
            <Key-space> : go to next frame + propagation (no forcing)\n \
        --------------------------------------------------------\n \
        Deletion : \n \
            d : delete rectangle with focus \n \
            D : delete all rectangles \n \
        --------------------------------------------------------\n \
        Select objects : \n \
            1 : choseobjectId1 \n \
            2 : choseobjectId2 \n \
            3 : choseobjectId3 \n \
            4 : choseobjectId4 \n \
            5 : choseobjectId5 \n \
            6 : choseobjectId6 \n \
            7 : choseobjectId7 \n \
            8 : choseobjectId8 \n \
            9 : choseobjectId9 \n \
            0 : choseobjectId10 \n"


def get_single_tag(tree, tagname):
    rv = tree.findall(tagname)
    if len(rv) != 1:
        tkMessageBox.showinfo(TITLE, "tag " + tagname + " needs to occur a single time at this point!")
        sys.exit(1)
    return rv[0]


# Return an attribute value. Check for its existence
def get_att(node, attname):
    rv = node.get(attname)
    if rv is None:
        tkMessageBox.showinfo(TITLE, "attribute " + attname + " not found in tag " + node.tag)
        sys.exit(1)
    return rv


# ***************************************************************************


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
        print "x1=", self.x1, "  y1=", self.y1, "  x2=", self.x2, "  y2=", self.y2, "  id=", self.object_id


# ***************************************************************************
# C type matching Python type
class c_AARect(ctypes.Structure):
    _fields_ = [("x1", ctypes.c_int), ("y1", ctypes.c_int), ("x2", ctypes.c_int), ("y2", ctypes.c_int), ("objectId", ctypes.c_int)]


# ***************************************************************************
# convert AARect to c_AARect
def to_c_aa_rect(r):
    return c_AARect(x1=int(r.x1), y1=int(r.y1), x2=int(r.x2), y2=int(r.y2), objectId=int(r.object_id))


# ***************************************************************************
# convert c_AARect to AARect
def to_aa_rect(c_r):
    return AARect(c_r.x1, c_r.y1, c_r.x2, c_r.y2, c_r.objectId)


# ***************************************************************************
class SemMousePos:
    """A semantic mouse position: in which rectangle (index) is the mouse
    and which semantic position does it occupy. sempose can be:
    ul	upper left corner
    ur	upper right corner
    ll	lower left corner
    lr	lower right corner
    c	center
    g	general position in the recangle
    n	no rectangles"""

    def __init__(self, index, sem_pos):
        self.index = index
        self.sem_pos = sem_pos


# ***************************************************************************


class AAFrame:
    """All rectangles of a frame"""

    def __init__(self):
        self.rects = []

    def get_rects(self):
        return self.rects

    # Check the position of the mouse cursor with respect to corners of all
    # the rectangles, as well as the centers. If it is not near anything,
    # still check for the nearest center.
    # position x,y
    def get_sem_mouse_pos(self, x, y):
        # First check for the corners
        min_val = 99999999
        arg_idx = -1
        arg_sem = ''
        for (i, r) in enumerate(self.rects):
            d = (r.x1 - x) * (r.x1 - x) + (r.y1 - y) * (r.y1 - y)
            if d < min_val:
                min_val = d
                arg_idx = i
                arg_sem = 'ul'
            d = (r.x1 - x) * (r.x1 - x) + (r.y2 - y) * (r.y2 - y)
            if d < min_val:
                min_val = d
                arg_idx = i
                arg_sem = 'll'
            d = (r.x2 - x) * (r.x2 - x) + (r.y1 - y) * (r.y1 - y)
            if d < min_val:
                min_val = d
                arg_idx = i
                arg_sem = 'ur'
            d = (r.x2 - x) * (r.x2 - x) + (r.y2 - y) * (r.y2 - y)
            if d < min_val:
                min_val = d
                arg_idx = i
                arg_sem = 'lr'

        # We are near enough to a corner, we are done
        if min_val < CORNER_DIST_THR * CORNER_DIST_THR:
            return SemMousePos(arg_idx, arg_sem)

        # Now check for the nearest center
        min_val = 99999999
        arg_idx = -1
        for (i, r) in enumerate(self.rects):
            cx = 0.5 * (r.x1 + r.x2)
            cy = 0.5 * (r.y1 + r.y2)
            d = (cx - x) * (cx - x) + (cy - y) * (cy - y)
            if d < min_val:
                min_val = d
                arg_idx = i

        if arg_idx < 0:
            return SemMousePos(-1, "n")

        if min_val < CENTER_DIST_THR * CENTER_DIST_THR:
            return SemMousePos(arg_idx, "c")
        else:
            return SemMousePos(arg_idx, "g")


# ***************************************************************************


class AAController:
    def __init__(self):
        # yet unassigned inits
        self.old_frame = None
        # An array holding an AAFrame object for each frame of the video
        self.frames = []
        # An array holding the classnr for each object nr. ("object_id")
        self.class_assignations = []
        # The nr. of the currently visible frame
        self.cur_frame_nr = 0
        self.cur_image = None
        self.aid_img = None
        self.switch_activated = False

        if len(sys.argv) < 1:
            self.usage()

        # dataset name
        self.dataset_name = cfg.DATASET_NAME
        self.video_name = cfg.FOLDER_NAME
        # print "self.videoname=", self.video_name
        # owner name
        self.owner = cfg.OWNER
        # folder name
        self.folder_name = cfg.FOLDER_NAME
        # voc path
        self.voc_path = cfg.MAIN_DIR + cfg.VOC_DIR
        # rgb
        prefix = cfg.MAIN_DIR + cfg.RGB_PREFIX
        self.filenames = sorted(glob.glob(prefix + "*"))
        if len(self.filenames) < 1:
            print >> sys.stderr, "Did not find any rgb frames! Is the prefix correct? Prefix: ", prefix
            self.usage()
        for i in range(len(self.filenames)):
            self.frames.append(AAFrame())
            self.class_assignations.append({})

        # if depth
        if cfg.D_PREFIX != "default":
            print("USING RGB AND DEPTH")
            self.depth_available = True
            prefix_depth = cfg.MAIN_DIR + cfg.D_PREFIX
            self.filenames_depth = sorted(glob.glob(prefix_depth + "*"))
            if len(self.filenames_depth) < 1:
                print >> sys.stderr, "Did not find any depths frames! Is the prefix correct?"
                self.usage()

            self.array_rgb2depth_ts = np.zeros(len(self.filenames), dtype=np.int)
            for id_img_rgb, filename_rgb in enumerate(self.filenames):
                split_token = cfg.RGB_PREFIX
                if '/' in cfg.RGB_PREFIX:
                    split_token = cfg.RGB_prefix.split('/')[1]
                ts_rgb = int(filename_rgb.split(split_token)[-1].split(".")[0])
                id_img_depth_closest = 0
                ts_depth_closest = 0
                for id_img_depth, filename_depth in enumerate(self.filenames_depth):
                    ts_depth = int(filename_depth.split(split_token)[-1].split(".")[0])
                    if abs(ts_rgb - ts_depth) <= abs(ts_rgb - ts_depth_closest):
                        ts_depth_closest = ts_depth
                        id_img_depth_closest = id_img_depth
                self.array_rgb2depth_ts[id_img_rgb] = id_img_depth_closest
        else:
            print("USING RGB ONLY")
            self.depth_available = False

        self.output_filename = cfg.MAIN_DIR + cfg.XML_PREFIX
        self.human_tracker_xml = cfg.MAIN_DIR + cfg.HUM_TRA_PREFIX
        if cfg.AID_IMG != 'default':
            self.aid_filename = cfg.MAIN_DIR + cfg.AID_IMG
        # If the given XML file exists, parse it

        if not os.path.isdir(os.path.dirname(self.output_filename)):
            os.makedirs(os.path.dirname(self.output_filename))
        if os.path.isfile(self.output_filename):
            if os.stat(self.output_filename).st_size > 0:
                self.parse_xml()
        else:
            # If it does NOT exist, let's try to create one
            if not os.path.exists(self.output_filename):
                # s = "Could not save to the specified XML file. Please check the location. Does the directory exist? Dir: " + self.output_filename
                # tkMessageBox.showinfo(TITLE, s)
                # sys.exit(1)
                tkMessageBox.showinfo(TITLE, "XML File " + self.output_filename + " does not exist. Creating a new one.")
                if cfg.HUM_TRA_PREFIX is not "default":
                    # print 'LOADING TRIGGERED'
                    self.load_human_tracked_xml()

    @staticmethod
    def usage():
        print >> sys.stderr, "Usage:"
        print >> sys.stderr, sys.argv[0], " <output-xml-filename> <framefileprefix RGB> <framefileprefix depth>"
        sys.exit(1)

    # Check the current annotation for validity
    def check_validity(self):
        msg = ''
        # Check for several occurrences of a object_id in the same frame.
        for (frnr, fr) in enumerate(self.frames):
            msg = msg + self.check_validity_frame(frnr)

        # Check for unassigned ClassAssignations (no known object class)
        msg2 = ''
        # print 'fr len ', len(self.frames)
        for fr_no in range(len(self.frames)-1):
            for (i, x) in self.class_assignations[fr_no].items():
                if x < 0:
                    msg2 = msg2 + str(i + 1) + ","
            if msg2 != '':
                msg2 = "The following activities do not have assigned classes: " + msg2 + "\n"
            msg = msg + msg2
        return msg

    # Check a single frame for validity (multiple identical ClassAssignations)
    def check_validity_frame(self, framenr):
        msg = ''
        ids = set()
        for r in self.frames[framenr].rects:
            if r.object_id in ids:
                msg = msg + 'Activity nr. ' + str(r.object_id) + ' occurs multiple times in frame nr. ' + str(
                    framenr + 1) + '.\n'
            else:
                ids.add(r.object_id)
        return msg

    # Open the image corresponding to the current frame number,
    # set the property self.curImage, and return it
    def cur_frame(self):
        if self.switch_activated and self.depth_available:
            # find the depth image whose timestamp is the closer from the rgb image
            # print "using depth images"
            name, ext = os.path.splitext(self.filenames_depth[self.array_rgb2depth_ts[self.cur_frame_nr]])
            path = self.filenames_depth[self.array_rgb2depth_ts[self.cur_frame_nr]]
        else:
            # print "using rgb images"
            name, ext = os.path.splitext(self.filenames[self.cur_frame_nr])
            path = self.filenames[self.cur_frame_nr]
        # print name
        if ext == ".png":
            # png = Image.open(self.filenames[self.curFrameNr])#.convert('L')
            img_matplotlib = mpimg.imread(path)
            value_max = np.amax(img_matplotlib)
            scale = 254. / value_max
            png = Image.fromarray(np.uint8(img_matplotlib * scale))
            # print "max(data)", max(data),"min(data)", min(data)
            self.cur_image = png.convert('RGB')
        elif ext == ".jpg":
            self.cur_image = Image.open(self.filenames[self.cur_frame_nr])
        else:
            print "def curFrame(self): Extension not supported but trying anyway. [", ext, "]"
            self.cur_image = Image.open(self.filenames[self.cur_frame_nr])
        # print "frame nr. ",self.curFrameNr, "=",self.filenames[self.curFrameNr]
        return self.cur_image

    def set_aid(self):
        path = self.aid_filename
        img_matplotlib = mpimg.imread(path)
        value_max = np.amax(img_matplotlib)
        scale = 254. / value_max
        png = Image.fromarray(np.uint8(img_matplotlib * scale))
        self.aid_img = png.convert('RGB')
        return self.aid_img

    # Remove all rectangles of the current frame
    def delete_all_rects(self):
        self.frames[self.cur_frame_nr].rects = []
        self.class_assignations[self.cur_frame_nr] = {}

    # Remove the rectangle with the given index from the list
    # of rectangles of the currently selected frame
    def delete_rect(self, index):
        # print 'To delete: ', index
        self.class_assignations[self.cur_frame_nr].pop(index+1, None)
        del self.frames[self.cur_frame_nr].rects[index]

    def next_frame(self, do_propagate, force):
        if self.cur_frame_nr < len(self.filenames) - 1:
            self.cur_frame_nr += 1
        # if the next frame does NOT contain any rectangles,
        # propagate the previous ones
        if do_propagate:
            x = len(self.frames[self.cur_frame_nr].rects)
            print "we have", x, "frames"
            if x > 0 and not force:
                print "No propagation, target frame is not empty"
            else:
                self.frames[self.cur_frame_nr].rects = []
                y = len(self.frames[self.cur_frame_nr - 1].rects)
                if y > 0:
                    # Tracking code goes here .....
                    print "Propagating ", y, "rectangle(s) to next frame"
                    prev_frame_classes = self.class_assignations[self.cur_frame_nr - 1].copy()
                    self.class_assignations[self.cur_frame_nr] = prev_frame_classes
                    if trackingLib is None:
                        # simple copy
                        print "simple copy"
                        self.cur_frame()
                        self.frames[self.cur_frame_nr].rects = copy.deepcopy(self.frames[self.cur_frame_nr - 1].rects)
                    else:
                        # JM tracking
                        print "use JM tracking"
                        self.old_frame = self.cur_image
                        self.cur_frame()

                        for inrect in self.frames[self.cur_frame_nr - 1].rects:
                            # convert PIL image to OpenCV image
                            cv_old_img = cvCreateImageFromPilImage(self.old_frame)
                            cv_cur_img = cvCreateImageFromPilImage(self.cur_image)
                            # No need to invoke cvRelease...()

                            # convert Python types to C types
                            c_inrect = to_c_aa_rect(inrect)
                            c_outrect = c_AARect()

                            # call C++ tracking lib
                            trackingLib.track_block_matching(ctypes.byref(cv_old_img), ctypes.byref(cv_cur_img),ctypes.byref(c_inrect), ctypes.byref(c_outrect))

                            # convert C types to Python types
                            outrect = to_aa_rect(c_outrect)
                            self.frames[self.cur_frame_nr].rects.append(outrect)

                else:
                    print "No frames to propagate"
        else:
            self.cur_frame()
        self.export_xml_filename("save.xml")
        return self.cur_image

    def next_frame_prop_current_rect(self, rect_index):
        propagate_id = self.frames[self.cur_frame_nr].rects[rect_index].object_id
        print "Rect[", rect_index, "].object_id == ", propagate_id

        if self.cur_frame_nr < len(self.filenames) - 1:
            self.cur_frame_nr += 1
            print "Propagating rectangle", propagate_id, " to new frame"
            x = len(self.frames[self.cur_frame_nr].rects)
            y = len(self.frames[self.cur_frame_nr - 1].rects)
            self.class_assignations[self.cur_frame_nr][propagate_id] = self.class_assignations[self.cur_frame_nr-1][propagate_id]
            print "we have ", x, " objects"
            print "we had  ", y, " objects"

            # get old rect to propagate
            rect_to_propagate = self.frames[self.cur_frame_nr - 1].rects[rect_index]

            # get his new position by tracking
            if trackingLib is None:
                # simple copy
                print "simple copy"
                self.cur_frame()
                rect_propagated = copy.deepcopy(rect_to_propagate)
            else:
                # JM tracking
                print "use JM tracking"
                self.old_frame = self.cur_image
                self.cur_frame()

                # convert PIL image to OpenCV image
                cv_old_img = cvCreateImageFromPilImage(self.old_frame)
                cv_cur_img = cvCreateImageFromPilImage(self.cur_image)
                # No need to invoke cvRelease...()

                # convert Python types to C types
                c_inrect = to_c_aa_rect(rect_to_propagate)
                c_outrect = c_AARect()

                # call C++ tracking lib
                trackingLib.track_block_matching(ctypes.byref(cv_old_img), ctypes.byref(cv_cur_img),
                                                 ctypes.byref(c_inrect), ctypes.byref(c_outrect))

                # convert C types to Python types
                rect_propagated = to_aa_rect(c_outrect)
            # self.frames[self.curFrameNr].rects.append(outrect)

            rect_propagated.object_id = propagate_id

            # update it or add it
            rect_already_exists = False
            for i, currentrect in enumerate(self.frames[self.cur_frame_nr].rects):
                if currentrect.object_id == propagate_id:
                    print "Rectangle found. Updating."
                    self.frames[self.cur_frame_nr].rects[i] = copy.deepcopy(rect_propagated)
                    rect_already_exists = True
                    break

            if not rect_already_exists:
                self.frames[self.cur_frame_nr].rects.append(rect_propagated)

        # self.curFrame()
        self.export_xml_filename("save.xml")
        return self.cur_image

    def change_frame(self, id_frame):
        self.cur_frame_nr = int(id_frame) - 1
        self.export_xml_filename("save.xml")
        return self.cur_frame()

    def next_frame_far(self):
        if self.cur_frame_nr < len(self.filenames) - JUMP_FRAMES:
            self.cur_frame_nr += JUMP_FRAMES
        else:
            self.cur_frame_nr = len(self.filenames) - 1
        self.export_xml_filename("save.xml")
        return self.cur_frame()

    def prev_frame(self):
        if self.cur_frame_nr > 0:
            self.cur_frame_nr -= 1
        self.export_xml_filename("save.xml")
        return self.cur_frame()

    def prev_frame_far(self):
        if self.cur_frame_nr >= JUMP_FRAMES:
            self.cur_frame_nr -= JUMP_FRAMES
        else:
            self.cur_frame_nr = 0
        self.export_xml_filename("save.xml")
        return self.cur_frame()

    def get_rects(self):
        return self.frames[self.cur_frame_nr].get_rects()

    def add_rect(self, x1, y1, x2, y2, object_id, fnr=-1, aclass=-1):
        if fnr == -1:
            fnr = self.cur_frame_nr
        if fnr >= len(self.frames):
            raise Exception()
        self.frames[fnr].get_rects().append(AARect(x1, y1, x2, y2, object_id))
        # print 'addrect object id ', object_id
        self.class_assignations[fnr][object_id] = aclass

    def del_rect(self, index):
        del self.frames[self.cur_frame_nr].get_rects()[index]

    def get_sem_mouse_pos(self, x, y):
        return self.frames[self.cur_frame_nr].get_sem_mouse_pos(x, y)

    # Update the running id for a rectangle index
    def update_object_id(self, index_rect, new_id):
        self.frames[self.cur_frame_nr].rects[index_rect].object_id = new_id
        self.use_object_id(new_id)

    # Tell the system the given object_id is used. If the array holding the classes
    # for the different ids is not large enough, grow it and insert -1 as class
    def use_object_id(self, new_id):
        # print 'useobjectid curframenr ', self.cur_frame_nr
        neededcap = new_id - len(self.class_assignations[self.cur_frame_nr].keys())
        if neededcap > 0:
            for i in range(neededcap):
                # print 'useobjectid new_id ', new_id
                self.class_assignations[self.cur_frame_nr-1][new_id] = -1
        print "new run id array", self.class_assignations[self.cur_frame_nr]

    def export_xml(self):
        self.export_xml_filename(self.output_filename)

    def export_xml_filename(self, filename):
        # Get maximum running id
        maxid = -1
        for (i, f) in enumerate(self.frames):
            for (j, r) in enumerate(f.get_rects()):
                if r.object_id > maxid:
                    maxid = r.object_id
        fd = None
        try:
            fd = open(filename, 'w')
        except IOError:
            tkMessageBox.showinfo(TITLE, "Could not save to the specified XML file. Please check the location. "
                                         "Does the directory exist?")
        print >> fd, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        print >> fd, "<tagset>"
        print >> fd, "  <video>"
        print >> fd, "	<videoName>" + self.video_name + "</videoName>"

        # self.filenames[self.curFrameNr]
        # Travers all different running id's
        for cur_object_id in range(maxid):
            found_rects = False
            for (i, f) in enumerate(self.frames):
                for (j, r) in enumerate(f.get_rects()):
                    if cur_object_id+1 in self.class_assignations[i].keys() and cur_object_id+1 == r.object_id:
                        obj_class = self.class_assignations[i][r.object_id]
                        if not found_rects:
                            found_rects = True
                            fd.write("	<object nr=\"" + str(cur_object_id + 1) + "\">\n")
                        s = "	  <bbox x=\"" + str(int(r.x1)) + "\" y=\"" + str(int(r.y1))
                        s = s + "\" width=\"" + str(int(r.x2 - r.x1 + 1)) + "\" height=\"" + str(int(r.y2 - r.y1 + 1))
                        s = s + "\" framenr=\"" + str(i + 1)
                        s = s + "\" framefile=\"" + self.filenames[i]
                        # print 'exportxmlfilename object id ', cur_object_id+1
                        # print 'objclass ', obj_class
                        s = s + "\" class=\"" + str(obj_class) + "\"/>\n"
                        fd.write(s)
            if found_rects:
                print >> fd, "	</object>"
        print >> fd, "  </video>"
        print >> fd, "</tagset>"
        fd.close()

    def export_xml2voc(self):
        print "Exporting..."
        mkdir_p(self.voc_path)
        for (i, f) in enumerate(self.frames):
            head, tail = os.path.split(self.filenames[i])
            filename = self.voc_path + tail[:-3] + "xml"
            fd = None
            try:
                fd = open(filename, 'w')
            except IOError:
                tkMessageBox.showinfo(TITLE, "Could not save to the specified XML file. Please check the location. "
                                             "Does the directory exist?")

            print >> fd, "<annotation>"
            print >> fd, "	<folder>" + self.folder_name + "</folder>"
            print >> fd, "	<filename>" + tail + "</filename>"
            print >> fd, "	<source>"
            print >> fd, "		<database>The " + self.dataset_name + " database</database>"
            print >> fd, "	</source>"
            print >> fd, "	<owner>" + self.owner + "</owner>"
            print >> fd, "	<size>"
            print >> fd, "		<width>640</width>"
            print >> fd, "		<height>480</height>"
            print >> fd, "		<depth>1</depth>"
            print >> fd, "	</size>"
            print >> fd, "	<segmented>0</segmented>"

            for (j, r) in enumerate(f.get_rects()):
                print >> fd, "	<object>"
                print >> fd, "		<name>" + str(self.class_assignations[i][r.object_id]) + "</name>"
                print >> fd, "		<pose>unknown</pose>"
                print >> fd, "		<truncated>-1</truncated>"
                print >> fd, "		<difficult>0</difficult>"
                print >> fd, "		<bndbox>"
                print >> fd, "			<xmin>" + str(int(r.x1)) + "</xmin>"
                print >> fd, "			<ymin>" + str(int(r.y1)) + "</ymin>"
                print >> fd, "			<xmax>" + str(int(r.x2)) + "</xmax>"
                print >> fd, "			<ymax>" + str(int(r.y2)) + "</ymax>"
                print >> fd, "		</bndbox>"
                print >> fd, "	</object>"

            print >> fd, "</annotation>"
            fd.close()
        print "Done !"
        tkMessageBox.showinfo("VOC export", "File(s) saved successfully!")

    def parse_xml(self):
        tree = xml.parse(self.output_filename)
        # root_element = tree.getroot()

        # Get the single video tag
        vids = tree.findall("video")
        if len(vids) < 1:
            tkMessageBox.showinfo(TITLE, "No <video> tag found in the input XML file!")
            sys.exit(1)
        if len(vids) > 1:
            tkMessageBox.showinfo(TITLE, "Currently only a single <video> tag is supported per XML file!")
            sys.exit(1)
        vid = vids[0]

        # Get all the objects
        objectnodes = vid.findall("object")
        if len(objectnodes) < 1:
            tkMessageBox.showinfo(TITLE, "The given XML file does not contain any objects.")
        for a in objectnodes:
            # Add the classnr to the object_id array. Grow if necessary
            anr = int(get_att(a, "nr"))

            # Get all the bounding boxes for this object
            bbs = a.findall("bbox")
            if len(bbs) < 1:
                tkMessageBox.showinfo(TITLE, "No <bbox> tags found for an object in the input XML file!")
                sys.exit(1)
            for bb in bbs:

                # Add the bounding box to the frames() list
                bfnr = int(get_att(bb, "framenr"))
                bx = int(get_att(bb, "x"))
                by = int(get_att(bb, "y"))
                bw = int(get_att(bb, "width"))
                bh = int(get_att(bb, "height"))
                aclass = int(get_att(bb, "class"))
                while len(self.class_assignations) < bfnr:
                    self.class_assignations.append({})
                try:
                    self.add_rect(bx, by, bx + bw - 1, by + bh - 1, anr, bfnr - 1, aclass)
                except IndexError:
                    print "*** ERROR ***"
                    print "The XML file contains rectangles in frame numbers which are outside of the video"
                    print "(frame number too large). Please check whether the XML file really fits to these"
                    print "frames."
                    sys.exit(1)

    def load_human_tracked_xml(self):
        tree = xml.parse(self.human_tracker_xml)
        # root_element = tree.getroot()

        # Get the single video tag
        vids = tree.findall("video")
        if len(vids) < 1:
            tkMessageBox.showinfo(TITLE, "No <video> tag found in the input XML file!")
            sys.exit(1)
        if len(vids) > 1:
            tkMessageBox.showinfo(TITLE, "Currently only a single <video> tag is supported per XML file!")
            sys.exit(1)
        vid = vids[0]

        # Get all the objects
        objectnodes = vid.findall("object")
        if len(objectnodes) < 1:
            tkMessageBox.showinfo(TITLE, "The given XML file does not contain any objects.")
        for a in objectnodes:
            # Add the classnr to the object_id array. Grow if necessary
            anr = int(get_att(a, "nr"))
            # print "size of object_id array:", len(self.ClassAssignations), "array:", self.ClassAssignations

            # Get all the bounding boxes for this object
            bbs = a.findall("bbox")
            if len(bbs) < 1:
                tkMessageBox.showinfo(TITLE, "No <bbox> tags found for an object in the input XML file!")
                sys.exit(1)
            for bb in bbs:

                # Add the bounding box to the frames() list
                bfnr = int(get_att(bb, "framenr"))
                bx = int(get_att(bb, "x"))
                by = int(get_att(bb, "y"))
                bw = int(get_att(bb, "width"))
                bh = int(get_att(bb, "height"))
                try:
                    self.add_rect(bx, by, bx + bw - 1, by + bh - 1, anr, bfnr - 1, -1)
                except IndexError:
                    print "*** ERROR ***"
                    print "The XML file contains rectangles in frame numbers which are outside of the video"
                    print "(frame number too large). Please check whether the XML file really fits to these"
                    print "frames."
                    sys.exit(1)


# ***************************************************************************
# GUI
# The state variable self.state can take one of the following values:
# ul 	we are currently moving the upper left corner
# ur 	we are currently moving the upper right corner
# ll 	we are currently moving the lower left corner
# lr 	we are currently moving the lower right corner
# c 	we are currently moving the window
# d	we are currently drawing a new rectangle
# i	we are currently choosing the running id
# "" 	(empty) no current object
# ***************************************************************************


class Example(Frame):
    def __init__(self, parent, cur_path):
        Frame.__init__(self, parent)
        self.parent = parent
        self.cur_path = cur_path
        self.ct = AAController()
        font_path = os.path.dirname(os.path.realpath(__file__))
        self.img_font = ImageFont.truetype(os.path.join(font_path, "FreeSans.ttf"), 30)
        self.init_ui()
        self.event_counter = 0

    # Interface startup: create all widgets and create key and mouse event
    # bindings
    def init_ui(self):
        self.parent.title(TITLE + " (frame nr.1 of " + str(len(self.ct.filenames)) + ")")
        self.pack(fill=BOTH, expand=1)
        self.img = self.ct.cur_frame()
        self.cur_frame = ImageTk.PhotoImage(self.img)

        if cfg.AID_IMG != 'default':
            self.aid_img = self.ct.set_aid()
            self.aid_img = self.aid_img.resize((361, 836), Image.ANTIALIAS)
            self.aid_frame = ImageTk.PhotoImage(self.aid_img)

        self.img_trash = ImageTk.PhotoImage(Image.open(self.cur_path + "/trashcan.png"))
        self.img_move = ImageTk.PhotoImage(Image.open(self.cur_path + "/move.png"))
        # create canvas
        self.canvas = Canvas(self.parent, width=self.img.size[0], height=self.img.size[1])
        if cfg.AID_IMG != 'default':
            self.aid_canvas = Canvas(self.parent, width=self.aid_img.size[0], height=self.aid_img.size[1])
        # create scale bar
        self.scalevar = IntVar()
        self.xscale = Scale(self.parent, variable=self.scalevar, from_=1, to=len(self.ct.filenames),
                            orient=HORIZONTAL, command=self.change_frame)

        self.canvas.create_image(0, 0, anchor=NW, image=self.cur_frame)
        if cfg.AID_IMG != 'default':
            self.aid_canvas.create_image(0,0, anchor=NW, image=self.aid_frame)

        self.object_id_box = Listbox(self.parent, width=50)
        self.id_text_var = StringVar()
        self.id_text_var.set("Next id: 0")
        self.id_setter = Button(self.parent, textvariable=self.id_text_var)
        self.switch_button = Button(self.parent, text="RGB <-> Depth", state=DISABLED)
        self.save_button = Button(self.parent, text="SAVE")
        self.export_2voc = Button(self.parent, text="EXPORT2VOC")
        self.quit_button = Button(self.parent, text="QUIT")
        self.fn_entry = Entry(self.parent)  # state='readonly')
        self.grid(sticky=W + E + N + S)

        # position
        self.canvas.grid(row=0, column=0, rowspan=6)
        self.object_id_box.grid(row=0, column=1, sticky=N + S)
        self.fn_entry.grid(row=1, column=1)
        self.id_setter.grid(row=2, column=1)
        # self.switch_button.grid(row=2, column=1)
        self.save_button.grid(row=3, column=1)
        self.export_2voc.grid(row=4, column=1)
        self.quit_button.grid(row=5, column=1)
        self.xscale.grid(row=6, sticky=W + E)
        if cfg.AID_IMG != 'default':
            self.aid_canvas.grid(row=0, column=3, rowspan=6)

        # bindings
        self.canvas.bind("<Key-Left>", self.prev_frame)
        self.canvas.bind("<Key-BackSpace>", self.prev_frame)
        self.canvas.bind("<Key-Right>", self.next_frame)
        self.canvas.bind("<Next>", self.next_frame_far)
        self.canvas.bind("<Prior>", self.prev_frame_far)  # the space key
        self.canvas.bind("<Motion>", self.mouse_move)
        self.canvas.bind("<Button-1>", self.left_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.left_mouse_up)
        self.canvas.bind("<Button-3>", self.right_mouse_down)
        self.canvas.bind("<ButtonRelease-3>", self.right_mouse_up)
        self.canvas.bind("q", self.quit)
        self.canvas.bind("s", self.save_xml)
        self.canvas.bind("f", self.next_frame_w_prop_forced)
        self.canvas.bind("p", self.next_frame_w_prop_forced_selected_rect)
        self.canvas.bind("d", self.delete_cur_rect)
        self.canvas.bind("D", self.delete_all_rects)
        self.canvas.bind("l", self.propagate_all_labels)
        self.canvas.bind("o", self.propagate_label)
        self.object_id_box.bind("<Key-space>", self.next_frame_w_rop)  # the space key
        self.canvas.bind("<Key-space>", self.next_frame_w_rop)  # the space key
        self.object_id_box.bind("<<ListboxSelect>>", self.object_id_box_click)
        self.id_setter.bind("<Button-1>", self.set_next_id)
        self.save_button.bind("<Button-1>", self.save_xml)
        self.export_2voc.bind("<Button-1>", self.save_xml2voc)
        self.quit_button.bind("<Button-1>", self.quit)

        # Variable inits
        self.state = ""
        self.mousex = 1
        self.mousey = 1
        # print 'curframe ', self.ct.cur_frame_nr
        self.object_id_proposed_for_new_rect = len(self.ct.class_assignations[self.ct.cur_frame_nr].keys()) + 1
        self.id_text_var.set("Next id: %d" % self.object_id_proposed_for_new_rect)
        self.display_anno()
        self.display_class_assignations()
        self.fn_entry.delete(0, END)
        self.fn_entry.insert(0, self.ct.video_name)
        self.is_modified = False
        self.canvas.focus_force()

    def get_canvas_box(self):
        x = self.canvas.winfo_rootx() + self.canvas.winfo_x()
        # print 'win ', self.canvas.winfo_x(), ' ', self.canvas.winfo_rootx()
        # print 'win ', self.canvas.winfo_y(), ' ', self.canvas.winfo_rooty()
        # y = self.canvas.winfo_rooty() + self.canvas.winfo_y()
        y = self.canvas.winfo_rooty()
        x1 = x + self.canvas.winfo_width()
        y1 = y + self.canvas.winfo_height()
        box = (x, y, x1, y1)
        # print box
        return box

    def check_validity(self):
        msg = self.ct.check_validity()
        if len(self.fn_entry.get()) < 1:
            msg = msg + "The video name is empty.\n"
        # if len(msg) > 0:
        #     tkMessageBox.showinfo(TITLE, "There are errors in the annotation:\n\n" + msg +
        #                           "\nThe file has been saved. Please address the problem(s) and save again.")

    def quit(self, event):
        # print "quit method"
        self.ct.videoname = self.fn_entry.get()
        ok = True

        if self.is_modified:
            if tkMessageBox.askyesno(title='Unsaved changes', message='The annotation has been modified. '
                                                                      'Do you really want to quit?'):
                tkMessageBox.showinfo("First help", "A backup of the latest changes can be found "
                                                    "in save.xml, just in case.")
            else:
                ok = False
        if ok:
            # close tracking library
            if trackingLib is not None:
                trackingLib.close_lib()
            self.parent.destroy()

    def save_images_with_bbox(self):
        grabcanvas = ImageGrab.grab(bbox=self.get_canvas_box())
        frame_name = 'bbox' + str(self.ct.cur_frame_nr).zfill(6) + '.png'
        path = os.path.join(cfg.BBOX_PREFIX, frame_name)
        grabcanvas.save(path)

    def update_after_jump(self):
        self.cur_frame = ImageTk.PhotoImage(self.img)
        self.display_anno()
        self.display_class_assignations()
        self.parent.title(
            TITLE + " (frame nr." + str(self.ct.cur_frame_nr + 1) + " of " + str(len(self.ct.filenames)) + ")")
        self.canvas.update()

    def change_frame(self, id_frame):
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.img = self.ct.change_frame(id_frame)
        self.update_after_jump()

    def prev_frame(self, event):
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.img = self.ct.prev_frame()
        self.update_after_jump()

    def prev_frame_far(self, event):
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.img = self.ct.prev_frame_far()
        self.update_after_jump()

    def next_frame(self, event):
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.img = self.ct.next_frame(False, False)
        self.update_after_jump()

    def next_frame_far(self, event):
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.img = self.ct.next_frame_far()
        self.update_after_jump()

    def next_frame_w_rop(self, event):
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.img = self.ct.next_frame(True, False)
        self.update_after_jump()
        self.is_modified = True

    def next_frame_w_prop_forced(self, event):
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.img = self.ct.next_frame(True, True)
        self.update_after_jump()
        self.is_modified = True

    def next_frame_w_prop_forced_selected_rect(self, event):
        sempos = self.ct.get_sem_mouse_pos(self.mousex, self.mousey)
        if sempos.index > -1:
            self.img = self.ct.next_frame_prop_current_rect(sempos.index)
        self.update_after_jump()
        self.is_modified = True

    def mouse_move(self, event):
        self.display_anno()
        self.mousex = event.x
        self.mousey = event.y
        maxx = self.img.size[0]
        maxy = self.img.size[1]

        # Put the focus on the canvas, else the other widgets
        # keep all keyboard events once they were selected.
        self.canvas.focus_force()

        if self.state == "d":
            # We currently draw a rectangle
            self.curx2 = min(maxx, max(1, event.x))
            self.cury2 = min(maxy, max(1, event.y))
            self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2, outline="blue", width=2)
        elif self.state == "i":
            # We currently choose a running id
            self.propobject_id = self.cur_object_id + (event.y - self.oldY) / 20
            if self.propobject_id < 0:
                self.propobject_id = 0
            if self.propobject_id > MAX_object_id:
                self.propobject_id = MAX_object_id
            self.canvas.create_rectangle(self.curx1, self.cury1, self.curx1 + 30, self.cury1 + 30, outline="white",
                                         fill="white")
            self.canvas.create_text(self.curx1 + 15, self.cury1 + 15, text=str(self.propobject_id),
                                    fill="blue", font=("Helvectica", "20"))
        elif self.state == "ul":
            # We currently move the upper left corner
            self.curx1 = min(maxx, max(1, event.x))
            self.cury1 = min(maxy, max(1, event.y))
            self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2, outline="blue", width=2)
        # ELtodo self.drawAnchorPoint(self.curx1, self.cury1)
        elif self.state == "ur":
            # We currently move the upper right corner
            self.curx2 = min(maxx, max(1, event.x))
            self.cury1 = min(maxy, max(1, event.y))
            self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2, outline="blue", width=2)
        # ELtodo self.drawAnchorPoint(self.curx2, self.cury1)
        # We currently move the lower left corner
        elif self.state == "ll":
            self.curx1 = min(maxx, max(1, event.x))
            self.cury2 = min(maxy, max(1, event.y))
            self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2, outline="blue", width=2)
        # ELtodo self.drawAnchorPoint(self.curx1, self.cury2)
        elif self.state == "lr":
            # We currently move the lower right corner
            self.curx2 = min(maxx, max(1, event.x))
            self.cury2 = min(maxy, max(1, event.y))
            self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2, outline="blue", width=2)
        # ELtodo self.drawAnchorPoint(self.curx2, self.cury2)
        elif self.state == "c":
            # We currently move the whole rectangle
            self.curx1 = min(maxx - 10, max(1, event.x - int(0.5 * self.cur_width)))
            self.cury1 = min(maxy - 10, max(1, event.y - int(0.5 * self.cur_heigth)))
            self.curx2 = min(maxx, max(self.curx1 + 10, max(1, event.x + int(0.5 * self.cur_width))))
            self.cury2 = min(maxy, max(self.cury1 + 10, max(1, event.y + int(0.5 * self.cur_heigth))))

            self.canvas.create_rectangle(self.curx1, self.cury1, self.curx2, self.cury2, outline="blue", width=2)
        # ELtodo self.drawAnchorPoint(event.x, event.y)
        # Drag outside of the canvas -> delete
        # if (event.x<0) or (event.x>self.img.size[0]) or (event.y<0) or (event.y>self.img.size[1]):
        #	self.canvas.create_image(self.curx1, self.cury1, anchor=NW, image=self.imgTrash)
        #	self.canvas.create_image(self.curx1, self.cury2-40, anchor=NW, image=self.imgTrash)
        #	self.canvas.create_image(self.curx2-40, self.cury1, anchor=NW, image=self.imgTrash)
        #	self.canvas.create_image(self.curx2-40, self.cury2-40, anchor=NW, image=self.imgTrash)

    def save_xml(self, event):
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.ct.videoname = self.fn_entry.get()
        self.ct.export_xml()
        self.check_validity()
        self.is_modified = False
        tkMessageBox.showinfo("Save", "File saved successfully!")

    def save_xml2voc(self, event):
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.ct.videoname = self.fn_entry.get()
        self.ct.export_xml()
        self.check_validity()
        self.is_modified = False
        self.ct.export_xml2voc()

    def activate_switch(self, event):
        self.ct.switchActivated = not self.ct.switchActivated
        # print self.ct.switchActivated
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.img = self.ct.cur_frame()
        self.update_after_jump()

    # Remove all rectangles of the current frame
    def delete_all_rects(self, event):
        self.ct.delete_all_rects()
        self.display_anno()
        self.display_class_assignations()
        self.canvas.update()
        if cfg.BBOX_PREFIX != 'default':
            self.save_images_with_bbox()
        self.is_modified = True

    # Remove the currently selected rectangle of the current frame
    def delete_cur_rect(self, event):
        sempos = self.ct.get_sem_mouse_pos(self.mousex, self.mousey)
        if sempos.index > -1:
            self.ct.delete_rect(sempos.index)
            self.display_anno()
            self.display_class_assignations()
            self.canvas.update()
            if cfg.BBOX_PREFIX != 'default':
                self.save_images_with_bbox()
        self.is_modified = True

    def left_mouse_down(self, event):
        # On a Mac the right click does not work, at least not expected
        # workaround: if the CTRL key is held with a left click, we consider
        # it a right click
        if (event.state & 0x0004) > 0:
            self.right_mouse_down(event)
            return

        # Which rectangle is the nearest one to the mouse cursor, and what is
        # its relative position (corners, center, general position)?
        sempos = self.ct.get_sem_mouse_pos(self.mousex, self.mousey)

        # We change an existing rectangle. Remove the old one from the
        # controler
        if sempos.sem_pos in ("ul", "ur", "ll", "lr", "c"):
            self.state = sempos.sem_pos
            r = self.ct.get_rects()[sempos.index]
            self.curx1 = r.x1
            self.cury1 = r.y1
            self.curx2 = r.x2
            self.cury2 = r.y2
            self.cur_width = abs(r.x2 - r.x1)
            self.cur_heigth = abs(r.y2 - r.y1)
            self.cur_object_id = r.object_id
            self.ct.del_rect(sempos.index)
        # We start drawing a new rectangle
        else:
            self.state = "d"
            self.cur_object_id = self.object_id_proposed_for_new_rect
            self.curx1 = event.x
            self.cury1 = event.y
            self.curx2 = -1
            self.cury2 = -1

        self.cur_sem_pos = SemMousePos(-1, "g")

    def left_mouse_up(self, event):
        # self.debugEvent('leftMouseUp')

        # On a Mac the right click does not work, at least not expected
        # workaround: if the CTRL key is held with a left click, we consider
        # it a right click
        if (event.state & 0x0004) > 0:
            self.right_mouse_up(event)
            return

        if self.state in ("ul", "ur", "ll", "lr", "c", "d"):
            # Are we inside the window?
            if True:  # not ((event.x<0) or (event.x>self.img.size[0]) or (event.y<0) or (event.y>self.img.size[1])):
                # If we create a new rectangle, we check whether we moved
                # since the first click (Non trivial rectangle)?
                if (self.state != "d") or (abs(event.x - self.curx1) > 5) or (abs(event.y - self.cury1) > 5):
                    self.ct.add_rect(self.curx1, self.cury1, self.curx2, self.cury2, self.cur_object_id, -1)
                    if cfg.BBOX_PREFIX != 'default':
                        self.save_images_with_bbox()
                    self.is_modified = True
                    # We just drew a new rectangle
                    if self.state == "d":
                        self.ct.use_object_id(self.cur_object_id)
                        self.display_class_assignations()
                        self.object_id_proposed_for_new_rect = self.object_id_proposed_for_new_rect + 1
                        self.id_text_var.set("Next id: %d" % self.object_id_proposed_for_new_rect)
            self.curx2 = event.x
            self.cury2 = event.y
        self.state = ""
        self.display_anno()

    def right_mouse_down(self, event):
        # print "right mouse down"
        sempos = self.ct.get_sem_mouse_pos(event.x, event.y)
        self.cur_sem_pos = sempos
        self.oldY = event.y
        # print "sempos.index", sempos.index
        if sempos.index >= 0:
            self.state = "i"
            r = self.ct.get_rects()[sempos.index]
            self.cur_object_id = r.object_id
            self.curx1 = r.x1
            self.cury1 = r.y1

    def right_mouse_up(self, event):
        if self.state == "i":
            self.ct.update_object_id(self.cur_sem_pos.index, self.propobject_id)
            self.display_class_assignations()
            self.is_modified = True
        self.state = ""

    # draw an anchor point at (x, y) coordinates
    @staticmethod
    def draw_anchor_point(draw, x, y, size=5, color="cyan"):
        x1 = x - size
        y1 = y - size
        x2 = x + size
        y2 = y + size
        draw.ellipse([x1, y1, x2, y2], outline=color)
        draw.ellipse([x1 + 1, y1 + 1, x2 - 1, y2 - 1], outline=color)
        draw.ellipse([x1 + 2, y1 + 2, x2 - 2, y2 - 2], outline=color)

    # Draw the image and the current annotation
    def display_anno(self):
        if self.state in ("ul", "ur", "ll", "lr", "c", "d", "i"):
            # We are currently in an operation, so do not search
            # the nearest rectangle. It is the one blocked at the
            # beginning of the operation
            sempos = self.cur_sem_pos
        else:
            # Search for the nearest rectangle:
            # which rectangle is the nearest one to the mouse cursor,
            # and what is its relative position (corners, center,
            # general position)?
            sempos = self.ct.get_sem_mouse_pos(self.mousex, self.mousey)

        # Init drawing
        draw_frame = self.img.copy()
        draw = ImageDraw.Draw(draw_frame)

        # Draw all rectangles
        for (i, r) in enumerate(self.ct.get_rects()):
            if i == sempos.index:
                curcol = "blue"
            else:
                curcol = "red"
            draw.rectangle([r.x1, r.y1, r.x2, r.y2], outline=curcol)
            draw.rectangle([r.x1 + 1, r.y1 + 1, r.x2 - 1, r.y2 - 1], outline=curcol)
            draw.text([r.x1 + 3, r.y1 + 2], str(r.object_id), font=self.img_font, fill=curcol)

            # Draw the icons
            if i == sempos.index:
                if sempos.sem_pos == "ul":
                    self.draw_anchor_point(draw, r.x1, r.y1)
                if sempos.sem_pos == "ur":
                    self.draw_anchor_point(draw, r.x2, r.y1)
                if sempos.sem_pos == "ll":
                    self.draw_anchor_point(draw, r.x1, r.y2)
                if sempos.sem_pos == "lr":
                    self.draw_anchor_point(draw, r.x2, r.y2)
                if sempos.sem_pos == "c":
                    cx = 0.5 * (r.x1 + r.x2)
                    cy = 0.5 * (r.y1 + r.y2)
                    self.draw_anchor_point(draw, cx, cy)

        del draw
        self.draw_photo = ImageTk.PhotoImage(draw_frame)
        self.canvas.create_image(0, 0, anchor=NW, image=self.draw_photo)

    def display_class_assignations(self):
        self.object_id_box.delete(0, END)
        # UNCOMMENT THIS FOR CMD CLASS LABEL TRACKING
        # print self.ct.class_assignations
        x = self.ct.class_assignations[self.ct.cur_frame_nr].values()
        for i in range(len(x)):
            if x[i] < 0:
                self.object_id_box.insert(END, str(i + 1) + " has no assigned class ")
            else:
                self.object_id_box.insert(END, "Human [" + str(i + 1) + "] belongs to group [" + str(x[i]) + "]")

    # a listbox item has been clicked: choose the object class for
    # a given object
    def object_id_box_click(self, event):
        self.clicked_object_id = self.object_id_box.curselection()

        class_id = tkSimpleDialog.askinteger('Set BBOX ID', 'Enter group ID for chosen person or 0 if they are not in a group')
        # print str(class_id), ' is the class id for that human.'

        object_id = int(self.clicked_object_id[0])
        # print 'objectidboxclick object id ', object_id+1
        # print 'objectidcoxclicl curfrnr ', self.ct.cur_frame_nr
        self.ct.class_assignations[self.ct.cur_frame_nr][object_id+1] = class_id
        self.display_class_assignations()
        self.is_modified = True

    def propagate_label(self, event):
        sempos = self.ct.get_sem_mouse_pos(self.mousex, self.mousey)
        # print sempos.index
        if sempos.index > -1:
            for frame_no in range(self.ct.cur_frame_nr+1, len(self.ct.class_assignations)):
                if sempos.index+1 in self.ct.class_assignations[frame_no].keys():
                    # print 'could propagate label ', frame_no, sempos.index+1
                    self.ct.class_assignations[frame_no][sempos.index+1] = self.ct.class_assignations[self.ct.cur_frame_nr][sempos.index+1]
        self.display_anno()
        self.display_class_assignations()
        self.is_modified = True

    def propagate_all_labels(self, event):
        for frame_no in range(self.ct.cur_frame_nr + 1, len(self.ct.class_assignations)):
            # print 'could propagate label ', frame_no, sempos.index+1
            for object_id in self.ct.class_assignations[self.ct.cur_frame_nr].keys():
                if object_id in self.ct.class_assignations[frame_no].keys():
                    self.ct.class_assignations[frame_no][object_id] = self.ct.class_assignations[self.ct.cur_frame_nr][object_id]
        self.display_anno()
        self.display_class_assignations()
        self.is_modified = True

    def debug_event(self, title):
        self.event_counter += 1
        # print 'event #' + str(self.event_counter), title

    def set_next_id(self, event):
        given_id = tkSimpleDialog.askinteger('Set Next ID',
                                             'Enter the id for the next bounding box you draw')
        self.object_id_proposed_for_new_rect = given_id
        self.id_text_var.set("Next id %d" % self.object_id_proposed_for_new_rect)


def onexit():
    # print "qqqq"
    ex.quit(None)


trackingLib = None


def main():
    cur_path = sys.path[0]

    global classnames
    global trackingLib

    config_path = sys.argv[1]
    cfg_file = os.path.join(config_path, 'config.yml')
    print "Loading config from >%s<" % cfg_file
    cfg_from_file(cfg_file)
    folder_path = sys.argv[2]
    cfg.MAIN_DIR = folder_path

    from os.path import normpath, basename
    cfg.FOLDER_NAME = basename(normpath(folder_path))
    cfg.MAIN_DIR = folder_path
    print "Configuration :"
    print cfg
    classnames = cfg.CLASSES

    # load C++ JM tracking library
    if os.name == 'posix':
        # ---- Mac Os
        if platform.system() == 'Darwin':
            trackingLib = ctypes.CDLL(os.path.join(cur_path, "boxtracking", "libboxtracking.dylib"))

        # ---- Linux
        else:
            trackingLib = ctypes.CDLL(os.path.join(cur_path, "boxtracking", "libboxtracking.so"))
    # ---- Windows
    elif os.name == 'nt':
        trackingLib = ctypes.CDLL(os.path.join(cur_path, "boxtracking", "libboxtracking.dll"))

    if trackingLib is not None:
        # print "JM tracking library loaded."
        trackingLib.init_lib()
    else:
        print "Failed to load JM tracking library."
    print trackingLib

    root = Tk()
    root.protocol("WM_DELETE_WINDOW", onexit)
    global ex
    ex = Example(root, cur_path)
    root.mainloop()


if __name__ == '__main__':
    main()

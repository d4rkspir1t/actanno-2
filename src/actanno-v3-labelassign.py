#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

from tkinter import Tk

from minimal_ctypes_opencv import *
# from minimal_ctypes_opencv import *
from config import cfg
from config import cfg_from_file
import supporting_files.labelassign.frame_manager as frame_mngr
import supporting_files.classname_manager as classn_mngr


# ***************************************************************************
# Global constants
# ***************************************************************************

MAX_object_id = 999
CORNER_DIST_THR = 8
CENTER_DIST_THR = 10
CORNER_SIZE = 30
CENTER_SIZE = 30
JUMP_FRAMES = 25

TITLE = "Actanno V3.0 - Category-based labelling"

# ***************************************************************************
# The data structure storing the annotations
# ***************************************************************************

# change the list below to define your own classes
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
			D : delete all rectangles"


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

def onexit():
	# print "qqqq"
	ex.quit(None)


trackingLib = None


def main():
	cur_path = sys.path[0]

	global trackingLib

	config_path = sys.argv[1]
	cfg_file = os.path.join(config_path, 'config.yml')
	# print "Loading config from >%s<" % cfg_file
	cfg_from_file(cfg_file)
	folder_path = sys.argv[2]
	cfg.MAIN_DIR = folder_path

	from os.path import normpath, basename
	cfg.FOLDER_NAME = basename(normpath(folder_path))
	cfg.MAIN_DIR = folder_path
	# print "Configuration :"
	# print cfg
	classnames_obj = classn_mngr.ClassNames(cfg.CLASSES)

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
		print("Failed to load JM tracking library.")
	# print trackingLib

	root = Tk()
	root.protocol("WM_DELETE_WINDOW", onexit)
	global ex
	ex = frame_mngr.FrameManager(root, cur_path, trackingLib, classnames_obj)
	root.mainloop()


if __name__ == '__main__':
	main()

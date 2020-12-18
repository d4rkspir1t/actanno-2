#!/usr/bin/env python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys

from tkinter import Tk

# from minimal_ctypes_opencv import *
import os
from config import cfg
from config import cfg_from_file
import supporting_files.labelonlyassign.frame_manager as frame_mngr
import supporting_files.classname_manager as classn_mngr


def onexit():
	ex.quit(None)


def main():
	cur_path = sys.path[0]
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

	root = Tk()
	root.protocol("WM_DELETE_WINDOW", onexit)
	global ex
	ex = frame_mngr.FrameManager(root, cur_path, classnames_obj)
	root.mainloop()


if __name__ == '__main__':
	main()

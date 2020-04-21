import sys
import glob
import numpy as np
import copy
import os
import matplotlib.image as mpimg
import xml.etree.ElementTree as xml

from PIL import Image

from tkinter import messagebox

from minimal_ctypes_opencv import *
from config import cfg
import supporting_files.rectangle_manager as rect_mngr
import supporting_files.aa_frame as aaf

MAX_object_id = 999
CORNER_DIST_THR = 8
CENTER_DIST_THR = 10
CORNER_SIZE = 30
CENTER_SIZE = 30
JUMP_FRAMES = 25

TITLE = "Actanno V3.0"

trackingLib = None


# Return an attribute value. Check for its existence
def get_att(node, attname):
	rv = node.get(attname)
	if rv is None:
		messagebox.showinfo(TITLE, "attribute " + attname + " not found in tag " + node.tag)
		sys.exit(1)
	return rv


def mkdir_p(path):
	import errno
	try:
		os.makedirs(path)
	except OSError as exc:  # Python >2.5
		if exc.errno == errno.EEXIST and os.path.isdir(path):
			pass
		else:
			raise


class AAController:
	def __init__(self, t_lib, classnames):
		# yet unassigned inits
		self.classnames_obj = classnames
		global trackingLib
		trackingLib = t_lib
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
			sys.stderr.write("Did not find any rgb frames! Is the prefix correct? Prefix: ", prefix)
			self.usage()
		for i in range(len(self.filenames)):
			self.frames.append(aaf.AAFrame())

		# if depth
		if cfg.D_PREFIX != "default":
			print("USING RGB AND DEPTH")
			self.depth_available = True
			prefix_depth = cfg.MAIN_DIR + cfg.D_PREFIX
			self.filenames_depth = sorted(glob.glob(prefix_depth + "*"))
			if len(self.filenames_depth) < 1:
				sys.stderr.write("Did not find any depths frames! Is the prefix correct?")
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
				messagebox.showinfo(TITLE, "XML File " + self.output_filename + " does not exist. Creating a new one.")

	@staticmethod
	def usage():
		sys.stderr.write('Usage:\n%s, %s' % (sys.argv[0], " <output-xml-filename> <framefileprefix RGB> <framefileprefix depth>"))
		sys.exit(1)

	# Check the current annotation for validity
	def check_validity(self):
		msg = ''
		# Check for several occurrences of a object_id in the same frame.
		for (frnr, fr) in enumerate(self.frames):
			msg = msg + self.check_validity_frame(frnr)

		# Check for unassigned ClassAssignations (no known object class)
		msg2 = ''
		for (i, x) in enumerate(self.class_assignations):
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
			# print(40*"-")
			# print "format :",png.format
			# print "size :", png.size
			# print "mode :", png.mode
			# png.load()
			# data = list(png.getdata())
			# print "max(data)", max(data),"min(data)", min(data)
			self.cur_image = png.convert('RGB')
		elif ext == ".jpg":
			self.cur_image = Image.open(self.filenames[self.cur_frame_nr])
		else:
			print("def curFrame(self): Extension not supported but trying anyway. [", ext, "]")
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

	# Remove the rectangle with the given index from the list
	# of rectangles of the currently selected frame
	def delete_rect(self, index):
		# print 'To delete: ', index
		del self.frames[self.cur_frame_nr].rects[index]

	def next_frame(self, do_propagate, force):
		if self.cur_frame_nr < len(self.filenames) - 1:
			self.cur_frame_nr += 1
		# if the next frame does NOT contain any rectangles,
		# propagate the previous ones
		if do_propagate:
			x = len(self.frames[self.cur_frame_nr].rects)

			print("we have", x, "frames")
			if x > 0 and not force:
				print("No propagation, target frame is not empty")
			else:
				self.frames[self.cur_frame_nr].rects = []
				y = len(self.frames[self.cur_frame_nr - 1].rects)
				if y > 0:
					# Tracking code goes here .....
					print("Propagating ", y, "rectangle(s) to next frame")

					if trackingLib is None:
						# simple copy
						print("simple copy")
						self.cur_frame()
						self.frames[self.cur_frame_nr].rects = copy.deepcopy(self.frames[self.cur_frame_nr - 1].rects)
					else:
						# JM tracking
						print("use JM tracking")
						self.old_frame = self.cur_image
						self.cur_frame()

						for inrect in self.frames[self.cur_frame_nr - 1].rects:
							# convert PIL image to OpenCV image
							cv_old_img = cvCreateImageFromPilImage(self.old_frame)
							cv_cur_img = cvCreateImageFromPilImage(self.cur_image)
							# No need to invoke cvRelease...()

							# convert Python types to C types
							c_inrect = rect_mngr.to_c_aa_rect(inrect)
							c_outrect = rect_mngr.CAARect()

							# call C++ tracking lib
							trackingLib.track_block_matching(ctypes.byref(cv_old_img), ctypes.byref(cv_cur_img),ctypes.byref(c_inrect), ctypes.byref(c_outrect))

							# convert C types to Python types
							outrect = rect_mngr.to_aa_rect(c_outrect)
							self.frames[self.cur_frame_nr].rects.append(outrect)

				else:
					print("No frames to propagate")
		else:
			self.cur_frame()
		self.export_xml_filename("save.xml")
		return self.cur_image

	def next_frame_prop_current_rect(self, rect_index):
		propagate_id = self.frames[self.cur_frame_nr].rects[rect_index].object_id
		# print "Rect[", rect_index, "].object_id == ", propagate_id

		if self.cur_frame_nr < len(self.filenames) - 1:
			self.cur_frame_nr += 1
			# print "Propagating rectangle", propagate_id, " to new frame"
			x = len(self.frames[self.cur_frame_nr].rects)
			y = len(self.frames[self.cur_frame_nr - 1].rects)
			# print "we have ", x, " objects"
			# print "we had  ", y, " objects"

			# get old rect to propagate
			rect_to_propagate = self.frames[self.cur_frame_nr - 1].rects[rect_index]

			# get his new position by tracking
			if trackingLib is None:
				# simple copy
				print("simple copy")
				self.cur_frame()
				rect_propagated = copy.deepcopy(rect_to_propagate)
			else:
				# JM tracking
				print("use JM tracking")
				self.old_frame = self.cur_image
				self.cur_frame()

				# convert PIL image to OpenCV image
				cv_old_img = cvCreateImageFromPilImage(self.old_frame)
				cv_cur_img = cvCreateImageFromPilImage(self.cur_image)
				# No need to invoke cvRelease...()

				# convert Python types to C types
				c_inrect = rect_mngr.to_c_aa_rect(rect_to_propagate)
				c_outrect = rect_mngr.CAARect()

				# call C++ tracking lib
				trackingLib.track_block_matching(ctypes.byref(cv_old_img), ctypes.byref(cv_cur_img),
												 ctypes.byref(c_inrect), ctypes.byref(c_outrect))

				# convert C types to Python types
				rect_propagated = rect_mngr.to_aa_rect(c_outrect)
			# self.frames[self.curFrameNr].rects.append(outrect)

			rect_propagated.object_id = propagate_id

			# update it or add it
			rect_already_exists = False
			for i, currentrect in enumerate(self.frames[self.cur_frame_nr].rects):
				if currentrect.object_id == propagate_id:
					print("Rectangle found. Updating.")
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

	def add_rect(self, x1, y1, x2, y2, object_id, fnr=-1):
		if fnr == -1:
			fnr = self.cur_frame_nr
		if fnr >= len(self.frames):
			raise Exception()
		self.frames[fnr].get_rects().append(rect_mngr.AARect(x1, y1, x2, y2, object_id))

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
		neededcap = new_id - len(self.class_assignations)
		if neededcap > 0:
			for i in range(neededcap):
				self.class_assignations.append(-1)
		# print "new run id array", self.class_assignations

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
			messagebox.showinfo(TITLE, "Could not save to the specified XML file. Please check the location. "
										 "Does the directory exist?")
		fd.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
		fd.write("<tagset>")
		fd.write("  <video>")
		fd.write("	<videoName>" + self.video_name + "</videoName>")

		# self.filenames[self.curFrameNr]
		# Travers all different running id's
		for cur_object_id in range(maxid):
			found_rects = False
			for (i, f) in enumerate(self.frames):
				for (j, r) in enumerate(f.get_rects()):
					if r.object_id == cur_object_id + 1:
						if not found_rects:
							found_rects = True
							fd.write("	<object nr=\"" + str(cur_object_id + 1) + "\" class=\"" + str(
								self.class_assignations[cur_object_id]) + "\">\n")
						framenr = int(self.filenames[i].split('bbox')[-1].split('.')[0])
						s = "	  <bbox x=\"" + str(int(r.x1)) + "\" y=\"" + str(int(r.y1))
						s = s + "\" width=\"" + str(int(r.x2 - r.x1 + 1)) + "\" height=\"" + str(int(r.y2 - r.y1 + 1))
						s = s + "\" framenr=\"" + str(framenr + 1)
						s = s + "\" framefile=\"" + self.filenames[i] + "\"/>\n"
						fd.write(s)
			if found_rects:
				fd.write("	</object>")
		fd.write("  </video>")
		fd.write("</tagset>")
		fd.close()

	def export_xml2voc(self):
		print("Exporting...")
		mkdir_p(self.voc_path)
		for (i, f) in enumerate(self.frames):
			head, tail = os.path.split(self.filenames[i])
			filename = self.voc_path + tail[:-3] + "xml"
			fd = None
			try:
				fd = open(filename, 'w')
			except IOError:
				messagebox.showinfo(TITLE, "Could not save to the specified XML file. Please check the location. "
											 "Does the directory exist?")

			fd.write("<annotation>")
			fd.write("	<folder>" + self.folder_name + "</folder>")
			fd.write("	<filename>" + tail + "</filename>")
			fd.write("	<source>")
			fd.write("		<database>The " + self.dataset_name + " database</database>")
			fd.write("	</source>")
			fd.write("	<owner>" + self.owner + "</owner>")
			fd.write("	<size>")
			fd.write("		<width>640</width>")
			fd.write("		<height>480</height>")
			fd.write("		<depth>1</depth>")
			fd.write("	</size>")
			fd.write("	<segmented>0</segmented>")

			for (j, r) in enumerate(f.get_rects()):
				fd.write("	<object>")
				fd.write("		<name>" + self.classnames_obj.name_list[self.class_assignations[r.object_id - 1]] + "</name>")
				fd.write("		<pose>unknown</pose>")
				fd.write("		<truncated>-1</truncated>")
				fd.write("		<difficult>0</difficult>")
				fd.write("		<bndbox>")
				fd.write("			<xmin>" + str(int(r.x1)) + "</xmin>")
				fd.write("			<ymin>" + str(int(r.y1)) + "</ymin>")
				fd.write("			<xmax>" + str(int(r.x2)) + "</xmax>")
				fd.write("			<ymax>" + str(int(r.y2)) + "</ymax>")
				fd.write("		</bndbox>")
				fd.write("	</object>")

			fd.write("</annotation>")
			fd.close()
		print("Done !")

	def parse_xml(self):
		tree = xml.parse(self.output_filename)
		# root_element = tree.getroot()

		# Get the single video tag
		vids = tree.findall("video")
		if len(vids) < 1:
			messagebox.showinfo(TITLE, "No <video> tag found in the input XML file!")
			sys.exit(1)
		if len(vids) > 1:
			messagebox.showinfo(TITLE, "Currently only a single <video> tag is supported per XML file!")
			sys.exit(1)
		vid = vids[0]

		# Get the video name
		# x=getSingleTag(vid,"videoName")
		# if (x.text is None) or (len(x.text)==0) or (x.text=="NO-NAME"):
		#	tkMessageBox.showinfo(TITLE, "The video name in the given XML file is empty. Please provide the correct name before saving the file.")
		#	self.videoname="NO-NAME"
		# else:
		#	self.videoname=x.text

		# Get all the objects
		objectnodes = vid.findall("object")
		if len(objectnodes) < 1:
			messagebox.showinfo(TITLE, "The given XML file does not contain any objects.")
		for a in objectnodes:
			# Add the classnr to the object_id array. Grow if necessary
			anr = int(get_att(a, "nr"))
			aclass = int(get_att(a, "class"))
			# print "-----",anr,aclass
			# print len(self.ClassAssignations)
			if len(self.class_assignations) < anr:
				# print "Growing object_id:"
				self.class_assignations += [None] * (anr - len(self.class_assignations))
			self.class_assignations[anr - 1] = aclass
			# print "size of object_id array:", len(self.ClassAssignations), "array:", self.ClassAssignations

			# Get all the bounding boxes for this object
			bbs = a.findall("bbox")
			if len(bbs) < 1:
				messagebox.showinfo(TITLE, "No <bbox> tags found for an object in the input XML file!")
				sys.exit(1)
			for bb in bbs:

				# Add the bounding box to the frames() list
				bfnr = int(get_att(bb, "framenr"))
				bx = int(get_att(bb, "x"))
				by = int(get_att(bb, "y"))
				bw = int(get_att(bb, "width"))
				bh = int(get_att(bb, "height"))
				try:
					self.add_rect(bx, by, bx + bw - 1, by + bh - 1, anr, bfnr - 1)
				except IndexError:
					print("*** ERROR ***")
					print("The XML file contains rectangles in frame numbers which are outside of the video")
					print("(frame number too large). Please check whether the XML file really fits to these")
					print("frames.")
					sys.exit(1)
import os
import pyscreenshot as ImageGrab

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageTk

from tkinter import Tk, Canvas, Frame, BOTH, Listbox, Toplevel, Message, Button, Entry, Scrollbar, Scale, IntVar, StringVar
from tkinter import N, S, W, E, NW, SW, NE, SE, CENTER, END, LEFT, RIGHT, X, Y, TOP, BOTTOM, HORIZONTAL, DISABLED
from tkinter import messagebox, simpledialog

from config import cfg
import supporting_files.labelassign.aa_controller as aac
import supporting_files.semantic_mouse_position_manager as smp_mngr


MAX_object_id = 999
CORNER_DIST_THR = 8
CENTER_DIST_THR = 10
CORNER_SIZE = 30
CENTER_SIZE = 30
JUMP_FRAMES = 25

TITLE = "Actanno V3.0 - Category-based labelling"

trackingLib = None


class FrameManager(Frame):
	def __init__(self, parent, cur_path, t_lib, classnames):
		global trackingLib
		trackingLib = t_lib
		self.classnames_obj = classnames
		Frame.__init__(self, parent)
		self.parent = parent
		self.cur_path = cur_path
		self.ct = aac.AAController(trackingLib, self.classnames_obj)
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

		self.aid_img = self.ct.set_aid()
		self.aid_img = self.aid_img.resize((340, 808), Image.ANTIALIAS)
		self.aid_frame = ImageTk.PhotoImage(self.aid_img)

		self.img_trash = ImageTk.PhotoImage(Image.open(self.cur_path + "/trashcan.png"))
		self.img_move = ImageTk.PhotoImage(Image.open(self.cur_path + "/move.png"))
		# create canvas
		self.canvas = Canvas(self.parent, width=self.img.size[0], height=self.img.size[1])
		self.aid_canvas = Canvas(self.parent, width=self.aid_img.size[0], height=self.aid_img.size[1])
		# create scale bar
		self.scalevar = IntVar()
		self.xscale = Scale(self.parent, variable=self.scalevar, from_=1, to=len(self.ct.filenames),
							orient=HORIZONTAL, command=self.change_frame)

		self.canvas.create_image(0, 0, anchor=NW, image=self.cur_frame)
		self.aid_canvas.create_image(0,0, anchor=NW, image=self.aid_frame)

		self.object_id_box = Listbox(self.parent)
		self.id_text_var = StringVar()
		self.id_text_var.set("Next id: 0")
		self.id_setter = Button(self.parent, textvariable=self.id_text_var, state=DISABLED)
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
		self.aid_canvas.grid(row=0, column=2, rowspan=6)

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
		self.object_id_box.bind("<Key-space>", self.next_frame_w_rop)  # the space key
		self.canvas.bind("<Key-space>", self.next_frame_w_rop)  # the space key
		self.object_id_box.bind("<<ListboxSelect>>", self.object_id_box_click)
		self.switch_button.bind("<Button-1>", self.activate_switch)
		self.save_button.bind("<Button-1>", self.save_xml)
		self.export_2voc.bind("<Button-1>", self.save_xml2voc)
		self.quit_button.bind("<Button-1>", self.quit)

		# Variable inits
		self.state = ""
		self.mousex = 1
		self.mousey = 1
		self.object_id_proposed_for_new_rect = len(self.ct.class_assignations) + 1
		self.id_text_var.set("Next id: %d" % (int(self.object_id_proposed_for_new_rect)))
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
		if len(msg) > 0:
			messagebox.showinfo(TITLE, "There are errors in the annotation:\n\n" + msg +
								  "\nThe file has been saved. Please address the problem(s) and save again.")

	def quit(self, event):
		# print "quit method"
		self.ct.videoname = self.fn_entry.get()
		ok = True

		if self.is_modified:
			if messagebox.askyesno(title='Unsaved changes', message='The annotation has been modified. '
																	  'Do you really want to quit?'):
				pass
			else:
				ok = False
		if ok:
			# close tracking library
			if trackingLib != None:
				trackingLib.close_lib()
			self.parent.destroy()

	def save_images_with_bbox(self):
		grabcanvas = ImageGrab.grab(bbox=self.get_canvas_box())
		# grabcanvas.show()
		frame_name = str(self.ct.filenames[self.ct.cur_frame_nr].split('/')[-1])
		path = os.path.join(cfg.BBOX_PREFIX, frame_name)
		grabcanvas.save(path)

	def update_after_jump(self):
		# if cfg.BBOX_PREFIX != 'default':
		# 	self.save_images_with_bbox()
		self.cur_frame = ImageTk.PhotoImage(self.img)
		self.display_anno()
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
		self.check_validity()
		self.ct.export_xml()
		self.is_modified = False
		messagebox.showinfo("Save", "File saved successfully!")

	def save_xml2voc(self, event):
		if cfg.BBOX_PREFIX != 'default':
			self.save_images_with_bbox()
		self.ct.videoname = self.fn_entry.get()
		self.check_validity()
		self.ct.export_xml()
		self.is_modified = False
		self.ct.export_xml2voc()
		messagebox.showinfo("Save", "VOC File saved successfully!")

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
		print('down idx', sempos.index)
		self.cur_sem_pos = smp_mngr.SemMousePos(-1, "g")

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
					self.ct.add_rect(self.curx1, self.cury1, self.curx2, self.cury2, self.cur_object_id)
					if cfg.BBOX_PREFIX != 'default':
						self.save_images_with_bbox()
					self.is_modified = True
					# We just drew a new rectangle
					if self.state == "d":
						self.ct.use_object_id(self.cur_object_id)
						self.display_class_assignations()
						self.object_id_proposed_for_new_rect = self.object_id_proposed_for_new_rect + 1
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

	# def chose_object_id(self, event, idx):
	# 	sempos = self.ct.get_sem_mouse_pos(self.mousex, self.mousey)
	# 	print "choseobject_id(self,event,id):", sempos.index, "pos: ", self.mousex, ",", self.mousey
	# 	if sempos.index > - 1:
	# 		self.ct.update_object_id(sempos.index, idx)
	# 		self.display_anno()
	# 		self.display_class_assignations()
	# 		self.is_modified = True

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
				curcol = "green"
			else:
				curcol = "green"
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
		x = self.ct.class_assignations
		for i in range(len(x)):
			if x[i] is None:
				continue
			if x[i] < 0:
				self.object_id_box.insert(END, str(i + 1) + " has no assigned class ")
			else:
				self.object_id_box.insert(END, str(i + 1) + " has class " + str(x[i]) + " [" + self.classnames_obj.name_list[x[i]] + "]")

	# a listbox item has been clicked: choose the object class for
	# a given object
	def object_id_box_click(self, event):
		self.clicked_object_id = self.object_id_box.curselection()
		top = self.class_dlg = Toplevel()
		length_of_dialog_box = 30 * len(self.classnames_obj.name_list)
		top.geometry("400x" + str(length_of_dialog_box) + "+" + str(self.winfo_rootx()) + "+" + str(self.winfo_rooty()))
		top.title("Enter class label for chosen object")
		class_id = 0
		for classname in self.classnames_obj.name_list:
			button_text = str(class_id) + " " + classname
			button = Button(top, text=button_text, command=lambda i=class_id: self.chose_class_nr(i))
			button.pack(fill=X)
			class_id += 1

	def chose_class_nr(self, class_nr):
		object_id = int(self.clicked_object_id[0])
		self.ct.class_assignations[object_id] = class_nr
		self.class_dlg.destroy()
		self.display_class_assignations()
		# Put the focus on the canvas, else the listbox gets all events
		self.canvas.focus_force()
		self.is_modified = True

	def debug_event(self, title):
		self.event_counter += 1
		# print 'event #' + str(self.event_counter), title

	def set_next_id(self, event):
		given_id = simpledialog.askinteger('Set Next ID',
											 'Enter the id for the next bounding box you draw')
		self.object_id_proposed_for_new_rect = given_id
		self.id_text_var.set("Next id %d" % self.object_id_proposed_for_new_rect)

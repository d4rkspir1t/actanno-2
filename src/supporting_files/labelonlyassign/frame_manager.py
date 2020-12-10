import os

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageTk

from tkinter import Canvas, Frame, BOTH, Listbox, Toplevel, Button, Entry, Scale, IntVar
from tkinter import N, S, W, E, NW, END, X, HORIZONTAL, DISABLED
from tkinter import messagebox

import supporting_files.labelonlyassign.aa_controller as aac


MAX_object_id = 999
CORNER_DIST_THR = 8
CENTER_DIST_THR = 10
CORNER_SIZE = 30
CENTER_SIZE = 30
JUMP_FRAMES = 25

TITLE = "Actanno V3.0 - F-formation labelling"

trackingLib = None


class FrameManager(Frame):
	def __init__(self, parent, cur_path, classnames):
		self.classnames_obj = classnames
		Frame.__init__(self, parent)
		self.parent = parent
		self.cur_path = cur_path
		self.ct = aac.AAController(self.classnames_obj)
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

		# create canvas
		self.canvas = Canvas(self.parent, width=self.img.size[0], height=self.img.size[1])
		self.aid_canvas = Canvas(self.parent, width=self.aid_img.size[0], height=self.aid_img.size[1])
		# create scale bar
		self.scalevar = IntVar()
		self.xscale = Scale(self.parent, variable=self.scalevar, from_=1, to=len(self.ct.filenames),
							orient=HORIZONTAL, command=self.change_frame)

		self.canvas.create_image(0, 0, anchor=NW, image=self.cur_frame)
		self.aid_canvas.create_image(0,0, anchor=NW, image=self.aid_frame)

		self.object_id_box = Listbox(self.parent, width=40)
		self.save_button = Button(self.parent, text="SAVE")
		self.quit_button = Button(self.parent, text="QUIT")
		self.fn_entry = Entry(self.parent, state=DISABLED)
		self.grid(sticky=W + E + N + S)

		# position
		self.canvas.grid(row=0, column=0, rowspan=6)
		self.object_id_box.grid(row=0, column=1, rowspan=3, sticky=N + S)
		self.save_button.grid(row=3, column=1)
		self.quit_button.grid(row=4, column=1)
		self.xscale.grid(row=6, sticky=W + E, columnspan=3)
		self.aid_canvas.grid(row=0, column=2, rowspan=6)

		# bindings
		self.canvas.bind("<Key-Left>", self.prev_frame)
		self.canvas.bind("<Key-BackSpace>", self.prev_frame)
		self.canvas.bind("<Key-Right>", self.next_frame)
		self.canvas.bind("<Next>", self.next_frame_far)
		self.canvas.bind("<Prior>", self.prev_frame_far)  # the space key
		self.canvas.bind("<Motion>", self.mouse_move)
		self.canvas.bind("q", self.quit)
		self.canvas.bind("s", self.save_xml)
		self.object_id_box.bind("<Key-space>", self.next_frame)  # the space key
		self.canvas.bind("<Key-space>", self.next_frame)  # the space key
		self.object_id_box.bind("<<ListboxSelect>>", self.object_id_box_click)
		self.save_button.bind("<Button-1>", self.save_xml)
		self.quit_button.bind("<Button-1>", self.quit)

		# Variable inits
		self.state = ""
		self.mousex = 1
		self.mousey = 1
		self.object_id_proposed_for_new_rect = list(self.ct.class_assignations.keys())[-1] + 1
		self.display_anno()
		self.display_class_assignations()
		self.fn_entry.delete(0, END)
		self.fn_entry.insert(0, self.ct.video_name)
		self.is_modified = False
		self.canvas.focus_force()

	def get_canvas_box(self):
		x = self.canvas.winfo_rootx() + self.canvas.winfo_x()
		y = self.canvas.winfo_rooty()
		x1 = x + self.canvas.winfo_width()
		y1 = y + self.canvas.winfo_height()
		box = (x, y, x1, y1)
		# print box
		return box

	def check_validity(self):
		msg = self.ct.check_validity()
		# if len(self.fn_entry.get()) < 1:
		# 	msg = msg + "The video name is empty.\n"
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
			self.parent.destroy()

	def update_after_jump(self):
		self.cur_frame = ImageTk.PhotoImage(self.img)
		self.display_anno()
		self.parent.title(
			TITLE + " (frame nr." + str(self.ct.cur_frame_nr + 1) + " of " + str(len(self.ct.filenames)) + ")")
		self.canvas.update()

	def change_frame(self, id_frame):
		self.img = self.ct.change_frame(id_frame)
		self.update_after_jump()

	def prev_frame(self, event):
		self.img = self.ct.prev_frame()
		self.update_after_jump()

	def prev_frame_far(self, event):
		self.img = self.ct.prev_frame_far()
		self.update_after_jump()

	def next_frame(self, event):
		self.img = self.ct.next_frame(False, False)
		self.update_after_jump()

	def next_frame_far(self, event):
		self.img = self.ct.next_frame_far()
		self.update_after_jump()

	def mouse_move(self, event):
		self.display_anno()
		self.mousex = event.x
		self.mousey = event.y
		maxx = self.img.size[0]
		maxy = self.img.size[1]
		self.canvas.focus_force()

	def save_xml(self, event):
		self.ct.videoname = self.fn_entry.get()
		self.check_validity()
		self.ct.export_xml()
		self.is_modified = False
		messagebox.showinfo("Save", "File saved successfully!")

	# Draw the image and the current annotation
	def display_anno(self):
		# Init drawing
		draw_frame = self.img.copy()
		self.draw_photo = ImageTk.PhotoImage(draw_frame)
		self.canvas.create_image(0, 0, anchor=NW, image=self.draw_photo)

	def display_class_assignations(self):
		self.object_id_box.delete(0, END)
		x = self.ct.class_assignations
		# print(self.ct.class_assignations)
		for key, val in x.items():
			if val is None:
				continue
			if val < 0:
				self.object_id_box.insert(END, str(key) + " has no assigned class ")
			else:
				self.object_id_box.insert(END, str(key) + " has class " + str(val) + " [" + self.classnames_obj.name_list[val] + "]")

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
		object_text = self.object_id_box.get(self.clicked_object_id)
		group_id = object_text.split(' ')[0]
		print(group_id, class_nr)
		self.ct.class_assignations[int(group_id)] = class_nr

		self.class_dlg.destroy()
		self.display_class_assignations()
		# Put the focus on the canvas, else the listbox gets all events
		self.canvas.focus_force()
		self.is_modified = True

	def debug_event(self, title):
		self.event_counter += 1
		# print 'event #' + str(self.event_counter), title

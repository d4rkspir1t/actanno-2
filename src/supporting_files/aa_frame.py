import supporting_files.semantic_mouse_position_manager as smp_mngr


MAX_object_id = 999
CORNER_DIST_THR = 8
CENTER_DIST_THR = 10
CORNER_SIZE = 30
CENTER_SIZE = 30
JUMP_FRAMES = 25


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
			return smp_mngr.SemMousePos(arg_idx, arg_sem)

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
			return smp_mngr.SemMousePos(-1, "n")

		if min_val < CENTER_DIST_THR * CENTER_DIST_THR:
			return smp_mngr.SemMousePos(arg_idx, "c")
		else:
			return smp_mngr.SemMousePos(arg_idx, "g")
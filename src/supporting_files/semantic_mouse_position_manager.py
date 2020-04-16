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

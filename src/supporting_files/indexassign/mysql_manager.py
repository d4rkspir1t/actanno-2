import mysql.connector as mysql


class MySqlManager:
    def __init__(self):
        self.db = mysql.connect(host="localhost",
                                user="admin",
                                passwd="password",
                                database="class_assignments")
        self.cursor = self.db.cursor(buffered=True)
        self.table_reset()

    def table_reset(self):
        try:
            self.cursor.execute("DROP TABLE hum_to_group;")
        except:
            pass
        self.cursor.execute(
            "CREATE TABLE hum_to_group (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, "
            "frame_no INT(11), human_id INT(11), label INT(11), tmp_obj_id INT(11));")
        self.cursor.execute("DESC hum_to_group;")
        print(self.cursor.fetchall())

    def drop_table(self):
        try:
            self.cursor.execute("DROP TABLE hum_to_group;")
        except:
            pass

    def select_ca_frame_info(self, fr_no):
        query = "SELECT human_id, label FROM hum_to_group WHERE frame_no = %s;" % fr_no
        self.cursor.execute(query)
        frame_info = self.cursor.fetchall()
        # for info in frame_info:
        #     print 'ln 358 (select frame info: ', info
        return frame_info

    def del_ca_frame_info(self, fr_no):
        query = "SELECT COUNT(*) FROM hum_to_group;"
        self.cursor.execute(query)
        frame_info = self.cursor.fetchall()
        # print 'ln 437 del frame all: ', frame_info

        query = "DELETE FROM hum_to_group WHERE frame_no = %s;" % fr_no
        self.cursor.execute(query)
        self.db.commit()

        query = "SELECT COUNT(*) FROM hum_to_group;"
        self.cursor.execute(query)
        frame_info = self.cursor.fetchall()
        # print 'ln 437 del frame all: ', frame_info

    def del_ca_frame_single(self, fr_no, index):
        query = "SELECT COUNT(*) FROM hum_to_group WHERE frame_no = %s;" % fr_no
        self.cursor.execute(query)
        frame_info = self.cursor.fetchall()
        # print 'ln 459 del frame single: ', frame_info

        query = "DELETE FROM hum_to_group WHERE frame_no = %s AND human_id = %s;" % (fr_no, index)
        self.cursor.execute(query)
        self.db.commit()

        query = "SELECT COUNT(*) FROM hum_to_group WHERE frame_no = %s;" % fr_no
        self.cursor.execute(query)
        frame_info = self.cursor.fetchall()
        # print 'ln 459 del frame single: ', frame_info

    def insert_ca_frame_all(self, fr_info_array):
        query = "INSERT INTO hum_to_group (frame_no, human_id, label) VALUES (%s, %s, %s);"
        self.cursor.executemany(query, fr_info_array)
        self.db.commit()
        # print 'ln 483 insert frame all: ', cursor.rowcount, "records inserted"

    def select_ca_frame_single(self, fr_no, obj_id):
        query = "SELECT human_id, label FROM hum_to_group WHERE frame_no = %s AND human_id = %s;" % (fr_no, obj_id)
        self.cursor.execute(query)
        frame_info = self.cursor.fetchone()
        # for info in frame_info:
        #     print 'ln 548 select frame single: ', info
        # print 'ln 548: ', frame_info
        return frame_info

    def update_ca_frame_single(self, fr_no, obj_id, label):
        query = "UPDATE hum_to_group SET label = %s WHERE frame_no = %s AND human_id = %s;" % (label, fr_no, obj_id)
        self.cursor.execute(query)
        self.db.commit()
        # print 'ln 557 update frame single'

    def insert_ca_frame_label(self, fr_no, obj_id, label):
        fr_info_single = (fr_no, obj_id, label)
        query = "INSERT INTO hum_to_group (frame_no, human_id, label) VALUES (%s, %s, %s);"
        self.cursor.execute(query, fr_info_single)
        self.db.commit()
        print('ln 563 insert frame single: ', self.cursor.rowcount, "record inserted %s %s %s" % (fr_info_single))

    def count_ca_frame_objects(self, fr_no):
        query = "SELECT COUNT(*) FROM hum_to_group WHERE frame_no = %s;" % fr_no
        self.cursor.execute(query)
        frame_info = self.cursor.fetchone()[0]
        # print 'ln 692 count frame objects: ', frame_info
        return frame_info

    def select_ca_frame_numbers(self):
        query = "SELECT frame_no FROM hum_to_group GROUP BY frame_no;"
        self.cursor.execute(query)
        frame_info = self.cursor.fetchall()
        # print 'ln 708 count frame objects: ', frame_info
        return frame_info

    def count_ca_frames(self):
        query = "SELECT COUNT(*) FROM hum_to_group GROUP BY frame_no;"
        self.cursor.execute(query)
        frame_info = self.cursor.fetchall()
        # print 'ln 811 count all frames: ', frame_info
        return len(frame_info)

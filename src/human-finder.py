import os
import numpy as np
import cv2
import imutils
from centroidtracker import CentroidTracker
# from pprint import pprint

folder = '../kcltestimages/bbox_saves'
tracked_bbox_output = os.path.join(folder, 'human_bbox.xml')
ext = 'png'
prototxt = '../rtod_helper/MobileNetSSD_deploy.prototxt.txt'
model = '../rtod_helper/MobileNetSSD_deploy.caffemodel'
conf = 0.2
net = cv2.dnn.readNetFromCaffe(prototxt, model)
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
               "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
               "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
               "sofa", "train", "tvmonitor"]
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))
ct = CentroidTracker()


def write_xml(frames, max_id):
    fd = None
    try:
        fd = open(tracked_bbox_output, 'w')
    except IOError:
        print 'IOERROR, output xml cannot be opened'
    print >> fd, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    print >> fd, "<tagset>"
    print >> fd, "  <video>"
    print >> fd, "	<videoName>" + 'Human_Detected_GroupAnnotated_Dataset' + "</videoName>"
    for cur_object_id in range(max_id+1):
        found_rects = False
        for idx, frame in enumerate(frames):
            for obj_id, rect in frame['rects'].items():
                if obj_id == cur_object_id:
                    if not found_rects:
                        found_rects = True
                        fd.write("	<object nr=\"" + str(cur_object_id + 1) + "\">\n")
                    s = "	  <bbox x=\"" + str(int(rect[0])) + "\" y=\"" + str(int(rect[1]))
                    s = s + "\" width=\"" + str(int(rect[2] - rect[0] + 1)) + "\" height=\"" + str(int(rect[3] - rect[1] + 1))
                    s = s + "\" framenr=\"" + str(idx + 1)
                    s = s + "\" framefile=\"" + frame['path']
                    s = s + "\" class=\"" + str(None) + "\"/>\n"
                    fd.write(s)
        if found_rects:
            print >> fd, "	</object>"
    print >> fd, "  </video>"
    print >> fd, "</tagset>"
    fd.close()


def get_files_to_analyse():
    files_to_detect_in = []
    for r, d, files in os.walk(folder, topdown=False):
        for name in sorted(files):
            if name.split('.')[-1] == ext:
                path = os.path.join(folder, name)
                files_to_detect_in.append(path)
                name_no = int(name.split('.')[0].split('bbox')[-1])
                # print str(name_no)
    return files_to_detect_in


def detect_and_track_people(files_to_detect_in):
    frames = []
    max_id = -1
    for image_path in files_to_detect_in:
        save_frame = {'path': image_path,
                      'rects': {}}

        image = cv2.imread(image_path)
        oh, ow = image.shape[:2]
        frame = imutils.resize(image, width=400)
        (h, w) = frame.shape[:2]
        rath = float(oh)/float(h)
        ratw = float(ow)/float(w)
        # print '%.2f, %.2f' % (rath, ratw)
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
        net.setInput(blob)
        detections = net.forward()
        human_count = 0
        rects = []

        for i in np.arange(0, detections.shape[2]):
            # extract the confidence (i.e., probability) associated with
            # the prediction
            confidence = detections[0, 0, i, 2]

            # filter out weak detections by ensuring the `confidence` is
            # greater than the minimum confidence
            if confidence > conf:
                # extract the index of the class label from the
                # `detections`, then compute the (x, y)-coordinates of
                # the bounding box for the object
                idx = int(detections[0, 0, i, 1])
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                label_name = CLASSES[idx]
                if label_name == 'person':
                    rects.append(box.astype("int"))
                    human_count += 1
                #     label = "#{}-{}: {:.2f}%".format(human_count, label_name, confidence * 100)
                # else:
                #     label = "{}: {:.2f}%".format(label_name, confidence * 100)
                    cv2.rectangle(frame, (startX, startY), (endX, endY),
                              COLORS[idx], 2)
                    y = startY - 15 if startY - 15 > 15 else startY + 15
                #     label = ''
                # cv2.putText(frame, label, (startX, y),
                #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)
        objects, obj_rects = ct.update(rects)
        for (objectID, centroid) in objects.items():
            # draw both the ID of the object and the centroid of the
            # object on the output frame
            text = "ID {}".format(objectID)
            cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.circle(frame, (centroid[0], centroid[1]), 4, (0, 255, 0), -1)
        for object_id in objects.keys():
            print object_id, ' - ', obj_rects[object_id]
            if object_id > max_id:
                max_id = object_id
            true_rects = [int(obj_rects[object_id][0] * ratw),
                          int(obj_rects[object_id][1] * rath),
                          int(obj_rects[object_id][2] * ratw),
                          int(obj_rects[object_id][3] * rath)]
            save_frame['rects'][object_id] = true_rects
        print '>' *10
        frames.append(save_frame)
        # cv2.imshow("Frame", frame)
        # cv2.waitKey(0)
    return frames, max_id


if __name__ == '__main__':
    files_to_detect_in = get_files_to_analyse()
    frames, max_id = detect_and_track_people(files_to_detect_in)
    # pprint(frames)
    write_xml(frames, max_id)

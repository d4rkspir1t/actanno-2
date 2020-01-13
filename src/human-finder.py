import os
import numpy as np
import cv2
import imutils

folder = '../kcltestimages/bbox_saves'
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

files_to_detect_in = []
for r, d, files in os.walk(folder, topdown=False):
    for name in sorted(files):
        if name.split('.')[-1] == ext:
            path = os.path.join(folder, name)
            files_to_detect_in.append(path)
            name_no = int(name.split('.')[0].split('bbox')[-1])
            print str(name_no)

for image_path in files_to_detect_in:
    image = cv2.imread(image_path)
    frame = imutils.resize(image, width=400)
    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), 0.007843, (300, 300), 127.5)
    net.setInput(blob)
    detections = net.forward()
    human_count = 0
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
    cv2.imshow("Frame", frame)
    cv2.waitKey(0)

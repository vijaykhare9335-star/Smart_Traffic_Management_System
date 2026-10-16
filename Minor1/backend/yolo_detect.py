import cv2
import os
import numpy as np

# -----------------------------
# PATH SETUP
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WEIGHTS = os.path.join(BASE_DIR, "yolov3-tiny.weights")
CFG = os.path.join(BASE_DIR, "yolov3.tiny.cfg")
NAMES = os.path.join(BASE_DIR, "coco.names")

# -----------------------------
# LOAD YOLOv3
# -----------------------------
net = cv2.dnn.readNet(WEIGHTS, CFG)

with open(NAMES, "r") as f:
    classes = f.read().splitlines()

layer_names = net.getLayerNames()
output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers().flatten()]

vehicle_classes = ["car", "bus", "truck", "motorbike"]

# -----------------------------
# OPEN 4 VIDEOS
# -----------------------------
caps = {
    "North": cv2.VideoCapture("north.mp4"),
    "South": cv2.VideoCapture("south.mp4"),
    "East": cv2.VideoCapture("east.mp4"),
    "West": cv2.VideoCapture("west.mp4"),
}

# -----------------------------
# MAIN LOOP
# -----------------------------
while True:

    for lane, cap in caps.items():

        ret, frame = cap.read()
        if not ret:
            continue

        height, width, _ = frame.shape

        blob = cv2.dnn.blobFromImage(frame, 1/255, (416, 416), swapRB=True)
        net.setInput(blob)
        outputs = net.forward(output_layers)

        boxes = []
        confidences = []
        class_ids = []

        # -----------------------------
        # DETECTION
        # -----------------------------
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]

                if confidence > 0.4 and classes[class_id] in vehicle_classes:

                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)

                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)

                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        # -----------------------------
        # APPLY NON-MAX SUPPRESSION
        # -----------------------------
        indexes = cv2.dnn.NMSBoxes(boxes, confidences, 0.4, 0.4)

        vehicle_count = 0

        if len(indexes) > 0:
            for i in indexes.flatten():
                x, y, w, h = boxes[i]
                label = classes[class_ids[i]]

                vehicle_count += 1

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, label, (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 255, 0),
                            2)

        # -----------------------------
        # TRAFFIC DENSITY + SIGNAL LOGIC
        # -----------------------------
        if vehicle_count <= 5:
            density = "LOW"
            green_time = 10
        elif vehicle_count <= 15:
            density = "MEDIUM"
            green_time = 20
        else:
            density = "HIGH"
            green_time = 30

        # -----------------------------
        # DISPLAY INFO
        # -----------------------------
        cv2.putText(frame, f"{lane} Lane", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 255, 0), 2)

        cv2.putText(frame, f"Vehicles: {vehicle_count}", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 0, 255), 2)

        cv2.putText(frame, f"Density: {density}", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 255, 0), 2)

        cv2.putText(frame, f"Green Time: {green_time}s", (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (255, 0, 255), 2)

        cv2.imshow(lane, frame)

    if cv2.waitKey(1) == 27:
        break

# -----------------------------
# CLEANUP
# -----------------------------
for cap in caps.values():
    cap.release()

cv2.destroyAllWindows()

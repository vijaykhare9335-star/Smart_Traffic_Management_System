import cv2
import os

videos = ['north.mp4', 'south.mp4', 'east.mp4', 'west.mp4']
for video in videos:
    if os.path.exists(video):
        cap = cv2.VideoCapture(video)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f'{video}: OK - Shape: {frame.shape}')
            else:
                print(f'{video}: FAILED - Cannot read frame')
            cap.release()
        else:
            print(f'{video}: FAILED - Cannot open')
    else:
        print(f'{video}: NOT FOUND')
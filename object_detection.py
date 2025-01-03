from flask import Flask, Response, render_template, request, jsonify
import cv2
from ultralytics import YOLO  
import threading
import numpy as np

app = Flask(__name__)

model = YOLO("yolo-Weights/yolo11n.pt")
classes = model.names
webcam_active = False
cap = None
event = threading.Event()
counter = 1
results = []

def error_frame(error):
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(img, str(error), (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    _, img = cv2.imencode('.jpg', img)
    img = img.tobytes()
    return(b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')


def generate_frames():
    global counter, results
    while event.is_set():
        try:
            ret, img= cap.read()
            if not ret:
                yield error_frame('Error: Unable to read camera')
        except Exception as err:
            yield error_frame(err.__str__())
            continue
        try:
            if counter%7==0:
                results.clear()
                results.append(list(model.predict(img, stream=True, verbose=False)))
        except Exception as err:
            yield error_frame(err.__str__())
            continue

        try:
            if results:
                for x in results[0]:
                    for y in x.boxes: 
                        if y.conf > 0.6:
                            x1, y1, x2, y2 = y.xyxy[0]
                            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 2)
                            text_loc = (x1, y1)
                            predicted_class = str(classes[int(y.cls)]).upper()
                            confidence = str(int(y.conf*100))
                            text = f"{predicted_class} [{confidence}%]"
                            cv2.putText(img, text, text_loc, cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        except Exception as err:
            yield error_frame(err.__str__())
            continue
        
        _, img = cv2.imencode('.jpg', img)
        img = img.tobytes()
        counter+=1
        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/toggle_webcam', methods=['POST', 'GET'])
def toggle_webcam():
    global webcam_active, cap
    if request.method == 'POST':
        try:
            data = request.get_json()
            action = data.get('action')
        except Exception as err:
            return jsonify({'status': 'error', 'message': err.__str__()})

        if action == 'start':
            if not webcam_active:
                try:
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        return jsonify({"status": "error", "message": "Unable to access webcam"})
                    cap.set(3, 640)
                    cap.set(4, 480)
                    webcam_active = True
                    event.set()
                    return jsonify({"status": "success", "webcam_active": webcam_active})
                except Exception as err:
                    return jsonify({"status": "error", "message": err.__str__()})    
            
            elif webcam_active:
                return jsonify({"status": "error", "message": 'Webcam already active.'})

        elif action == 'stop':
            if webcam_active:
                try:
                    webcam_active = False
                    event.clear()
                    if cap:
                        cap.release()
                    cv2.destroyAllWindows()
                    return jsonify({"status": "success", "webcam_active": webcam_active})
                except Exception as err:
                    return jsonify({"status": "error", "message": err.__str__()})   
                
            elif not webcam_active:
                return jsonify({"status": "error", "message": "Webcam already stopped"})
        
        else:
            return jsonify({"status": "error", "message": "Invalid action"})

    elif request.method == 'GET':
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame;')


if __name__ == '__main__':
    app.run(debug=True)

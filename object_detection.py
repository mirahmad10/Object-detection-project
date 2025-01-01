from flask import Flask, Response, render_template, request, jsonify
import cv2
from ultralytics import YOLO  
import threading

app = Flask(__name__)

model = YOLO("yolo-Weights/yolo11n.pt")
classes = model.names
webcam_active = False
cap = None
event = threading.Event()

def generate_frames():
    while event.is_set():
        ret, img= cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break
        
        try:
            results = model.predict(img, stream=True, verbose=False)
        except Exception as err:
            return 'Error: Model could not predict'
        
        try:
            for x in results:
                for y in x.boxes: 
                    if y.conf > 0.6:
                        x1, y1, x2, y2 = y.xyxy[0]
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 2)
                        text_loc = [x1, y1]

                        predicted_class = str(classes[int(y.cls)]).upper()
                        confidence = str(int(y.conf*100))
                        text = f"{predicted_class} [{confidence}%]"
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        fontsize = 0.7
                        color = (255, 0, 0)
                        thickness = 2
                        cv2.putText(img, text, text_loc, font, fontsize, color, thickness)
                    else:
                        continue
        except Exception as err:
            return 'Error: Could not draw on image'
        
        _, img = cv2.imencode('.jpg', img)
        img = img.tobytes()
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
            return jsonify({'status': 'error', 'message': err})

        if action == 'start':
            if not webcam_active:
                try:
                    cap = cv2.VideoCapture(0)
                    if not cap.isOpened():
                        return jsonify({"status": "error", "message": "Unable to access webcam"}), 500
                    cap.set(3, 640)
                    cap.set(4, 480)
                    webcam_active = True
                    event.set()
                    return jsonify({"status": "success", "webcam_active": webcam_active})
                except Exception as err:
                    return jsonify({"status": "error", "message": err})    
            elif webcam_active:
                return jsonify({"status": "error", "message": 'Webcam already active.'})

        elif action == 'stop':
            if webcam_active:
                webcam_active = False
                event.clear()
                if cap:
                    cap.release()
                cv2.destroyAllWindows()
                return jsonify({"status": "success", "webcam_active": webcam_active})
            elif not webcam_active:
                return jsonify({"status": "success", "message": "Webcam already stopped"})
        
        else:
            return jsonify({"status": "error", "message": "Invalid action"}), 400

    elif request.method == 'GET':
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame;')


if __name__ == '__main__':
    app.run(debug=True)
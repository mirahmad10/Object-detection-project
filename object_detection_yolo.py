from flask import Flask, Response, render_template, request, jsonify
import cv2
from ultralytics import YOLO  

app = Flask(__name__)

model = YOLO("yolo-Weights/yolo11n.pt")
classes = model.names
webcam_active = False

def generate_frames():
    global webcam_active
    while True:
        if not webcam_active:
            continue

        ret, img= cap.read()
        results = model.predict(img, stream=True, verbose=False)

        if not ret:
            print("Error: Failed to capture frame.")
            break

        for x in results:
            for y in x.boxes: 
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
            
        _, img = cv2.imencode('.jpg', img)
        img = img.tobytes()
        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_webcam', methods=['POST'])
def toggle_webcam():
    global webcam_active, cap
    data = request.get_json()
    action = data.get('action')

    if action == 'start':
        if not webcam_active: 
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return jsonify({"status": "error", "message": "Unable to access webcam"}), 500
            cap.set(3, 640)  
            cap.set(4, 480)  
        webcam_active = True
        return jsonify({"status": "success", "webcam_active": webcam_active})

    elif action == 'stop':
        if webcam_active:
            webcam_active = False
            if cap:
                cap.release() 
            cv2.destroyAllWindows()
        return jsonify({"status": "success", "webcam_active": webcam_active})

    return jsonify({"status": "error", "message": "Invalid action"}), 400

if __name__ == '__main__':
    app.run(debug=True)
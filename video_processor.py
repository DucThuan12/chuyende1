import os

import cv2
from flask import Flask, jsonify, request
from ultralytics import YOLO

from config import KEYPOINTTHRESH, MODELPATH
from helper import coNguoi, layDiem, thayKhau, tinhgoc
from message import CURLMSG, PUSHUPMSG, SQUATMSG

app = Flask(__name__)

print("Dang tai model YOLO...")
model = YOLO(MODELPATH)
print("Tai model thanh cong!")


def _normalize_exercise(exercise_type: str) -> str:
    if exercise_type in {"curl", "curl-left", "curl-right"}:
        return "curl"
    return exercise_type


@app.route("/process_video", methods=["POST"])
def process_video():
    if "video" not in request.files or "exercise" not in request.form:
        return jsonify({"error": "Thieu file video hoac loai bai tap"}), 400

    exercise_type = request.form["exercise"].strip().lower()
    supported_exercises = {"squat", "pushup", "curl", "curl-left", "curl-right"}
    if exercise_type not in supported_exercises:
        return jsonify({"error": f"Bai tap khong duoc ho tro: {exercise_type}"}), 400

    normalized_exercise = _normalize_exercise(exercise_type)
    video_file = request.files["video"]
    video_path = f"temp_{exercise_type}.mp4"
    video_file.save(video_path)

    cap = cv2.VideoCapture(video_path)
    tongsolan = 0
    solandung = 0
    danh_sach_loi = []
    trangthai = "UP" if normalized_exercise in ["squat", "pushup"] else "DOWN"

    repMinKnee = 999
    repMinTorso = 999
    repMinElbow = 999
    repMinBody = 999
    repMaxElbow = 0
    repMaxElbowShift = 0
    startElbow = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, verbose=False)

        if coNguoi(results):
            kp, conf = layDiem(results)

            if normalized_exercise == "squat":
                canthiet = [5, 6, 11, 12, 13, 14, 15, 16]
                if all(thayKhau(conf, j, KEYPOINTTHRESH) for j in canthiet):
                    leftKnee = tinhgoc(kp[11], kp[13], kp[15])
                    rightKnee = tinhgoc(kp[12], kp[14], kp[16])
                    kneeAngle = (leftKnee + rightKnee) / 2.0

                    leftTorso = tinhgoc(kp[5], kp[11], kp[13])
                    rightTorso = tinhgoc(kp[6], kp[12], kp[14])
                    torsoAngle = (leftTorso + rightTorso) / 2.0

                    if trangthai == "UP" and kneeAngle < 100:
                        trangthai = "DOWN"
                        repMinKnee = kneeAngle
                        repMinTorso = torsoAngle
                    elif trangthai == "DOWN":
                        repMinKnee = min(repMinKnee, kneeAngle)
                        repMinTorso = min(repMinTorso, torsoAngle)

                        if kneeAngle > 155:
                            tongsolan += 1
                            trangthai = "UP"
                            errors = []

                            if repMinKnee > 110:
                                errors.append(SQUATMSG["notlow"]["advice"])
                            if repMinTorso < 150:
                                errors.append(SQUATMSG["backlean"]["advice"])

                            if not errors:
                                solandung += 1
                            else:
                                danh_sach_loi.extend(errors)

                            repMinKnee, repMinTorso = 999, 999

            elif normalized_exercise == "pushup":
                canthiet = [5, 7, 9, 11, 15, 6, 8, 10, 12, 16]
                if all(thayKhau(conf, j, KEYPOINTTHRESH) for j in canthiet):
                    leftElbow = tinhgoc(kp[5], kp[7], kp[9])
                    rightElbow = tinhgoc(kp[6], kp[8], kp[10])
                    elbowAngle = (leftElbow + rightElbow) / 2.0

                    leftBody = tinhgoc(kp[5], kp[11], kp[15])
                    rightBody = tinhgoc(kp[6], kp[12], kp[16])
                    bodyAngle = (leftBody + rightBody) / 2.0

                    if trangthai == "UP" and elbowAngle < 95:
                        trangthai = "DOWN"
                        repMinElbow = elbowAngle
                        repMinBody = bodyAngle
                    elif trangthai == "DOWN":
                        repMinElbow = min(repMinElbow, elbowAngle)
                        repMinBody = min(repMinBody, bodyAngle)

                        if elbowAngle > 155:
                            tongsolan += 1
                            trangthai = "UP"
                            errors = []

                            if repMinElbow > 95:
                                errors.append(PUSHUPMSG["notlow"]["advice"])
                            if repMinBody < 155:
                                errors.append(PUSHUPMSG["bodyline"]["advice"])

                            if not errors:
                                solandung += 1
                            else:
                                danh_sach_loi.extend(errors)

                            repMinElbow, repMinBody = 999, 999

            elif normalized_exercise == "curl":
                if exercise_type == "curl-right":
                    shoulderIdx, elbowIdx, wristIdx = 6, 8, 10
                else:
                    shoulderIdx, elbowIdx, wristIdx = 5, 7, 9

                canthiet = [shoulderIdx, elbowIdx, wristIdx]
                if all(thayKhau(conf, j, KEYPOINTTHRESH) for j in canthiet):
                    elbowAngle = tinhgoc(kp[shoulderIdx], kp[elbowIdx], kp[wristIdx])

                    if trangthai == "DOWN" and elbowAngle < 65:
                        trangthai = "UP"
                        repMinElbow = elbowAngle
                        repMaxElbow = elbowAngle
                        startElbow = kp[elbowIdx].copy()
                        repMaxElbowShift = 0
                    elif trangthai == "UP":
                        repMinElbow = min(repMinElbow, elbowAngle)
                        repMaxElbow = max(repMaxElbow, elbowAngle)

                        if startElbow is not None:
                            shift = abs(kp[elbowIdx][0] - startElbow[0]) + abs(kp[elbowIdx][1] - startElbow[1])
                            repMaxElbowShift = max(repMaxElbowShift, shift)

                        if elbowAngle > 145:
                            tongsolan += 1
                            trangthai = "DOWN"
                            errors = []

                            if repMinElbow > 65:
                                errors.append(CURLMSG["notbend"]["advice"])
                            if repMaxElbow < 155:
                                errors.append(CURLMSG["notstraight"]["advice"])
                            if repMaxElbowShift > 45:
                                errors.append(CURLMSG["elbowshift"]["advice"])

                            if not errors:
                                solandung += 1
                            else:
                                danh_sach_loi.extend(errors)

                            repMinElbow, repMaxElbowShift = 999, 0
                            repMaxElbow, startElbow = 0, None

    cap.release()
    if os.path.exists(video_path):
        os.remove(video_path)

    if tongsolan == 0:
        feedback_text = "Ban chua hoan thanh luot tap nao. Hay thu lai va co gang nhe!"
    else:
        ty_le = (solandung / tongsolan) * 100
        loi_str = ""
        if danh_sach_loi:
            cac_loi_duy_nhat = list(set(danh_sach_loi))
            loi_str = " Chu y: " + " ".join(cac_loi_duy_nhat)

        if ty_le == 100:
            feedback_text = "Qua tuyet voi! Ban da tap dung form 100%."
        elif ty_le >= 70:
            feedback_text = f"Rat tot! Ban dat {int(ty_le)}% chuan form.{loi_str}"
        elif ty_le > 0:
            feedback_text = f"Co gang len! Ban dat {int(ty_le)}% chuan form.{loi_str}"
        else:
            feedback_text = f"Chua dat luot chuan form nao. Dung nan chi!{loi_str}"

    return jsonify(
        {
            "status": "success",
            "exercise": exercise_type.upper(),
            "total_reps": tongsolan,
            "correct_reps": solandung,
            "feedback": feedback_text,
        }
    )


if __name__ == "__main__":
    print("Dang chay server AI cham diem video...")
    app.run(host="0.0.0.0", port=5000)

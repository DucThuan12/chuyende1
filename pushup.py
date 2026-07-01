import cv2
from ultralytics import YOLO

from config import MODELPATH, CAMERAINDEX, KEYPOINTTHRESH, WARNINGCOOLDOWN, WARNINGSHOWSEC, ERRORCOOLDOWN, SHOWFPS
from helper import (
    tinhgoc, FPSCounter, WarningManager, ResultManager, vietchu,
    coNguoi, layDiem, thayKhau, save_bad_rep
)
from message import COMMONMSG, PUSHUPMSG


def _chon_ben_tot_nhat(kp, conf, threshold):
    left_ok = all(thayKhau(conf, j, threshold) for j in [5, 7, 9, 11, 15])
    right_ok = all(thayKhau(conf, j, threshold) for j in [6, 8, 10, 12, 16])

    if left_ok and right_ok:
        left_score = sum(conf[j] for j in [5, 7, 9, 11, 15])
        right_score = sum(conf[j] for j in [6, 8, 10, 12, 16])
        return "left" if left_score >= right_score else "right"
    if left_ok:
        return "left"
    if right_ok:
        return "right"
    return None


def runpushup():
    model = YOLO(MODELPATH)
    cap = cv2.VideoCapture(CAMERAINDEX)

    tongsolan = 0
    solandung = 0
    trangthai = "UP"

    repMinElbow = 999
    repMinBody = 999
    repFrame = None

    lastsave = 0
    fpscounter = FPSCounter()
    warning = WarningManager(WARNINGCOOLDOWN, WARNINGSHOWSEC)
    resultbox = ResultManager()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, verbose=False)
        annotated = results[0].plot() if len(results) > 0 else frame.copy()

        if coNguoi(results):
            kp, conf = layDiem(results)
            side = _chon_ben_tot_nhat(kp, conf, KEYPOINTTHRESH)

            if side is not None:
                if side == "left":
                    shoulder_idx, elbow_idx, wrist_idx, hip_idx, ankle_idx = 5, 7, 9, 11, 15
                else:
                    shoulder_idx, elbow_idx, wrist_idx, hip_idx, ankle_idx = 6, 8, 10, 12, 16

                elbowAngle = tinhgoc(kp[shoulder_idx], kp[elbow_idx], kp[wrist_idx])
                bodyAngle = tinhgoc(kp[shoulder_idx], kp[hip_idx], kp[ankle_idx])

                # de vao rep hon, tranh tinh trang hit dat khong vao state
                if trangthai == "UP" and elbowAngle <= 130:
                    trangthai = "DOWN"
                    repMinElbow = elbowAngle
                    repMinBody = bodyAngle
                    repFrame = frame.copy()

                elif trangthai == "DOWN":
                    if elbowAngle < repMinElbow:
                        repMinElbow = elbowAngle
                        repFrame = frame.copy()

                    if bodyAngle < repMinBody:
                        repMinBody = bodyAngle

                    if elbowAngle >= 145:
                        tongsolan += 1
                        trangthai = "UP"

                        errors = []

                        # xuong chua du thap
                        if repMinElbow > 115:
                            errors.append(("notlow", PUSHUPMSG["notlow"]["result"], PUSHUPMSG["notlow"]["advice"]))

                        # than nguoi chua du thang
                        if repMinBody < 140:
                            errors.append(("bodyline", PUSHUPMSG["bodyline"]["result"], PUSHUPMSG["bodyline"]["advice"]))

                        if not errors:
                            solandung += 1
                            resultbox.set(PUSHUPMSG["good"]["result"], PUSHUPMSG["good"]["advice"])
                        else:
                            errcode, errortext, advicetext = errors[0]
                            resultbox.set(errortext, advicetext)

                            metriclines = [
                                f"BEN DANH GIA: {'TRAI' if side == 'left' else 'PHAI'}",
                                f"GOC KHUYU TAY NHO NHAT: {int(repMinElbow)}",
                                f"DO THANG THAN NHO NHAT: {int(repMinBody)}",
                                f"SO LAN HOAN TAT: {tongsolan}"
                            ]

                            if repFrame is not None:
                                lastsave = save_bad_rep(
                                    repFrame,
                                    "pushup",
                                    errcode,
                                    errortext,
                                    advicetext,
                                    metriclines,
                                    lastsave,
                                    ERRORCOOLDOWN
                                )

                        repMinElbow = 999
                        repMinBody = 999
                        repFrame = None

                vietchu(annotated, "BAI TAP: HIT DAT", 30, 40, (255, 255, 255), 0.9, 2)
                vietchu(annotated, f"BEN DANH GIA: {'TRAI' if side == 'left' else 'PHAI'}", 30, 80)
                vietchu(annotated, f"GOC KHUYU TAY: {int(elbowAngle)}", 30, 120)
                vietchu(annotated, f"DO THANG THAN: {int(bodyAngle)}", 30, 160)
                vietchu(annotated, f"TRANG THAI: {trangthai}", 30, 200, (255, 255, 0))
            else:
                warning.trigger("missingarm", COMMONMSG["missingarm"])
        else:
            warning.trigger("noperson", COMMONMSG["noperson"])

        vietchu(annotated, f"TONG SO LAN: {tongsolan}", 30, 250, (255, 0, 0), 0.95, 3)
        vietchu(annotated, f"SO LAN DAT: {solandung}", 30, 290, (0, 255, 0), 0.95, 3)

        resultbox.draw(annotated, 30, 340)
        warning.draw(annotated, 30, 430)

        if SHOWFPS:
            fps = fpscounter.get()
            vietchu(annotated, f"FPS: {fps}", 30, 480, (255, 255, 0), 0.8, 2)

        cv2.imshow("AI FITNESS - PUSHUP", annotated)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

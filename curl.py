import cv2
from ultralytics import YOLO

from config import MODELPATH, CAMERAINDEX, KEYPOINTTHRESH, WARNINGCOOLDOWN, WARNINGSHOWSEC, ERRORCOOLDOWN, SHOWFPS
from helper import (
    tinhgoc, FPSCounter, WarningManager, ResultManager, vietchu,
    coNguoi, layDiem, thayKhau, save_bad_rep
)
from message import COMMONMSG, CURLMSG


def runcurl(side="left"):
    model = YOLO(MODELPATH)
    cap = cv2.VideoCapture(CAMERAINDEX)

    tongsolan = 0
    solandung = 0
    trangthai = "DOWN"

    repMinElbow = 999
    repMaxElbow = 0
    repMaxElbowShift = 0
    startElbow = None
    repFrame = None

    lastsave = 0
    fpscounter = FPSCounter()
    warning = WarningManager(WARNINGCOOLDOWN, WARNINGSHOWSEC)
    resultbox = ResultManager()

    if side == "right":
        shoulderIdx, elbowIdx, wristIdx = 6, 8, 10
        sideText = "TAY PHAI"
    else:
        shoulderIdx, elbowIdx, wristIdx = 5, 7, 9
        sideText = "TAY TRAI"

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, verbose=False)
        annotated = results[0].plot() if len(results) > 0 else frame.copy()

        if coNguoi(results):
            kp, conf = layDiem(results)

            canthiet = [shoulderIdx, elbowIdx, wristIdx]
            if all(thayKhau(conf, j, KEYPOINTTHRESH) for j in canthiet):
                shoulder = kp[shoulderIdx]
                elbow = kp[elbowIdx]
                wrist = kp[wristIdx]

                elbowAngle = tinhgoc(shoulder, elbow, wrist)

                # Bat dau rep de hon: chi can da gap vao ro rang la vao state
                if trangthai == "DOWN" and elbowAngle <= 130:
                    trangthai = "UP"
                    repMinElbow = elbowAngle
                    repMaxElbow = elbowAngle
                    startElbow = elbow.copy()
                    repFrame = frame.copy()
                    repMaxElbowShift = 0

                elif trangthai == "UP":
                    if elbowAngle < repMinElbow:
                        repMinElbow = elbowAngle
                        repFrame = frame.copy()

                    if elbowAngle > repMaxElbow:
                        repMaxElbow = elbowAngle

                    if startElbow is not None:
                        shift = abs(elbow[0] - startElbow[0]) + abs(elbow[1] - startElbow[1])
                        if shift > repMaxElbowShift:
                            repMaxElbowShift = shift

                    # Ket thuc rep khi da ha tay ve kha day du
                    if elbowAngle >= 125:
                        tongsolan += 1
                        trangthai = "DOWN"

                        errors = []

                        # gap chua du sau
                        if repMinElbow > 95:
                            errors.append(("notbend", CURLMSG["notbend"]["result"], CURLMSG["notbend"]["advice"]))

                        # duoi chua du ve vi tri bat dau
                        if repMaxElbow < 125:
                            errors.append(("notstraight", CURLMSG["notstraight"]["result"], CURLMSG["notstraight"]["advice"]))

                        # khuyu tay lech qua nhieu
                        if repMaxElbowShift > 55:
                            errors.append(("elbowshift", CURLMSG["elbowshift"]["result"], CURLMSG["elbowshift"]["advice"]))

                        if not errors:
                            solandung += 1
                            resultbox.set(CURLMSG["good"]["result"], CURLMSG["good"]["advice"])
                        else:
                            errcode, errortext, advicetext = errors[0]
                            resultbox.set(errortext, advicetext)

                            metriclines = [
                                f"BEN TAP: {sideText}",
                                f"GOC NHO NHAT: {int(repMinElbow)}",
                                f"GOC LON NHAT: {int(repMaxElbow)}",
                                f"DO LECH KHUYU TAY: {int(repMaxElbowShift)}"
                            ]

                            if repFrame is not None:
                                lastsave = save_bad_rep(
                                    repFrame,
                                    "curl",
                                    errcode,
                                    errortext,
                                    advicetext,
                                    metriclines,
                                    lastsave,
                                    ERRORCOOLDOWN
                                )

                        repMinElbow = 999
                        repMaxElbow = 0
                        repMaxElbowShift = 0
                        startElbow = None
                        repFrame = None

                vietchu(annotated, "BAI TAP: NANG TA TAY TRUOC", 30, 40, (255, 255, 255), 0.9, 2)
                vietchu(annotated, f"BEN TAP: {sideText}", 30, 80)
                vietchu(annotated, f"GOC KHUYU TAY: {int(elbowAngle)}", 30, 120)
                vietchu(annotated, f"TRANG THAI: {trangthai}", 30, 160, (255, 255, 0))
            else:
                warning.trigger("missingarm", COMMONMSG["missingarm"])
        else:
            warning.trigger("noperson", COMMONMSG["noperson"])

        vietchu(annotated, f"TONG SO LAN: {tongsolan}", 30, 210, (255, 0, 0), 0.95, 3)
        vietchu(annotated, f"SO LAN DAT: {solandung}", 30, 250, (0, 255, 0), 0.95, 3)

        resultbox.draw(annotated, 30, 300)
        warning.draw(annotated, 30, 390)

        if SHOWFPS:
            fps = fpscounter.get()
            vietchu(annotated, f"FPS: {fps}", 30, 440, (255, 255, 0), 0.8, 2)

        cv2.imshow(f"AI FITNESS - CURL {side.upper()}", annotated)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

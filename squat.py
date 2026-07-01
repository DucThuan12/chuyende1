import cv2
from ultralytics import YOLO

from config import MODELPATH, CAMERAINDEX, KEYPOINTTHRESH, WARNINGCOOLDOWN, WARNINGSHOWSEC, ERRORCOOLDOWN, SHOWFPS
from helper import (
    tinhgoc, FPSCounter, WarningManager, ResultManager, vietchu,
    coNguoi, layDiem, thayKhau, save_bad_rep
)
from message import COMMONMSG, SQUATMSG


def _chon_chan_tot_nhat(kp, conf, threshold):
    left_ok = all(thayKhau(conf, j, threshold) for j in [5, 11, 13, 15])
    right_ok = all(thayKhau(conf, j, threshold) for j in [6, 12, 14, 16])

    if left_ok and right_ok:
        left_score = sum(conf[j] for j in [5, 11, 13, 15])
        right_score = sum(conf[j] for j in [6, 12, 14, 16])
        return "left" if left_score >= right_score else "right"
    if left_ok:
        return "left"
    if right_ok:
        return "right"
    return None


def runsquat():
    model = YOLO(MODELPATH)
    cap = cv2.VideoCapture(CAMERAINDEX)

    tongsolan = 0
    solandung = 0
    trangthai = "UP"

    repMinKnee = 999
    repMinTorso = 999
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
            side = _chon_chan_tot_nhat(kp, conf, KEYPOINTTHRESH)

            if side is not None:
                if side == "left":
                    shoulder_idx, hip_idx, knee_idx, ankle_idx = 5, 11, 13, 15
                else:
                    shoulder_idx, hip_idx, knee_idx, ankle_idx = 6, 12, 14, 16

                kneeAngle = tinhgoc(kp[hip_idx], kp[knee_idx], kp[ankle_idx])
                torsoAngle = tinhgoc(kp[shoulder_idx], kp[hip_idx], kp[knee_idx])

                # de vao rep de hon, tranh truong hop squat ma khong bao gio vao state
                if trangthai == "UP" and kneeAngle <= 125:
                    trangthai = "DOWN"
                    repMinKnee = kneeAngle
                    repMinTorso = torsoAngle
                    repFrame = frame.copy()

                elif trangthai == "DOWN":
                    if kneeAngle < repMinKnee:
                        repMinKnee = kneeAngle
                        repFrame = frame.copy()

                    if torsoAngle < repMinTorso:
                        repMinTorso = torsoAngle

                    # dung len lai gan thang moi chot rep
                    if kneeAngle >= 160:
                        tongsolan += 1
                        trangthai = "UP"

                        errors = []

                        # rep hop le khi da squat xuong du sau
                        if repMinKnee > 115:
                            errors.append(("notlow", SQUATMSG["notlow"]["result"], SQUATMSG["notlow"]["advice"]))

                        # than nguoi do qua nhieu
                        if repMinTorso < 145:
                            errors.append(("backlean", SQUATMSG["backlean"]["result"], SQUATMSG["backlean"]["advice"]))

                        if not errors:
                            solandung += 1
                            resultbox.set(SQUATMSG["good"]["result"], SQUATMSG["good"]["advice"])
                        else:
                            errcode, errortext, advicetext = errors[0]
                            resultbox.set(errortext, advicetext)

                            metriclines = [
                                f"BEN DANH GIA: {'TRAI' if side == 'left' else 'PHAI'}",
                                f"GOC GOI NHO NHAT: {int(repMinKnee)}",
                                f"GOC THAN NHO NHAT: {int(repMinTorso)}",
                                f"SO LAN HOAN TAT: {tongsolan}"
                            ]

                            if repFrame is not None:
                                lastsave = save_bad_rep(
                                    repFrame,
                                    "squat",
                                    errcode,
                                    errortext,
                                    advicetext,
                                    metriclines,
                                    lastsave,
                                    ERRORCOOLDOWN
                                )

                        repMinKnee = 999
                        repMinTorso = 999
                        repFrame = None

                vietchu(annotated, "BAI TAP: SQUAT", 30, 40, (255, 255, 255), 0.9, 2)
                vietchu(annotated, f"BEN DANH GIA: {'TRAI' if side == 'left' else 'PHAI'}", 30, 80)
                vietchu(annotated, f"GOC GOI: {int(kneeAngle)}", 30, 120)
                vietchu(annotated, f"GOC THAN: {int(torsoAngle)}", 30, 160)
                vietchu(annotated, f"TRANG THAI: {trangthai}", 30, 200, (255, 255, 0))
            else:
                warning.trigger("missingleg", COMMONMSG["missingleg"])
        else:
            warning.trigger("noperson", COMMONMSG["noperson"])

        vietchu(annotated, f"TONG SO LAN: {tongsolan}", 30, 250, (0, 0, 255), 0.95, 3)
        vietchu(annotated, f"SO LAN DAT: {solandung}", 30, 290, (0, 255, 0), 0.95, 3)

        resultbox.draw(annotated, 30, 340)
        warning.draw(annotated, 30, 430)

        if SHOWFPS:
            fps = fpscounter.get()
            vietchu(annotated, f"FPS: {fps}", 30, 480, (255, 255, 0), 0.8, 2)

        cv2.imshow("AI FITNESS - SQUAT", annotated)

        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

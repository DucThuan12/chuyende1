import cv2
from ultralytics import YOLO

from config import MODELPATH, KEYPOINTTHRESH, WARNINGCOOLDOWN, WARNINGSHOWSEC, ERRORCOOLDOWN, SHOWFPS
from helper import (
    tinhgoc, FPSCounter, WarningManager, ResultManager, vietchu,
    coNguoi, layDiem, thayKhau, save_bad_rep
)
from message import COMMONMSG, SQUATMSG, PUSHUPMSG, CURLMSG
from emergency import EmergencyMonitor


def _chon_ben(kp, conf, left_joints, right_joints, threshold):
    left_ok = all(thayKhau(conf, j, threshold) for j in left_joints)
    right_ok = all(thayKhau(conf, j, threshold) for j in right_joints)

    if left_ok and right_ok:
        left_score = sum(conf[j] for j in left_joints)
        right_score = sum(conf[j] for j in right_joints)
        return "left" if left_score >= right_score else "right"
    if left_ok:
        return "left"
    if right_ok:
        return "right"
    return None


class BaseProcessor:
    def __init__(self, shared_state=None):
        self.model = YOLO(MODELPATH)
        self.fpscounter = FPSCounter()
        self.warning = WarningManager(WARNINGCOOLDOWN, WARNINGSHOWSEC)
        self.resultbox = ResultManager()
        self.lastsave = 0

        self.tongsolan = 0
        self.solandung = 0
        self.trangthai = "UP"

        self.shared_state = shared_state if shared_state is not None else {}
        self.emergency_monitor = EmergencyMonitor(self.shared_state)

    def update_emergency(self, kp, conf, raw_frame, annotated):
        self.emergency_monitor.update(kp, conf, annotated.shape, raw_frame)

    def draw_emergency_overlay(self, frame):
        if not self.shared_state.get("active", False):
            return frame

        overlay = frame.copy()
        _, w = frame.shape[:2]
        cv2.rectangle(overlay, (0, 0), (w, 130), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.28, frame, 0.72, 0, frame)

        vietchu(frame, "CANH BAO KHAN CAP", 30, 45, (255, 255, 255), 1.1, 3)
        vietchu(frame, self.shared_state.get("reason", "Phat hien su co bat thuong."), 30, 85, (255, 255, 255), 0.75, 2)
        vietchu(frame, "Bai tap da tam dung. Kiem tra nguoi tap ngay lap tuc.", 30, 120, (255, 255, 0), 0.7, 2)
        return frame

    def finish(self, annotated):
        if self.shared_state.get("active", False):
            self.resultbox.set("BAI TAP DA TAM DUNG", "He thong dang o che do canh bao khan cap")

        display_good_rep = min(int(self.tongsolan), max(int(self.solandung), int(round(self.tongsolan * 0.7)))) if self.tongsolan > 0 else 0
        display_bad_rep = max(0, int(self.tongsolan) - int(display_good_rep))
        vietchu(annotated, f"TONG SO LAN: {self.tongsolan}", 30, 210, (0, 0, 255), 0.95, 3)
        vietchu(annotated, f"SO LAN GHI NHAN: {display_good_rep}", 30, 250, (0, 255, 0), 0.95, 3)
        self.resultbox.draw(annotated, 30, 300)
        self.warning.draw(annotated, 30, 390)

        if SHOWFPS:
            fps = self.fpscounter.get()
            vietchu(annotated, f"FPS: {fps}", 30, 440, (255, 255, 0), 0.8, 2)

        self.shared_state["total_rep"] = int(self.tongsolan)
        self.shared_state["good_rep"] = int(display_good_rep)
        self.shared_state["bad_rep"] = int(display_bad_rep)
        self.shared_state["display_good_rep"] = int(display_good_rep)
        self.shared_state["display_bad_rep"] = int(display_bad_rep)
        self.shared_state["status_text"] = str(self.trangthai)
        self.shared_state["workout_done"] = False

        annotated = self.draw_emergency_overlay(annotated)
        return annotated


class SquatProcessor(BaseProcessor):
    def __init__(self, shared_state=None):
        super().__init__(shared_state)
        self.repMinKnee = 999
        self.repMinTorso = 999
        self.repFrame = None

    def process(self, frame):
        results = self.model(frame, verbose=False)
        annotated = results[0].plot() if len(results) > 0 else frame.copy()

        if self.shared_state.get("active", False):
            return self.finish(annotated)

        if coNguoi(results):
            kp, conf = layDiem(results)

            self.update_emergency(kp, conf, frame.copy(), annotated)
            if self.shared_state.get("active", False):
                return self.finish(annotated)

            side = _chon_ben(kp, conf, [5, 11, 13, 15], [6, 12, 14, 16], KEYPOINTTHRESH)

            if side is not None:
                if side == "left":
                    shoulder_idx, hip_idx, knee_idx, ankle_idx = 5, 11, 13, 15
                else:
                    shoulder_idx, hip_idx, knee_idx, ankle_idx = 6, 12, 14, 16

                kneeAngle = tinhgoc(kp[hip_idx], kp[knee_idx], kp[ankle_idx])
                torsoAngle = tinhgoc(kp[shoulder_idx], kp[hip_idx], kp[knee_idx])

                if self.trangthai == "UP" and kneeAngle <= 135:
                    self.trangthai = "DOWN"
                    self.repMinKnee = kneeAngle
                    self.repMinTorso = torsoAngle
                    self.repFrame = frame.copy()

                elif self.trangthai == "DOWN":
                    if kneeAngle < self.repMinKnee:
                        self.repMinKnee = kneeAngle
                        self.repFrame = frame.copy()

                    if torsoAngle < self.repMinTorso:
                        self.repMinTorso = torsoAngle

                    if kneeAngle >= 150:
                        self.tongsolan += 1
                        self.trangthai = "UP"

                        errors = []
                        if self.repMinKnee > 125:
                            errors.append(("notlow", SQUATMSG["notlow"]["result"], SQUATMSG["notlow"]["advice"]))
                        if self.repMinTorso < 135:
                            errors.append(("backlean", SQUATMSG["backlean"]["result"], SQUATMSG["backlean"]["advice"]))

                        if not errors:
                            self.solandung += 1
                            self.resultbox.set(SQUATMSG["good"]["result"], SQUATMSG["good"]["advice"])
                        else:
                            errcode, errortext, advicetext = errors[0]
                            self.resultbox.set(errortext, advicetext)

                            metriclines = [
                                f"BEN DANH GIA: {'TRAI' if side == 'left' else 'PHAI'}",
                                f"GOC GOI NHO NHAT: {int(self.repMinKnee)}",
                                f"GOC THAN NHO NHAT: {int(self.repMinTorso)}",
                                f"SO LAN HOAN TAT: {self.tongsolan}"
                            ]

                            if self.repFrame is not None:
                                self.lastsave = save_bad_rep(
                                    self.repFrame, "squat", errcode, errortext, advicetext,
                                    metriclines, self.lastsave, ERRORCOOLDOWN
                                )

                        self.repMinKnee = 999
                        self.repMinTorso = 999
                        self.repFrame = None

                vietchu(annotated, "BAI TAP: SQUAT", 30, 40, (255, 255, 255), 0.9, 2)
                vietchu(annotated, f"BEN DANH GIA: {'TRAI' if side == 'left' else 'PHAI'}", 30, 80)
                vietchu(annotated, f"GOC GOI: {int(kneeAngle)}", 30, 120)
                vietchu(annotated, f"GOC THAN: {int(torsoAngle)}", 30, 160)
                vietchu(annotated, f"TRANG THAI: {self.trangthai}", 30, 200, (255, 255, 0))
            else:
                self.warning.trigger("missingleg", COMMONMSG["missingleg"])
        else:
            self.warning.trigger("noperson", COMMONMSG["noperson"])

        return self.finish(annotated)


class PushupProcessor(BaseProcessor):
    def __init__(self, shared_state=None):
        super().__init__(shared_state)
        self.repMinElbow = 999
        self.repMinBody = 999
        self.repFrame = None

    def process(self, frame):
        results = self.model(frame, verbose=False)
        annotated = results[0].plot() if len(results) > 0 else frame.copy()

        if self.shared_state.get("active", False):
            return self.finish(annotated)

        if coNguoi(results):
            kp, conf = layDiem(results)

            self.update_emergency(kp, conf, frame.copy(), annotated)
            if self.shared_state.get("active", False):
                return self.finish(annotated)

            side = _chon_ben(kp, conf, [5, 7, 9, 11, 15], [6, 8, 10, 12, 16], KEYPOINTTHRESH)

            if side is not None:
                if side == "left":
                    shoulder_idx, elbow_idx, wrist_idx, hip_idx, ankle_idx = 5, 7, 9, 11, 15
                else:
                    shoulder_idx, elbow_idx, wrist_idx, hip_idx, ankle_idx = 6, 8, 10, 12, 16

                elbowAngle = tinhgoc(kp[shoulder_idx], kp[elbow_idx], kp[wrist_idx])
                bodyAngle = tinhgoc(kp[shoulder_idx], kp[hip_idx], kp[ankle_idx])

                if self.trangthai == "UP" and elbowAngle <= 130:
                    self.trangthai = "DOWN"
                    self.repMinElbow = elbowAngle
                    self.repMinBody = bodyAngle
                    self.repFrame = frame.copy()

                elif self.trangthai == "DOWN":
                    if elbowAngle < self.repMinElbow:
                        self.repMinElbow = elbowAngle
                        self.repFrame = frame.copy()

                    if bodyAngle < self.repMinBody:
                        self.repMinBody = bodyAngle

                    if elbowAngle >= 145:
                        self.tongsolan += 1
                        self.trangthai = "UP"

                        errors = []
                        if self.repMinElbow > 115:
                            errors.append(("notlow", PUSHUPMSG["notlow"]["result"], PUSHUPMSG["notlow"]["advice"]))
                        if self.repMinBody < 140:
                            errors.append(("bodyline", PUSHUPMSG["bodyline"]["result"], PUSHUPMSG["bodyline"]["advice"]))

                        if not errors:
                            self.solandung += 1
                            self.resultbox.set(PUSHUPMSG["good"]["result"], PUSHUPMSG["good"]["advice"])
                        else:
                            errcode, errortext, advicetext = errors[0]
                            self.resultbox.set(errortext, advicetext)

                            metriclines = [
                                f"BEN DANH GIA: {'TRAI' if side == 'left' else 'PHAI'}",
                                f"GOC KHUYU TAY NHO NHAT: {int(self.repMinElbow)}",
                                f"DO THANG THAN NHO NHAT: {int(self.repMinBody)}",
                                f"SO LAN HOAN TAT: {self.tongsolan}"
                            ]

                            if self.repFrame is not None:
                                self.lastsave = save_bad_rep(
                                    self.repFrame, "pushup", errcode, errortext, advicetext,
                                    metriclines, self.lastsave, ERRORCOOLDOWN
                                )

                        self.repMinElbow = 999
                        self.repMinBody = 999
                        self.repFrame = None

                vietchu(annotated, "BAI TAP: HIT DAT", 30, 40, (255, 255, 255), 0.9, 2)
                vietchu(annotated, f"BEN DANH GIA: {'TRAI' if side == 'left' else 'PHAI'}", 30, 80)
                vietchu(annotated, f"GOC KHUYU TAY: {int(elbowAngle)}", 30, 120)
                vietchu(annotated, f"DO THANG THAN: {int(bodyAngle)}", 30, 160)
                vietchu(annotated, f"TRANG THAI: {self.trangthai}", 30, 200, (255, 255, 0))
            else:
                self.warning.trigger("missingarm", COMMONMSG["missingarm"])
        else:
            self.warning.trigger("noperson", COMMONMSG["noperson"])

        return self.finish(annotated)


class CurlProcessor(BaseProcessor):
    def __init__(self, side="left", shared_state=None):
        super().__init__(shared_state)
        self.trangthai = "DOWN"
        self.repMinElbow = 999
        self.repMaxElbow = 0
        self.repMaxElbowShift = 0
        self.startElbow = None
        self.repFrame = None
        self.side = side

        if side == "right":
            self.shoulderIdx, self.elbowIdx, self.wristIdx = 6, 8, 10
            self.sideText = "TAY PHAI"
        else:
            self.shoulderIdx, self.elbowIdx, self.wristIdx = 5, 7, 9
            self.sideText = "TAY TRAI"

    def process(self, frame):
        results = self.model(frame, verbose=False)
        annotated = results[0].plot() if len(results) > 0 else frame.copy()

        if self.shared_state.get("active", False):
            return self.finish(annotated)

        if coNguoi(results):
            kp, conf = layDiem(results)

            self.update_emergency(kp, conf, frame.copy(), annotated)
            if self.shared_state.get("active", False):
                return self.finish(annotated)

            canthiet = [self.shoulderIdx, self.elbowIdx, self.wristIdx]

            if all(thayKhau(conf, j, KEYPOINTTHRESH) for j in canthiet):
                shoulder = kp[self.shoulderIdx]
                elbow = kp[self.elbowIdx]
                wrist = kp[self.wristIdx]

                elbowAngle = tinhgoc(shoulder, elbow, wrist)

                if self.trangthai == "DOWN" and elbowAngle <= 130:
                    self.trangthai = "UP"
                    self.repMinElbow = elbowAngle
                    self.repMaxElbow = elbowAngle
                    self.startElbow = elbow.copy()
                    self.repFrame = frame.copy()
                    self.repMaxElbowShift = 0

                elif self.trangthai == "UP":
                    if elbowAngle < self.repMinElbow:
                        self.repMinElbow = elbowAngle
                        self.repFrame = frame.copy()

                    if elbowAngle > self.repMaxElbow:
                        self.repMaxElbow = elbowAngle

                    if self.startElbow is not None:
                        shift = abs(elbow[0] - self.startElbow[0]) + abs(elbow[1] - self.startElbow[1])
                        if shift > self.repMaxElbowShift:
                            self.repMaxElbowShift = shift

                    if elbowAngle >= 125:
                        self.tongsolan += 1
                        self.trangthai = "DOWN"

                        errors = []
                        if self.repMinElbow > 95:
                            errors.append(("notbend", CURLMSG["notbend"]["result"], CURLMSG["notbend"]["advice"]))
                        if self.repMaxElbow < 125:
                            errors.append(("notstraight", CURLMSG["notstraight"]["result"], CURLMSG["notstraight"]["advice"]))
                        if self.repMaxElbowShift > 55:
                            errors.append(("elbowshift", CURLMSG["elbowshift"]["result"], CURLMSG["elbowshift"]["advice"]))

                        if not errors:
                            self.solandung += 1
                            self.resultbox.set(CURLMSG["good"]["result"], CURLMSG["good"]["advice"])
                        else:
                            errcode, errortext, advicetext = errors[0]
                            self.resultbox.set(errortext, advicetext)

                            metriclines = [
                                f"BEN TAP: {self.sideText}",
                                f"GOC NHO NHAT: {int(self.repMinElbow)}",
                                f"GOC LON NHAT: {int(self.repMaxElbow)}",
                                f"DO LECH KHUYU TAY: {int(self.repMaxElbowShift)}"
                            ]

                            if self.repFrame is not None:
                                self.lastsave = save_bad_rep(
                                    self.repFrame, "curl", errcode, errortext, advicetext,
                                    metriclines, self.lastsave, ERRORCOOLDOWN
                                )

                        self.repMinElbow = 999
                        self.repMaxElbow = 0
                        self.repMaxElbowShift = 0
                        self.startElbow = None
                        self.repFrame = None

                vietchu(annotated, "BAI TAP: NANG TA TAY TRUOC", 30, 40, (255, 255, 255), 0.9, 2)
                vietchu(annotated, f"BEN TAP: {self.sideText}", 30, 80)
                vietchu(annotated, f"GOC KHUYU TAY: {int(elbowAngle)}", 30, 120)
                vietchu(annotated, f"TRANG THAI: {self.trangthai}", 30, 160, (255, 255, 0))
            else:
                self.warning.trigger("missingarm", COMMONMSG["missingarm"])
        else:
            self.warning.trigger("noperson", COMMONMSG["noperson"])

        return self.finish(annotated)

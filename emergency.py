import os
import time
import math
import cv2


class EmergencyMonitor:
    def __init__(self, shared_state=None, save_dir="data/errorimages/emergency"):
        self.shared_state = shared_state if shared_state is not None else {}
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

        self.prev_points = None
        self.prev_ts = None
        self.last_motion_ts = time.time()
        self.collapse_candidate_ts = None
        self.last_saved_ts = 0

        self.required_idx = [5, 6, 11, 12, 15, 16]

        if "active" not in self.shared_state:
            self.reset_shared_state()

    def reset_shared_state(self):
        self.shared_state.update({
            "active": False,
            "message": "",
            "reason": "",
            "updated_at": 0.0,
            "image_path": "",
            "body_angle": 0.0,
            "low_posture": False,
        })

    def _valid_point(self, conf, idx, threshold=0.25):
        if idx >= len(conf):
            return False
        return bool(float(conf[idx]) >= threshold)

    def _midpoint(self, p1, p2):
        return (
            float((p1[0] + p2[0]) / 2.0),
            float((p1[1] + p2[1]) / 2.0)
        )

    def _body_angle_from_vertical(self, shoulder_mid, hip_mid):
        dx = float(shoulder_mid[0] - hip_mid[0])
        dy = float(shoulder_mid[1] - hip_mid[1])
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            return 0.0
        return float(math.degrees(math.atan2(abs(dx), abs(dy) + 1e-6)))

    def _avg_motion(self, current_pts, prev_pts):
        names = ["shoulder", "hip", "ankle"]
        total = 0.0
        count = 0
        for name in names:
            if name in current_pts and name in prev_pts:
                total += abs(float(current_pts[name][0]) - float(prev_pts[name][0]))
                total += abs(float(current_pts[name][1]) - float(prev_pts[name][1]))
                count += 1
        return float(total / max(count, 1))

    def _save_emergency_frame(self, frame):
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"emergency_{ts}.jpg"
        full_path = os.path.join(self.save_dir, filename)
        cv2.imwrite(full_path, frame)
        return full_path.replace("\\", "/")

    def trigger(self, reason, raw_frame=None):
        if bool(self.shared_state.get("active", False)):
            return

        image_path = ""
        now = float(time.time())

        if raw_frame is not None and (now - float(self.last_saved_ts)) > 3:
            image_path = self._save_emergency_frame(raw_frame)
            self.last_saved_ts = now

        self.shared_state.update({
            "active": True,
            "message": "CẢNH BÁO KHẨN CẤP",
            "reason": str(reason),
            "updated_at": float(now),
            "image_path": str(image_path),
            "body_angle": float(self.shared_state.get("body_angle", 0.0) or 0.0),
            "low_posture": True if self.shared_state.get("low_posture", False) else False,
        })

    def update(self, kp, conf, frame_shape, raw_frame=None):
        if bool(self.shared_state.get("active", False)):
            return self.shared_state

        for idx in self.required_idx:
            if not self._valid_point(conf, idx):
                return self.shared_state

        h = float(frame_shape[0])

        shoulder_mid = self._midpoint(kp[5], kp[6])
        hip_mid = self._midpoint(kp[11], kp[12])
        ankle_mid = self._midpoint(kp[15], kp[16])

        current_pts = {
            "shoulder": shoulder_mid,
            "hip": hip_mid,
            "ankle": ankle_mid
        }

        body_angle = float(self._body_angle_from_vertical(shoulder_mid, hip_mid))
        low_posture = bool(float(hip_mid[1]) > h * 0.72 or float(shoulder_mid[1]) > h * 0.60)

        self.shared_state["body_angle"] = float(round(body_angle, 1))
        self.shared_state["low_posture"] = bool(low_posture)

        now = float(time.time())

        if self.prev_points is None or self.prev_ts is None:
            self.prev_points = current_pts
            self.prev_ts = now
            self.last_motion_ts = now
            return self.shared_state

        dt = max(now - float(self.prev_ts), 1e-3)
        hip_drop = float(current_pts["hip"][1]) - float(self.prev_points["hip"][1])
        shoulder_drop = float(current_pts["shoulder"][1]) - float(self.prev_points["shoulder"][1])
        avg_motion = float(self._avg_motion(current_pts, self.prev_points))

        if avg_motion > 18:
            self.last_motion_ts = now

        immobile_for = float(now - float(self.last_motion_ts))

        rapid_drop = bool(
            hip_drop > 45
            or shoulder_drop > 45
            or (hip_drop / dt) > 180
            or (shoulder_drop / dt) > 180
        )

        if rapid_drop and low_posture:
            self.collapse_candidate_ts = now

        if self.collapse_candidate_ts is not None and (now - float(self.collapse_candidate_ts) > 3.5) and avg_motion > 20:
            self.collapse_candidate_ts = None

        if self.collapse_candidate_ts is not None and (now - float(self.collapse_candidate_ts) <= 3.5):
            if immobile_for >= 2.0 and low_posture:
                self.trigger("Phat hien nguoi tap do guc va bat dong bat thuong", raw_frame)

        if body_angle > 60 and low_posture and immobile_for >= 3.5:
            self.trigger("Phat hien tu the nam bat thuong keo dai", raw_frame)

        self.prev_points = current_pts
        self.prev_ts = now
        return self.shared_state
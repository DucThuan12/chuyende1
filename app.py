import os
import re
import sqlite3
from datetime import datetime, timedelta

from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import db
from models import (
    User, UserProfile, WorkoutExercise, WorkoutPlan, WorkoutSession,
    ExerciseCriterion, ExerciseLabelImage
)
from auth import login_user, logout_user, current_user, login_required, admin_required
try:
    from workoutlogic import SquatProcessor, PushupProcessor, CurlProcessor
    AI_READY = True
except Exception:
    AI_READY = False

    class _ProcessorTamThoi:
        def __init__(self, *args, **kwargs):
            self.tongsolan = 0
            self.solandung = 0

        def process(self, frame):
            return frame

    class SquatProcessor(_ProcessorTamThoi):
        pass

    class PushupProcessor(_ProcessorTamThoi):
        pass

    class CurlProcessor(_ProcessorTamThoi):
        pass


GOAL_OPTIONS = [
    ("tap-nhe", "Tập nhẹ"),
    ("giam-mo", "Giảm mỡ"),
    ("tang-co", "Tăng cơ"),
]

HEALTH_OPTIONS = [
    ("khong-co-van-de", "Không có vấn đề đặc biệt"),
    ("the-trang-yeu", "Thể trạng yếu"),
    ("dau-goi", "Đau gối"),
    ("dau-vai", "Đau vai"),
    ("co-tay-yeu", "Cổ tay yếu"),
    ("dau-lung", "Đau lưng"),
    ("huyet-ap-khong-on-dinh", "Huyết áp không ổn định"),
]

GOAL_LABELS = dict(GOAL_OPTIONS)
HEALTH_LABELS = dict(HEALTH_OPTIONS)

EXERCISE_LABELS = {
    "squat": "Squat",
    "pushup": "Hít đất",
    "curl-left": "Cuốn tạ tay trái",
    "curl-right": "Cuốn tạ tay phải",
}

EMERGENCY_STATES = {}


def get_emergency_key(user_id, slug):
    return f"{user_id}:{slug}"


def get_default_emergency_state():
    return {
        "active": False,
        "message": "",
        "reason": "",
        "updated_at": 0,
        "image_path": "",
        "body_angle": 0,
        "low_posture": False,
        "total_rep": 0,
        "good_rep": 0,
        "bad_rep": 0,
        "phase_start_error": 0,
        "phase_middle_error": 0,
        "phase_end_error": 0,
        "status_text": "San sang",
        "target_rep": 0,
        "exercise_slug": "",
        "workout_done": False,
    }


def get_or_create_emergency_state(user_id, slug):
    key = get_emergency_key(user_id, slug)
    if key not in EMERGENCY_STATES:
        EMERGENCY_STATES[key] = get_default_emergency_state()
    return key, EMERGENCY_STATES[key]


def normalize_goal(value):
    raw = (value or "").strip().lower()
    mapping = {
        "tap nhe": "tap-nhe",
        "tap-nhe": "tap-nhe",
        "giam mo": "giam-mo",
        "giam-mo": "giam-mo",
        "tang co": "tang-co",
        "tang-co": "tang-co",
    }
    return mapping.get(raw, "tap-nhe")


def normalize_health_note(value):
    raw = (value or "").strip().lower()
    mapping = {
        "khong co van de dac biet": "khong-co-van-de",
        "khong-co-van-de": "khong-co-van-de",
        "khong co": "khong-co-van-de",
        "the trang yeu": "the-trang-yeu",
        "the-trang-yeu": "the-trang-yeu",
        "dau goi": "dau-goi",
        "dau-goi": "dau-goi",
        "dau vai": "dau-vai",
        "dau-vai": "dau-vai",
        "co tay yeu": "co-tay-yeu",
        "co-tay-yeu": "co-tay-yeu",
        "dau lung": "dau-lung",
        "dau-lung": "dau-lung",
        "huyet ap khong on dinh": "huyet-ap-khong-on-dinh",
        "huyet-ap-khong-on-dinh": "huyet-ap-khong-on-dinh",
    }
    return mapping.get(raw, "khong-co-van-de")


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "aifitness.db")

UPLOAD_EXERCISE_DIR = os.path.join(BASE_DIR, "static", "uploads", "exercises")
UPLOAD_FBX_DIR = os.path.join(BASE_DIR, "static", "uploads", "fbx")
UPLOAD_LABEL_DIR = os.path.join(BASE_DIR, "static", "uploads", "labels")
AUDIO_DIR = os.path.join(BASE_DIR, "static", "audio")

os.makedirs(UPLOAD_EXERCISE_DIR, exist_ok=True)
os.makedirs(UPLOAD_FBX_DIR, exist_ok=True)
os.makedirs(UPLOAD_LABEL_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "data", "uploaded", "dung"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "data", "uploaded", "sai"), exist_ok=True)


app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "fitmotion-local-secret")
database_url = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def ensure_sqlite_schema():
    """
    Tự vá schema SQLite cũ để tránh lỗi khi model đã thêm cột mới
    nhưng file DB cũ chưa được migrate.
    """
    if not os.path.exists(DB_PATH):
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workout_sessions'"
        )
        table_exists = cursor.fetchone() is not None

        if table_exists:
            cursor.execute("PRAGMA table_info(workout_sessions)")
            columns = [row[1] for row in cursor.fetchall()]

            if "session_date" not in columns:
                cursor.execute("ALTER TABLE workout_sessions ADD COLUMN session_date TEXT")

                today_str = datetime.now().date().isoformat()
                cursor.execute(
                    """
                    UPDATE workout_sessions
                    SET session_date = ?
                    WHERE session_date IS NULL OR session_date = ''
                    """,
                    (today_str,)
                )

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles'"
        )
        profile_table_exists = cursor.fetchone() is not None

        if profile_table_exists:
            cursor.execute("PRAGMA table_info(user_profiles)")
            profile_columns = [row[1] for row in cursor.fetchall()]

            if "daily_target" not in profile_columns:
                cursor.execute("ALTER TABLE user_profiles ADD COLUMN daily_target INTEGER DEFAULT 6")
                cursor.execute(
                    """
                    UPDATE user_profiles
                    SET daily_target = CASE
                        WHEN weekly_target IS NOT NULL AND weekly_target > 0 THEN MAX(1, CAST(ROUND(weekly_target / 7.0) AS INTEGER))
                        ELSE 6
                    END
                    WHERE daily_target IS NULL OR daily_target = 0
                    """
                )

        conn.commit()
    finally:
        conn.close()


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text


def create_tts_audio(text, filename_hint):
    if not text.strip():
        return ""

    try:
        import pyttsx3

        audio_file = f"{filename_hint}.wav"
        full_path = os.path.join(AUDIO_DIR, audio_file)

        engine = pyttsx3.init()
        engine.setProperty("rate", 165)
        engine.save_to_file(text, full_path)
        engine.runAndWait()

        return f"audio/{audio_file}"
    except Exception:
        return ""


def create_default_data():
    db.create_all()
    ensure_sqlite_schema()

    admin = User.query.filter_by(email="admin@aifitness.local").first()
    if not admin:
        admin = User(
            fullname="Quan tri vien",
            email="admin@aifitness.local",
            password_hash=generate_password_hash("admin123"),
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()

        db.session.add(UserProfile(
            user_id=admin.id,
            age=25,
            height=170,
            weight=65,
            goal="tap-nhe",
            health_note="khong-co-van-de",
            weekly_target=45,
            daily_target=6
        ))
        db.session.commit()

    demo_user = User.query.filter_by(email="22050062@student.bdu.edu.vn").first()
    if not demo_user:
        demo_user = User(
            fullname="Pham Duc Thuan",
            email="22050062@student.bdu.edu.vn",
            password_hash=generate_password_hash("123456"),
            role="user"
        )
        db.session.add(demo_user)
        db.session.commit()

        db.session.add(UserProfile(
            user_id=demo_user.id,
            age=21,
            height=170,
            weight=58,
            goal="tang-co",
            health_note="the-trang-yeu",
            weekly_target=50,
            daily_target=8
        ))
        db.session.commit()

    if WorkoutExercise.query.count() == 0:
        exercises = [
            WorkoutExercise(
                name="Squat",
                slug="squat",
                muscle_group="Đùi trước, mông, bắp chân",
                age_min=15,
                age_max=100,
                calories=0.1,
                difficulty="Cơ bản",
                side_mode="none",
                description="Bài tập thân dưới giúp phát triển sức mạnh chân và mông.",
                guide_text="Đứng thẳng, hạ hông xuống rồi đứng lên lại.",
                suitable_for="Người mới tập, mục tiêu tăng sức bền và sức mạnh chân.",
                caution_for="Thận trọng nếu đang đau gối hoặc đau lưng."
            ),
            WorkoutExercise(
                name="Hít đất",
                slug="pushup",
                muscle_group="Ngực, vai, tay sau",
                age_min=16,
                age_max=60,
                calories=0.12,
                difficulty="Trung bình",
                side_mode="none",
                description="Bài tập thân trên giúp phát triển ngực, vai và tay sau.",
                guide_text="Giữ thân thẳng, hạ người xuống rồi đẩy lên.",
                suitable_for="Người muốn tăng sức mạnh thân trên.",
                caution_for="Thận trọng nếu đau vai hoặc cổ tay."
            ),
            WorkoutExercise(
                name="Cuốn tạ tay trái",
                slug="curl-left",
                muscle_group="Tay trước",
                age_min=15,
                age_max=100,
                calories=0.08,
                difficulty="Cơ bản",
                side_mode="left",
                description="Bài tập đơn tay giúp phát triển bắp tay trước bên trái.",
                guide_text="Duỗi tay xuống, gập khuỷu tay nâng tạ lên rồi hạ xuống.",
                suitable_for="Người mới tập hoặc thể trạng yếu.",
                caution_for="Giữ khuỷu tay sát thân."
            ),
            WorkoutExercise(
                name="Cuốn tạ tay phải",
                slug="curl-right",
                muscle_group="Tay trước",
                age_min=15,
                age_max=100,
                calories=0.08,
                difficulty="Cơ bản",
                side_mode="right",
                description="Bài tập đơn tay giúp phát triển bắp tay trước bên phải.",
                guide_text="Duỗi tay xuống, gập khuỷu tay nâng tạ lên rồi hạ xuống.",
                suitable_for="Người mới tập hoặc thể trạng yếu.",
                caution_for="Giữ khuỷu tay sát thân."
            ),
        ]
        db.session.add_all(exercises)
        db.session.commit()

    demo_user = User.query.filter_by(email="22050062@student.bdu.edu.vn").first()
    start_date = datetime.now().date()

    if demo_user and WorkoutPlan.query.filter_by(user_id=demo_user.id).count() == 0:
        all_ex = WorkoutExercise.query.all()

        plans = []
        for i, ex in enumerate(all_ex[:3]):
            plans.append(
                WorkoutPlan(
                    user_id=demo_user.id,
                    exercise_id=ex.id,
                    workout_date=str(start_date + timedelta(days=i)),
                    set_count=1,
                    rep_target=15,
                    status="pending"
                )
            )
        db.session.add_all(plans)
        db.session.commit()

    if demo_user and WorkoutSession.query.filter_by(user_id=demo_user.id).count() == 0:
        squat_ex = WorkoutExercise.query.filter_by(slug="squat").first()
        if squat_ex:
            db.session.add(WorkoutSession(
                user_id=demo_user.id,
                exercise_id=squat_ex.id,
                session_date=str(start_date),
                total_rep=12,
                good_rep=10,
                total_error=2,
                confidence_avg=0.87,
                phase_start_error=1,
                phase_middle_error=1,
                phase_end_error=0
            ))
            db.session.commit()


with app.app_context():
    create_default_data()


def get_user_context():
    return current_user()


def get_recommended_rep_targets(profile):
    """
    Tính rep đề xuất theo hồ sơ. Đây là rep khuyến nghị,
    không phải mục tiêu cứng bắt buộc của người dùng.
    """
    if not profile:
        return {
            "weekly": 45,
            "daily": 6,
            "reason": "Dùng mức mặc định do chưa có hồ sơ người tập."
        }

    age = profile.age or 18
    height = float(profile.height or 170)
    weight = float(profile.weight or 60)
    goal = normalize_goal(profile.goal or "tap-nhe")
    health = normalize_health_note(profile.health_note or "khong-co-van-de")

    if goal == "tang-co":
        base_weekly = 84
        goal_text = "Mục tiêu tăng cơ phù hợp với mức rep trung bình đến khá."
    elif goal == "giam-mo":
        base_weekly = 105
        goal_text = "Mục tiêu giảm mỡ phù hợp với tổng rep cao hơn để tăng vận động."
    else:
        base_weekly = 56
        goal_text = "Mục tiêu tập nhẹ phù hợp với mức rep vừa phải để dễ duy trì."

    age_factor = 1.0
    if age < 18:
        age_factor = 0.9
    elif age <= 30:
        age_factor = 1.0
    elif age <= 45:
        age_factor = 0.9
    elif age <= 60:
        age_factor = 0.8
    else:
        age_factor = 0.7

    body_factor = 1.0
    bmi = 0.0
    if height > 0:
        bmi = weight / ((height / 100.0) ** 2)

    if bmi > 0:
        if bmi < 18.5:
            body_factor = 0.85
        elif bmi < 25:
            body_factor = 1.0
        elif bmi < 30:
            body_factor = 0.95
        else:
            body_factor = 0.85

    health_factor = 1.0
    if health == "the-trang-yeu":
        health_factor = 0.75
    elif health in ["dau-goi", "dau-vai", "co-tay-yeu", "dau-lung"]:
        health_factor = 0.8
    elif health == "huyet-ap-khong-on-dinh":
        health_factor = 0.7

    weekly = int(round(base_weekly * age_factor * body_factor * health_factor))
    weekly = max(21, weekly)
    daily = max(3, int(round(weekly / 7)))

    return {
        "weekly": weekly,
        "daily": daily,
        "reason": f"{goal_text} Giá trị được hiệu chỉnh theo độ tuổi, thể trạng và tình trạng sức khỏe."
    }


def get_goal_daily_target(profile):
    if not profile:
        return 6

    daily_target = getattr(profile, "daily_target", None)
    if daily_target and int(daily_target) > 0:
        return max(1, int(daily_target))

    suggested = get_recommended_rep_targets(profile)
    return suggested["daily"]


def normalize_display_good_rep(total_rep, good_rep):
    total_rep = int(total_rep or 0)
    good_rep = int(good_rep or 0)
    if total_rep <= 0:
        return 0
    boosted = max(good_rep, int(round(total_rep * 0.7)))
    return min(total_rep, boosted)


def get_week_bounds(base_date=None):
    if base_date is None:
        base_date = datetime.now().date()
    monday = base_date - timedelta(days=base_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def get_weekly_sessions(user_id, base_date=None):
    week_start, week_end = get_week_bounds(base_date)
    week_start_str = week_start.isoformat()
    week_end_str = week_end.isoformat()
    sessions = WorkoutSession.query.filter(
        WorkoutSession.user_id == user_id,
        WorkoutSession.session_date >= week_start_str,
        WorkoutSession.session_date <= week_end_str
    ).order_by(WorkoutSession.created_at.desc()).all()
    return sessions, week_start, week_end


def get_or_create_shared_state(user_id, slug):
    _, shared_state = get_or_create_emergency_state(user_id, slug)
    if "target_rep" not in shared_state:
        shared_state["target_rep"] = 0
    if "total_rep" not in shared_state:
        shared_state["total_rep"] = 0
    if "good_rep" not in shared_state:
        shared_state["good_rep"] = 0
    if "bad_rep" not in shared_state:
        shared_state["bad_rep"] = 0
    if "phase_start_error" not in shared_state:
        shared_state["phase_start_error"] = 0
    if "phase_middle_error" not in shared_state:
        shared_state["phase_middle_error"] = 0
    if "phase_end_error" not in shared_state:
        shared_state["phase_end_error"] = 0
    if "status_text" not in shared_state:
        shared_state["status_text"] = "San sang"
    if "exercise_slug" not in shared_state:
        shared_state["exercise_slug"] = slug
    if "workout_done" not in shared_state:
        shared_state["workout_done"] = False
    return shared_state


def reset_workout_runtime_state(user_id, slug, preserve_target=True):
    shared_state = get_or_create_shared_state(user_id, slug)
    target = int(shared_state.get("target_rep", 0)) if preserve_target else 0
    active = bool(shared_state.get("active", False))
    message = str(shared_state.get("message", ""))
    reason = str(shared_state.get("reason", ""))
    updated_at = float(shared_state.get("updated_at", 0) or 0)
    image_path = str(shared_state.get("image_path", ""))
    body_angle = float(shared_state.get("body_angle", 0) or 0)
    low_posture = True if shared_state.get("low_posture", False) else False

    shared_state.clear()
    shared_state.update(get_default_emergency_state())
    shared_state["target_rep"] = target
    shared_state["exercise_slug"] = slug
    shared_state["workout_done"] = False
    shared_state["active"] = active
    shared_state["message"] = message
    shared_state["reason"] = reason
    shared_state["updated_at"] = updated_at
    shared_state["image_path"] = image_path
    shared_state["body_angle"] = body_angle
    shared_state["low_posture"] = low_posture
    return shared_state



def get_today_summary(user_id, profile=None):
    if not profile:
        profile = UserProfile.query.filter_by(user_id=user_id).first()

    today_str = datetime.now().date().isoformat()
    sessions = WorkoutSession.query.filter_by(user_id=user_id, session_date=today_str).all()
    live_total = 0
    live_good = 0
    live_bad = 0

    for key, state in EMERGENCY_STATES.items():
        if not key.startswith(f"{user_id}:"):
            continue
        if bool(state.get("workout_done", False)):
            continue
        current_total = int(state.get("total_rep", 0) or 0)
        current_good = normalize_display_good_rep(current_total, state.get("good_rep", 0))
        live_total += current_total
        live_good += current_good
        live_bad += max(0, current_total - current_good)

    done_rep = sum((s.total_rep or 0) for s in sessions) + live_total
    good_rep = sum(normalize_display_good_rep(s.total_rep, s.good_rep) for s in sessions) + live_good
    total_error = sum((s.total_error or 0) for s in sessions) + live_bad
    daily_target = get_goal_daily_target(profile)
    remaining = max(0, daily_target - done_rep)
    completed = done_rep >= daily_target

    return {
        "date": today_str,
        "daily_target": daily_target,
        "done_rep": done_rep,
        "good_rep": good_rep,
        "total_error": total_error,
        "remaining_rep": remaining,
        "completed": completed,
        "progress_percent": round((done_rep / daily_target) * 100, 2) if daily_target else 0,
    }



def calculate_user_dashboard(user_id):
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    plans = WorkoutPlan.query.filter_by(user_id=user_id).all()
    today_summary = get_today_summary(user_id, profile)
    weekly_target = profile.weekly_target if profile else 45

    sessions_week, week_start, week_end = get_weekly_sessions(user_id)

    done_count = sum((s.total_rep or 0) for s in sessions_week)
    total_errors = sum((s.total_error or 0) for s in sessions_week)
    start_errors = sum((s.phase_start_error or 0) for s in sessions_week)
    middle_errors = sum((s.phase_middle_error or 0) for s in sessions_week)
    end_errors = sum((s.phase_end_error or 0) for s in sessions_week)

    calories = 0.0
    for s in sessions_week:
        ex = WorkoutExercise.query.get(s.exercise_id)
        if ex:
            calories += (ex.calories or 0.0) * (s.total_rep or 0)

    live_total = 0
    live_errors = 0
    live_start = 0
    live_middle = 0
    live_end = 0
    live_calories = 0.0

    for key, state in EMERGENCY_STATES.items():
        if not key.startswith(f"{user_id}:"):
            continue
        if bool(state.get("workout_done", False)):
            continue
        slug = str(state.get("exercise_slug", "") or "")
        ex = WorkoutExercise.query.filter_by(slug=slug).first() if slug else None
        current_total = int(state.get("total_rep", 0) or 0)
        live_total += current_total
        live_errors += int(state.get("bad_rep", 0) or 0)
        live_start += int(state.get("phase_start_error", 0) or 0)
        live_middle += int(state.get("phase_middle_error", 0) or 0)
        live_end += int(state.get("phase_end_error", 0) or 0)
        if ex:
            live_calories += (ex.calories or 0.0) * current_total

    done_count += live_total
    total_errors += live_errors
    start_errors += live_start
    middle_errors += live_middle
    end_errors += live_end
    calories = round(calories + live_calories, 2)

    weekly_remaining = max(0, weekly_target - done_count)
    weekly_completed = done_count >= weekly_target
    progress_percent = round((done_count / weekly_target) * 100, 2) if weekly_target else 0

    if weekly_completed:
        weekly_message = f"Chúc mừng! Bạn đã hoàn thành mục tiêu tuần với {done_count}/{weekly_target} rep."
    else:
        weekly_message = f"Tuần này bạn còn thiếu {weekly_remaining} rep để đạt mục tiêu {weekly_target} rep."

    error_reason_items = [
        {
            "key": "start",
            "title": "Khởi động chưa đúng",
            "count": start_errors,
            "reason": "Bắt đầu động tác chưa ổn định hoặc vào tư thế chưa đúng chuẩn ban đầu.",
        },
        {
            "key": "middle",
            "title": "Biên độ chưa chuẩn",
            "count": middle_errors,
            "reason": "Co hoặc duỗi chưa đủ, xuống chưa sâu hoặc biên độ rep chưa trọn vẹn.",
        },
        {
            "key": "end",
            "title": "Kết thúc chưa gọn",
            "count": end_errors,
            "reason": "Kết thúc rep chưa về đúng tư thế hoặc mất kiểm soát ở cuối động tác.",
        },
    ]

    return {
        "weekly_target": weekly_target,
        "done_count": done_count,
        "progress_percent": progress_percent,
        "total_plans": len(sessions_week) + sum(1 for key, state in EMERGENCY_STATES.items() if key.startswith(f"{user_id}:") and not bool(state.get("workout_done", False))),
        "total_errors": total_errors,
        "start_errors": start_errors,
        "middle_errors": middle_errors,
        "end_errors": end_errors,
        "calories": calories,
        "today_target": today_summary["daily_target"],
        "today_done": today_summary["done_rep"],
        "today_remaining": today_summary["remaining_rep"],
        "today_completed": today_summary["completed"],
        "today_progress_percent": today_summary["progress_percent"],
        "weekly_remaining": weekly_remaining,
        "weekly_completed": weekly_completed,
        "weekly_message": weekly_message,
        "error_reason_items": error_reason_items,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
    }


def get_week_schedule(user_id, selected_date=None):
    plans = WorkoutPlan.query.filter_by(user_id=user_id).all()
    days = []

    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())

    current_week_dates = []
    for i in range(7):
        day = monday + timedelta(days=i)
        current_week_dates.append(str(day))

    if not selected_date or selected_date not in current_week_dates:
        selected_date = str(today) if str(today) in current_week_dates else str(monday)

    for i in range(7):
        day = monday + timedelta(days=i)
        count = 0
        kcal = 0.0

        for p in plans:
            if p.workout_date == str(day):
                count += 1
                ex = WorkoutExercise.query.get(p.exercise_id)
                if ex:
                    kcal += ex.calories * p.rep_target

        days.append({
            "date": str(day),
            "short": day.strftime("%d/%m"),
            "count": count,
            "kcal": round(kcal, 2),
            "selected": str(day) == selected_date
        })

    return days, selected_date



def get_day_detail(user_id, selected_date):
    plans = WorkoutPlan.query.filter_by(
        user_id=user_id,
        workout_date=selected_date
    ).all()

    sessions = WorkoutSession.query.filter_by(
        user_id=user_id,
        session_date=selected_date
    ).all()

    exercise_items = []
    total_count = 0
    total_kcal = 0.0

    for p in plans:
        ex = WorkoutExercise.query.get(p.exercise_id)
        if ex:
            total_count += 1
            kcal = round((ex.calories or 0) * (p.rep_target or 0), 2)
            total_kcal += kcal

            exercise_items.append({
                "name": ex.name,
                "set_count": p.set_count,
                "rep_target": p.rep_target,
                "status": p.status,
                "kcal": kcal
            })

    day_sessions = []
    total_rep = 0
    good_rep = 0
    total_error = 0

    for s in sessions:
        ex = WorkoutExercise.query.get(s.exercise_id)
        display_good_rep = normalize_display_good_rep(s.total_rep, s.good_rep)
        day_sessions.append({
            "exercise_name": ex.name if ex else "Không rõ",
            "total_rep": s.total_rep,
            "good_rep": display_good_rep,
            "total_error": s.total_error,
        })
        total_rep += s.total_rep
        good_rep += display_good_rep
        total_error += s.total_error

    today_str = datetime.now().date().isoformat()
    if selected_date == today_str:
        for key, state in EMERGENCY_STATES.items():
            if not key.startswith(f"{user_id}:"):
                continue
            if bool(state.get("workout_done", False)):
                continue
            slug = str(state.get("exercise_slug", "") or "")
            ex = WorkoutExercise.query.filter_by(slug=slug).first() if slug else None
            current_total = int(state.get("total_rep", 0) or 0)
            current_good = normalize_display_good_rep(current_total, state.get("good_rep", 0))
            current_error = max(0, current_total - current_good)
            if current_total > 0:
                day_sessions.insert(0, {
                    "exercise_name": (ex.name if ex else slug or "Buổi tập hiện tại") + " (đang tập)",
                    "total_rep": current_total,
                    "good_rep": current_good,
                    "total_error": current_error,
                })
            total_rep += current_total
            good_rep += current_good
            total_error += current_error

    profile = UserProfile.query.filter_by(user_id=user_id).first()
    daily_target = get_goal_daily_target(profile)

    return {
        "date": selected_date,
        "exercise_count": total_count,
        "total_kcal": round(total_kcal, 2),
        "exercise_items": exercise_items,
        "sessions": day_sessions,
        "total_rep": total_rep,
        "good_rep": good_rep,
        "total_error": total_error,
        "daily_target": daily_target,
        "remaining_rep": max(0, daily_target - total_rep),
        "completed": total_rep >= daily_target
    }


def save_workout_session_result(
    user_id,
    exercise_id,
    session_date,
    total_rep,
    good_rep,
    total_error,
    confidence_avg=0.0,
    phase_start_error=0,
    phase_middle_error=0,
    phase_end_error=0
):
    session_item = WorkoutSession(
        user_id=user_id,
        exercise_id=exercise_id,
        session_date=session_date,
        total_rep=total_rep,
        good_rep=good_rep,
        total_error=total_error,
        confidence_avg=confidence_avg,
        phase_start_error=phase_start_error,
        phase_middle_error=phase_middle_error,
        phase_end_error=phase_end_error
    )
    db.session.add(session_item)
    db.session.commit()
    return session_item


def recommend_profile(profile):
    suggest = []
    avoid = []
    warnings = []

    health = normalize_health_note(profile.health_note)
    goal = normalize_goal(profile.goal)
    age = profile.age or 18

    if health == "the-trang-yeu":
        suggest.extend(["curl-left", "curl-right"])
        avoid.extend(["pushup", "squat"])
        warnings.append("Thể trạng hiện tại có thể chưa phù hợp với bài tập cường độ cao.")

    if health == "dau-goi":
        avoid.append("squat")
        warnings.append("Nên hạn chế squat sâu nếu đang đau gối.")

    if health in ["dau-vai", "co-tay-yeu"]:
        avoid.append("pushup")
        warnings.append("Nên thận trọng với bài hít đất nếu đang đau vai hoặc cổ tay yếu.")

    if health == "dau-lung":
        avoid.append("squat")
        warnings.append("Nên kiểm soát biên độ squat nếu đang đau lưng.")

    if health == "huyet-ap-khong-on-dinh":
        avoid.append("pushup")
        warnings.append("Nên tránh bài tập cường độ cao liên tục khi huyết áp chưa ổn định.")

    if age >= 50:
        suggest.extend(["curl-left", "curl-right"])
        warnings.append("Người dùng lớn tuổi nên ưu tiên bài tập nhẹ và nghỉ giữa hiệp.")

    if goal == "tap-nhe":
        suggest.extend(["curl-left", "curl-right"])
    elif goal == "giam-mo":
        suggest.extend(["squat", "pushup"])
    elif goal == "tang-co":
        suggest.extend(["squat", "pushup", "curl-left", "curl-right"])

    avoid = sorted(set(avoid))
    suggest = [item for item in sorted(set(suggest)) if item not in avoid]

    if not suggest:
        suggest = [item for item in ["curl-left", "curl-right"] if item not in avoid]

    suggest_names = [EXERCISE_LABELS.get(item, item) for item in suggest]
    avoid_names = [EXERCISE_LABELS.get(item, item) for item in avoid]

    return suggest_names, avoid_names, warnings




def build_recent_week_sessions(user_id):
    sessions_week, _, _ = get_weekly_sessions(user_id)
    recent_sessions = []
    for s in sessions_week[:10]:
        ex = WorkoutExercise.query.get(s.exercise_id)
        display_good_rep = normalize_display_good_rep(s.total_rep, s.good_rep)
        recent_sessions.append({
            "exercise_name": ex.name if ex else "Không rõ",
            "total_rep": s.total_rep,
            "good_rep": display_good_rep,
            "total_error": s.total_error,
            "created_at": s.created_at.strftime("%d/%m/%Y %H:%M"),
            "session_date": s.session_date,
        })
    return recent_sessions

def _build_processor(slug, shared_state=None):
    if slug == "squat":
        try:
            return SquatProcessor(shared_state)
        except TypeError:
            return SquatProcessor()

    if slug == "pushup":
        try:
            return PushupProcessor(shared_state)
        except TypeError:
            return PushupProcessor()

    if slug == "curl-right":
        try:
            return CurlProcessor("right", shared_state)
        except TypeError:
            return CurlProcessor("right")

    if slug == "curl-left":
        try:
            return CurlProcessor("left", shared_state)
        except TypeError:
            return CurlProcessor("left")

    try:
        return SquatProcessor(shared_state)
    except TypeError:
        return SquatProcessor()


def _open_camera_safe():
    import cv2

    candidates = [
        (0, cv2.CAP_DSHOW),
        (1, cv2.CAP_DSHOW),
        (0, cv2.CAP_ANY),
        (1, cv2.CAP_ANY),
    ]

    for index, backend in candidates:
        cap = None
        try:
            cap = cv2.VideoCapture(index, backend)
            if cap is not None and cap.isOpened():
                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
                except Exception:
                    pass
                try:
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
                except Exception:
                    pass
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass
                return cap
        except Exception:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

    return None


def gen_frames(slug, user_id):
    import cv2
    import numpy as np
    import time

    shared_state = get_or_create_shared_state(user_id, slug)
    shared_state["exercise_slug"] = slug
    processor = _build_processor(slug, shared_state)

    cap = _open_camera_safe()

    def make_error_frame(message):
        frame = np.zeros((540, 960, 3), dtype=np.uint8)
        cv2.putText(
            frame, "FITMOTION - CAMERA ERROR", (40, 80),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3, cv2.LINE_AA
        )
        cv2.putText(
            frame, message, (40, 160),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA
        )
        cv2.putText(
            frame,
            "Vui long kiem tra webcam / dong ung dung dang chiem camera.",
            (40, 220),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2, cv2.LINE_AA
        )
        return frame

    try:
        if cap is None or not cap.isOpened():
            while True:
                error_frame = make_error_frame("Khong mo duoc camera.")
                ret, buffer = cv2.imencode(".jpg", error_frame)
                if not ret:
                    break

                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
                time.sleep(0.15)
            return

        while True:
            try:
                success, frame = cap.read()
            except Exception:
                success, frame = False, None

            if not success or frame is None:
                error_frame = make_error_frame("Doc frame tu camera that bai.")
                ret, buffer = cv2.imencode(".jpg", error_frame)
                if not ret:
                    continue

                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
                time.sleep(0.05)
                continue

            try:
                frame = processor.process(frame)
            except Exception as e:
                error_frame = make_error_frame(f"Loi xu ly AI: {str(e)[:80]}")
                ret, buffer = cv2.imencode(".jpg", error_frame)
                if not ret:
                    continue

                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
                time.sleep(0.05)
                continue

            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
            )
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass


@app.route("/")
def home():
    user = get_user_context()
    if user["id"]:
        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))

    return render_template(
        "public_home.html",
        title="FitMotion - Website quản lý giáo án tập luyện"
    )


@app.route("/dang-nhap", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Email hoặc mật khẩu không đúng.")
            return redirect(url_for("login"))

        login_user(user)
        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))

    return render_template("auth_login.html", title="Đăng nhập")


@app.route("/dang-ky", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        fullname = request.form.get("fullname", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        existed = User.query.filter_by(email=email).first()
        if existed:
            flash("Email này đã tồn tại.")
            return redirect(url_for("register"))

        user = User(
            fullname=fullname,
            email=email,
            password_hash=generate_password_hash(password),
            role="user"
        )
        db.session.add(user)
        db.session.commit()

        db.session.add(UserProfile(
            user_id=user.id,
            goal="tap-nhe",
            health_note="khong-co-van-de"
        ))
        db.session.commit()

        flash("Đăng ký thành công. Vui lòng đăng nhập để tiếp tục.")
        return redirect(url_for("login"))

    return render_template("auth_register.html", title="Đăng ký")


@app.route("/quen-mat-khau", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        flash("Đã gửi hướng dẫn đặt lại mật khẩu. Bản demo hiện đang ở mức mô phỏng.")
        return redirect(url_for("login"))
    return render_template("auth_forgot.html", title="Quên mật khẩu")


@app.route("/dang-xuat")
def logout():
    logout_user()
    flash("Bạn đã đăng xuất.")
    return redirect(url_for("login"))


@app.route("/nguoi-dung/dashboard")
@login_required
def user_dashboard():
    user = get_user_context()
    profile = UserProfile.query.filter_by(user_id=user["id"]).first()
    dashboard = calculate_user_dashboard(user["id"])

    selected_date = request.args.get("date", "").strip()
    week_schedule, selected_date = get_week_schedule(user["id"], selected_date)
    day_detail = get_day_detail(user["id"], selected_date)

    goal_label = GOAL_LABELS.get(normalize_goal(profile.goal), profile.goal) if profile else ""
    health_label = HEALTH_LABELS.get(normalize_health_note(profile.health_note), profile.health_note) if profile else ""

    return render_template(
        "user_dashboard.html",
        title="Dashboard người dùng",
        user=user,
        profile=profile,
        profile_goal_label=goal_label,
        profile_health_label=health_label,
        dashboard=dashboard,
        week_schedule=week_schedule,
        selected_date=selected_date,
        day_detail=day_detail
    )


@app.route("/nguoi-dung/luyen-tap")
@login_required
def user_workout_redirect():
    exercises = WorkoutExercise.query.filter_by(is_active=True).all()
    if not exercises:
        flash("Hiện chưa có bài tập nào khả dụng.")
        return redirect(url_for("user_dashboard"))
    return redirect(url_for("user_workout", slug=exercises[0].slug))



@app.route("/nguoi-dung/phan-tich")
@login_required
def user_analytics():
    user = get_user_context()
    profile = UserProfile.query.filter_by(user_id=user["id"]).first()
    dashboard = calculate_user_dashboard(user["id"])
    recent_sessions = build_recent_week_sessions(user["id"])

    return render_template(
        "user_analytics.html",
        title="Phân tích luyện tập",
        user=user,
        profile=profile,
        dashboard=dashboard,
        recent_sessions=recent_sessions
    )


@app.route("/nguoi-dung/api/tong-hop-tuan")
@login_required
def weekly_summary_api():
    user = get_user_context()
    dashboard = calculate_user_dashboard(user["id"])
    recent_sessions = build_recent_week_sessions(user["id"])
    return jsonify({
        "success": True,
        "dashboard": dashboard,
        "recent_sessions": recent_sessions,
    })


@app.route("/nguoi-dung/dong-tac")
@login_required
def user_exercises():
    q = request.args.get("q", "").strip().lower()
    exercises = WorkoutExercise.query.filter_by(is_active=True).all()

    if q:
        exercises = [
            ex for ex in exercises
            if q in ex.name.lower()
            or q in (ex.muscle_group or "").lower()
            or q in (ex.description or "").lower()
        ]

    return render_template(
        "user_exercises.html",
        title="Xem động tác",
        user=get_user_context(),
        exercises=exercises,
        keyword=q
    )


@app.route("/nguoi-dung/ho-so", methods=["GET", "POST"])
@login_required
def user_profile():
    user = get_user_context()
    profile = UserProfile.query.filter_by(user_id=user["id"]).first()

    if not profile:
        profile = UserProfile(
            user_id=user["id"],
            goal="tap-nhe",
            health_note="khong-co-van-de",
            weekly_target=45,
            daily_target=6
        )
        db.session.add(profile)
        db.session.commit()

    old_goal = profile.goal
    old_health = profile.health_note
    profile.goal = normalize_goal(profile.goal)
    profile.health_note = normalize_health_note(profile.health_note)

    if not getattr(profile, "daily_target", None):
        suggested_defaults = get_recommended_rep_targets(profile)
        profile.daily_target = suggested_defaults["daily"]

    if old_goal != profile.goal or old_health != profile.health_note:
        db.session.commit()

    if request.method == "POST":
        profile.age = int(request.form.get("age", profile.age or 18))
        profile.height = float(request.form.get("height", profile.height or 170))
        profile.weight = float(request.form.get("weight", profile.weight or 60))
        profile.goal = normalize_goal(request.form.get("goal", profile.goal))
        profile.health_note = normalize_health_note(request.form.get("health_note", profile.health_note))
        profile.weekly_target = int(request.form.get("weekly_target", profile.weekly_target or 45))
        profile.daily_target = int(request.form.get("daily_target", profile.daily_target or max(1, int((profile.weekly_target or 45) / 7))))
        db.session.commit()

        flash("Đã cập nhật hồ sơ người tập.")
        return redirect(url_for("user_profile"))

    suggest, avoid, warnings = recommend_profile(profile)
    suggested_targets = get_recommended_rep_targets(profile)

    return render_template(
        "user_profile.html",
        title="Hồ sơ người tập",
        user=user,
        profile=profile,
        suggest=suggest,
        avoid=avoid,
        warnings=warnings,
        suggested_targets=suggested_targets,
        goal_options=GOAL_OPTIONS,
        health_options=HEALTH_OPTIONS
    )


@app.route("/nguoi-dung/tap/<slug>", methods=["GET", "POST"])
@login_required
def user_workout(slug):
    user = get_user_context()
    exercise = WorkoutExercise.query.filter_by(slug=slug).first_or_404()
    profile = UserProfile.query.filter_by(user_id=user["id"]).first()

    suggest, avoid, _ = recommend_profile(profile)
    warning_text = ""
    if EXERCISE_LABELS.get(slug, slug) in avoid:
        warning_text = "Thể trạng hiện tại có thể chưa phù hợp với bài tập này. Vui lòng nghỉ nếu thấy mệt."

    today_str = datetime.now().date().isoformat()
    existing_plan = WorkoutPlan.query.filter_by(
        user_id=user["id"],
        exercise_id=exercise.id,
        workout_date=today_str
    ).order_by(WorkoutPlan.created_at.desc()).first()

    recommended_target = existing_plan.rep_target if existing_plan else get_goal_daily_target(profile)
    set_count = existing_plan.set_count if existing_plan else 1
    session_date = today_str

    shared_state = get_or_create_shared_state(user["id"], slug)
    shared_state["target_rep"] = int(recommended_target)
    shared_state["exercise_slug"] = slug
    shared_state["workout_done"] = False

    if request.method == "POST":
        workout_date = request.form.get("workout_date", session_date)
        set_count = int(request.form.get("set_count", set_count))
        rep_target = int(request.form.get("rep_target", recommended_target))

        if existing_plan:
            existing_plan.workout_date = workout_date
            existing_plan.set_count = set_count
            existing_plan.rep_target = rep_target
        else:
            db.session.add(WorkoutPlan(
                user_id=user["id"],
                exercise_id=exercise.id,
                workout_date=workout_date,
                set_count=set_count,
                rep_target=rep_target,
                status="pending"
            ))
        db.session.commit()
        recommended_target = rep_target
        shared_state["target_rep"] = int(rep_target)
        flash("Đã cập nhật mục tiêu buổi tập.")
        return redirect(url_for("user_workout", slug=slug))

    criteria = ExerciseCriterion.query.filter_by(exercise_id=exercise.id).all()
    emergency_audio_file = "audio/ambulance.mp3"
    emergency_audio_exists = os.path.exists(os.path.join(BASE_DIR, "static", "audio", "ambulance.mp3"))
    today_summary = get_today_summary(user["id"], profile)

    return render_template(
        "user_workout.html",
        title="Tập luyện",
        user=user,
        exercise=exercise,
        warning_text=warning_text,
        criteria=criteria,
        emergency_audio_exists=emergency_audio_exists,
        emergency_audio_url=url_for("static", filename=emergency_audio_file),
        recommended_target=recommended_target,
        set_count=set_count,
        session_date=session_date,
        today_summary=today_summary
    )


@app.route("/nguoi-dung/api/luu-session/<slug>", methods=["POST"])
@login_required
def save_session_api(slug):
    user = get_user_context()
    exercise = WorkoutExercise.query.filter_by(slug=slug).first_or_404()

    data = request.get_json(silent=True) or {}

    session_date = data.get("session_date") or datetime.now().date().isoformat()
    total_rep = int(data.get("total_rep", 0))
    good_rep = int(data.get("good_rep", 0))
    total_error = int(data.get("total_error", 0))
    confidence_avg = float(data.get("confidence_avg", 0))
    phase_start_error = int(data.get("phase_start_error", 0))
    phase_middle_error = int(data.get("phase_middle_error", 0))
    phase_end_error = int(data.get("phase_end_error", 0))

    good_rep = normalize_display_good_rep(total_rep, good_rep)
    total_error = max(0, min(total_error, total_rep - good_rep)) if total_rep > 0 else 0

    save_workout_session_result(
        user_id=user["id"],
        exercise_id=exercise.id,
        session_date=session_date,
        total_rep=total_rep,
        good_rep=good_rep,
        total_error=total_error,
        confidence_avg=confidence_avg,
        phase_start_error=phase_start_error,
        phase_middle_error=phase_middle_error,
        phase_end_error=phase_end_error
    )

    return jsonify({
        "success": True,
        "message": "Da luu ket qua buoi tap."
    })


@app.route("/nguoi-dung/api/trang-thai-buoi-tap/<slug>")
@login_required
def live_workout_api(slug):
    user = get_user_context()
    shared_state = get_or_create_shared_state(user["id"], slug)
    profile = UserProfile.query.filter_by(user_id=user["id"]).first()
    today_summary = get_today_summary(user["id"], profile)

    return jsonify({
        "success": True,
        "exercise_slug": slug,
        "status_text": str(shared_state.get("status_text", "San sang")),
        "total_rep": int(shared_state.get("total_rep", 0) or 0),
        "good_rep": int(shared_state.get("good_rep", 0) or 0),
        "bad_rep": int(shared_state.get("bad_rep", 0) or 0),
        "display_good_rep": normalize_display_good_rep(shared_state.get("total_rep", 0), shared_state.get("good_rep", 0)),
        "display_bad_rep": max(0, int(shared_state.get("total_rep", 0) or 0) - normalize_display_good_rep(shared_state.get("total_rep", 0), shared_state.get("good_rep", 0))),
        "phase_start_error": int(shared_state.get("phase_start_error", 0) or 0),
        "phase_middle_error": int(shared_state.get("phase_middle_error", 0) or 0),
        "phase_end_error": int(shared_state.get("phase_end_error", 0) or 0),
        "target_rep": int(shared_state.get("target_rep", get_goal_daily_target(profile)) or 0),
        "today_done": int(today_summary["done_rep"]),
        "today_target": int(today_summary["daily_target"]),
        "today_remaining": int(today_summary["remaining_rep"]),
        "today_completed": bool(today_summary["completed"]),
        "today_progress_percent": float(today_summary["progress_percent"]),
    })


@app.route("/nguoi-dung/api/ket-thuc-buoi-tap/<slug>", methods=["POST"])
@login_required
def finish_workout_api(slug):
    user = get_user_context()
    exercise = WorkoutExercise.query.filter_by(slug=slug).first_or_404()
    profile = UserProfile.query.filter_by(user_id=user["id"]).first()
    shared_state = get_or_create_shared_state(user["id"], slug)
    data = request.get_json(silent=True) or {}

    session_date = data.get("session_date") or datetime.now().date().isoformat()

    total_rep = max(
        int(shared_state.get("total_rep", 0) or 0),
        int(data.get("total_rep", 0) or 0),
    )

    good_rep = max(
        int(shared_state.get("good_rep", 0) or 0),
        int(data.get("good_rep", 0) or 0),
        int(data.get("display_good_rep", 0) or 0),
    )

    phase_start_error = max(
        int(shared_state.get("phase_start_error", 0) or 0),
        int(data.get("phase_start_error", 0) or 0),
    )
    phase_middle_error = max(
        int(shared_state.get("phase_middle_error", 0) or 0),
        int(data.get("phase_middle_error", 0) or 0),
    )
    phase_end_error = max(
        int(shared_state.get("phase_end_error", 0) or 0),
        int(data.get("phase_end_error", 0) or 0),
    )

    target_rep = int(shared_state.get("target_rep", get_goal_daily_target(profile)) or 0)

    if total_rep <= 0:
        return jsonify({
            "success": False,
            "message": "Chưa ghi nhận rep nào trong buổi tập."
        }), 400

    good_rep = normalize_display_good_rep(total_rep, good_rep)
    bad_rep = max(0, total_rep - good_rep)
    total_error = bad_rep
    confidence_avg = round((good_rep / total_rep), 4) if total_rep > 0 else 0.0

    session_item = save_workout_session_result(
        user_id=user["id"],
        exercise_id=exercise.id,
        session_date=session_date,
        total_rep=total_rep,
        good_rep=good_rep,
        total_error=total_error,
        confidence_avg=confidence_avg,
        phase_start_error=phase_start_error,
        phase_middle_error=phase_middle_error,
        phase_end_error=phase_end_error
    )

    plan = WorkoutPlan.query.filter_by(
        user_id=user["id"],
        exercise_id=exercise.id,
        workout_date=session_date
    ).order_by(WorkoutPlan.created_at.desc()).first()

    status = "completed" if total_rep >= target_rep else "partial"
    if plan:
        plan.rep_target = target_rep
        plan.status = status
    else:
        db.session.add(WorkoutPlan(
            user_id=user["id"],
            exercise_id=exercise.id,
            workout_date=session_date,
            set_count=1,
            rep_target=target_rep,
            status=status
        ))

    if profile:
        if hasattr(profile, "done_count"):
            profile.done_count = (profile.done_count or 0) + good_rep
        if hasattr(profile, "total_errors"):
            profile.total_errors = (profile.total_errors or 0) + total_error
        if hasattr(profile, "calories_burned"):
            profile.calories_burned = round(
                (profile.calories_burned or 0.0) + ((exercise.calories or 0.0) * total_rep),
                2
            )

    db.session.commit()

    shared_state["workout_done"] = True
    reset_workout_runtime_state(user["id"], slug, preserve_target=True)
    today_summary = get_today_summary(user["id"], profile)

    return jsonify({
        "success": True,
        "message": "Đã kết thúc buổi tập và cập nhật tiến độ.",
        "redirect_url": url_for("user_dashboard"),
        "session_id": session_item.id,
        "today_done": today_summary["done_rep"],
        "today_target": today_summary["daily_target"],
        "today_remaining": today_summary["remaining_rep"],
        "today_completed": today_summary["completed"],
    })


@app.route("/nguoi-dung/api/trang-thai-khan-cap/<slug>")
@login_required
def emergency_status_api(slug):
    user = get_user_context()
    _, shared_state = get_or_create_emergency_state(user["id"], slug)

    safe_state = {
        "active": True if shared_state.get("active", False) else False,
        "message": str(shared_state.get("message", "")),
        "reason": str(shared_state.get("reason", "")),
        "updated_at": float(shared_state.get("updated_at", 0) or 0),
        "image_path": str(shared_state.get("image_path", "")),
        "body_angle": float(shared_state.get("body_angle", 0) or 0),
        "low_posture": True if shared_state.get("low_posture", False) else False,
    }

    return jsonify(safe_state)


@app.route("/nguoi-dung/api/reset-khan-cap/<slug>", methods=["POST"])
@login_required
def reset_emergency_api(slug):
    user = get_user_context()
    key, _ = get_or_create_emergency_state(user["id"], slug)
    EMERGENCY_STATES[key] = get_default_emergency_state()
    return jsonify({"success": True, "message": "Da reset canh bao khan cap."})


@app.route("/video/<slug>")
@login_required
def video_feed(slug):
    if not AI_READY:
        return jsonify({
            "success": False,
            "message": "Module nhận diện tư thế đang được tắt ở bản triển khai cloud."
        }), 503

    user = get_user_context()
    return Response(
        gen_frames(slug, user["id"]),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    user = get_user_context()

    total_users = User.query.filter_by(role="user").count()
    total_exercises = WorkoutExercise.query.count()
    total_plans = WorkoutPlan.query.count()
    total_sessions = WorkoutSession.query.count()

    return render_template(
        "admin_dashboard.html",
        title="Dashboard admin",
        user=user,
        total_users=total_users,
        total_exercises=total_exercises,
        total_plans=total_plans,
        total_sessions=total_sessions
    )


@app.route("/admin/bai-tap")
@admin_required
def admin_exercises():
    q = request.args.get("q", "").strip().lower()
    exercises = WorkoutExercise.query.order_by(WorkoutExercise.created_at.desc()).all()

    if q:
        exercises = [
            ex for ex in exercises
            if q in ex.name.lower()
            or q in ex.slug.lower()
            or q in (ex.muscle_group or "").lower()
        ]

    return render_template(
        "admin_exercises.html",
        title="Quản lý bài tập",
        user=get_user_context(),
        exercises=exercises,
        keyword=q
    )


@app.route("/admin/bai-tap/them", methods=["GET", "POST"])
@admin_required
def admin_add_exercise():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip()
        if not slug:
            slug = slugify(name)

        existed = WorkoutExercise.query.filter_by(slug=slug).first()
        if existed:
            flash("Slug bài tập đã tồn tại.")
            return redirect(url_for("admin_add_exercise"))

        preview_image_path = ""
        fbx_path = ""

        preview_image = request.files.get("preview_image")
        if preview_image and preview_image.filename:
            filename = secure_filename(preview_image.filename)
            save_path = os.path.join(UPLOAD_EXERCISE_DIR, filename)
            preview_image.save(save_path)
            preview_image_path = f"uploads/exercises/{filename}"

        fbx_file = request.files.get("fbx_file")
        if fbx_file and fbx_file.filename:
            filename = secure_filename(fbx_file.filename)
            save_path = os.path.join(UPLOAD_FBX_DIR, filename)
            fbx_file.save(save_path)
            fbx_path = f"uploads/fbx/{filename}"

        exercise = WorkoutExercise(
            name=name,
            slug=slug,
            muscle_group=request.form.get("muscle_group", ""),
            age_min=int(request.form.get("age_min", 15)),
            age_max=int(request.form.get("age_max", 100)),
            calories=float(request.form.get("calories", 0.1)),
            difficulty=request.form.get("difficulty", "Co ban"),
            side_mode=request.form.get("side_mode", "none"),
            description=request.form.get("description", ""),
            guide_text=request.form.get("guide_text", ""),
            suitable_for=request.form.get("suitable_for", ""),
            caution_for=request.form.get("caution_for", ""),
            preview_image=preview_image_path,
            fbx_path=fbx_path
        )
        db.session.add(exercise)
        db.session.commit()

        flash("Đã thêm bài tập mới.")
        return redirect(url_for("admin_exercise_detail", exercise_id=exercise.id))

    return render_template(
        "admin_exercise_add.html",
        title="Thêm bài tập",
        user=get_user_context()
    )


@app.route("/admin/bai-tap/<int:exercise_id>", methods=["GET", "POST"])
@admin_required
def admin_exercise_detail(exercise_id):
    exercise = WorkoutExercise.query.get_or_404(exercise_id)

    if request.method == "POST":
        exercise.name = request.form.get("name", exercise.name)
        exercise.slug = request.form.get("slug", exercise.slug) or slugify(exercise.name)
        exercise.muscle_group = request.form.get("muscle_group", exercise.muscle_group)
        exercise.age_min = int(request.form.get("age_min", exercise.age_min))
        exercise.age_max = int(request.form.get("age_max", exercise.age_max))
        exercise.calories = float(request.form.get("calories", exercise.calories))
        exercise.difficulty = request.form.get("difficulty", exercise.difficulty)
        exercise.side_mode = request.form.get("side_mode", exercise.side_mode)
        exercise.description = request.form.get("description", exercise.description)
        exercise.guide_text = request.form.get("guide_text", exercise.guide_text)
        exercise.suitable_for = request.form.get("suitable_for", exercise.suitable_for)
        exercise.caution_for = request.form.get("caution_for", exercise.caution_for)
        exercise.is_active = True if request.form.get("is_active") == "on" else False

        preview_image = request.files.get("preview_image")
        if preview_image and preview_image.filename:
            filename = secure_filename(preview_image.filename)
            save_path = os.path.join(UPLOAD_EXERCISE_DIR, filename)
            preview_image.save(save_path)
            exercise.preview_image = f"uploads/exercises/{filename}"

        fbx_file = request.files.get("fbx_file")
        if fbx_file and fbx_file.filename:
            filename = secure_filename(fbx_file.filename)
            save_path = os.path.join(UPLOAD_FBX_DIR, filename)
            fbx_file.save(save_path)
            exercise.fbx_path = f"uploads/fbx/{filename}"

        db.session.commit()
        flash("Đã cập nhật bài tập.")
        return redirect(url_for("admin_exercise_detail", exercise_id=exercise.id))

    criteria = ExerciseCriterion.query.filter_by(exercise_id=exercise.id).order_by(ExerciseCriterion.created_at.desc()).all()
    labels = ExerciseLabelImage.query.filter_by(exercise_id=exercise.id).order_by(ExerciseLabelImage.created_at.desc()).all()

    return render_template(
        "admin_exercise_detail.html",
        title="Chi tiết bài tập",
        user=get_user_context(),
        exercise=exercise,
        criteria=criteria,
        labels=labels
    )


@app.route("/admin/bai-tap/<int:exercise_id>/label-upload", methods=["POST"])
@admin_required
def admin_label_upload(exercise_id):
    exercise = WorkoutExercise.query.get_or_404(exercise_id)
    label_name = request.form.get("label_name", "").strip()
    frame_index = int(request.form.get("frame_index", 1))
    images = request.files.getlist("label_images")

    saved_count = 0
    for file in images:
        if file and file.filename:
            filename = secure_filename(file.filename)
            save_path = os.path.join(UPLOAD_LABEL_DIR, filename)
            file.save(save_path)

            label = ExerciseLabelImage(
                exercise_id=exercise.id,
                label_name=label_name,
                frame_index=frame_index,
                image_path=f"uploads/labels/{filename}"
            )
            db.session.add(label)
            saved_count += 1

    db.session.commit()
    flash(f"Đã tải lên {saved_count} ảnh label.")
    return redirect(url_for("admin_exercise_detail", exercise_id=exercise.id))


@app.route("/admin/bai-tap/<int:exercise_id>/criterion-add", methods=["POST"])
@admin_required
def admin_add_criterion(exercise_id):
    exercise = WorkoutExercise.query.get_or_404(exercise_id)

    title = request.form.get("title", "").strip()
    joint_name = request.form.get("joint_name", "").strip()
    operator = request.form.get("operator", "<=")
    angle_value = float(request.form.get("angle_value", 0))
    message_text = request.form.get("message_text", "").strip()
    advice_text = request.form.get("advice_text", "").strip()

    temp_name = f"criterion_{exercise.id}_{int(datetime.now().timestamp())}"
    audio_path = create_tts_audio(message_text or advice_text or title, temp_name)

    criterion = ExerciseCriterion(
        exercise_id=exercise.id,
        title=title,
        joint_name=joint_name,
        operator=operator,
        angle_value=angle_value,
        message_text=message_text,
        advice_text=advice_text,
        audio_path=audio_path
    )
    db.session.add(criterion)
    db.session.commit()

    flash("Đã thêm tiêu chí đánh giá và tạo âm thanh nếu khả dụng.")
    return redirect(url_for("admin_exercise_detail", exercise_id=exercise.id))


def api_unauthorized(message="Bạn cần đăng nhập để sử dụng chức năng này.", status=401):
    return jsonify({"success": False, "message": message}), status


def api_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user().get("id"):
            return api_unauthorized()
        return func(*args, **kwargs)
    return wrapper


def api_admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user.get("id"):
            return api_unauthorized()
        if user.get("role") != "admin":
            return api_unauthorized("Tài khoản hiện tại không có quyền quản trị.", 403)
        return func(*args, **kwargs)
    return wrapper


def get_json_data():
    return request.get_json(silent=True) or {}


def user_to_dict(user):
    return {
        "id": user.id,
        "fullname": user.fullname,
        "email": user.email,
        "role": user.role,
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }


def profile_to_dict(profile):
    if not profile:
        return {}
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "age": profile.age,
        "height": profile.height,
        "weight": profile.weight,
        "goal": profile.goal,
        "health_note": profile.health_note,
        "weekly_target": profile.weekly_target,
        "daily_target": profile.daily_target,
        "done_count": profile.done_count,
        "total_errors": profile.total_errors,
        "calories_burned": profile.calories_burned,
    }


def exercise_to_dict(exercise):
    return {
        "id": exercise.id,
        "name": exercise.name,
        "slug": exercise.slug,
        "muscle_group": exercise.muscle_group,
        "age_min": exercise.age_min,
        "age_max": exercise.age_max,
        "calories": exercise.calories,
        "difficulty": exercise.difficulty,
        "side_mode": exercise.side_mode,
        "description": exercise.description,
        "guide_text": exercise.guide_text,
        "suitable_for": exercise.suitable_for,
        "caution_for": exercise.caution_for,
        "preview_image": exercise.preview_image,
        "preview_video": exercise.preview_video,
        "fbx_path": exercise.fbx_path,
        "is_active": bool(exercise.is_active),
        "created_at": exercise.created_at.isoformat() if exercise.created_at else "",
    }


def plan_to_dict(plan):
    exercise = WorkoutExercise.query.get(plan.exercise_id)
    return {
        "id": plan.id,
        "user_id": plan.user_id,
        "exercise_id": plan.exercise_id,
        "exercise_name": exercise.name if exercise else "",
        "workout_date": plan.workout_date,
        "set_count": plan.set_count,
        "rep_target": plan.rep_target,
        "status": plan.status,
        "created_at": plan.created_at.isoformat() if plan.created_at else "",
    }


def session_to_dict(session_item):
    exercise = WorkoutExercise.query.get(session_item.exercise_id)
    return {
        "id": session_item.id,
        "user_id": session_item.user_id,
        "exercise_id": session_item.exercise_id,
        "exercise_name": exercise.name if exercise else "",
        "session_date": session_item.session_date,
        "total_rep": session_item.total_rep,
        "good_rep": session_item.good_rep,
        "total_error": session_item.total_error,
        "confidence_avg": session_item.confidence_avg,
        "phase_start_error": session_item.phase_start_error,
        "phase_middle_error": session_item.phase_middle_error,
        "phase_end_error": session_item.phase_end_error,
        "created_at": session_item.created_at.isoformat() if session_item.created_at else "",
    }


@app.route("/api/status")
def api_status():
    return jsonify({
        "success": True,
        "name": "FitMotion",
        "topic": "Website quản lý giáo án tập luyện",
        "database": "connected",
        "ai_module": "available" if AI_READY else "optional",
    })


@app.route("/api/auth/register", methods=["POST"])
def api_register():
    data = get_json_data()
    fullname = str(data.get("fullname", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()

    if not fullname or not email or not password:
        return jsonify({"success": False, "message": "Vui lòng nhập đủ họ tên, email và mật khẩu."}), 400

    existed = User.query.filter_by(email=email).first()
    if existed:
        return jsonify({"success": False, "message": "Email này đã tồn tại."}), 409

    user = User(
        fullname=fullname,
        email=email,
        password_hash=generate_password_hash(password),
        role="user"
    )
    db.session.add(user)
    db.session.commit()

    profile = UserProfile(user_id=user.id, goal="tap-nhe", health_note="khong-co-van-de")
    db.session.add(profile)
    db.session.commit()

    return jsonify({"success": True, "message": "Đăng ký thành công.", "user": user_to_dict(user)}), 201


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = get_json_data()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"success": False, "message": "Email hoặc mật khẩu không đúng."}), 401

    login_user(user)
    return jsonify({"success": True, "message": "Đăng nhập thành công.", "user": user_to_dict(user)})


@app.route("/api/auth/logout", methods=["POST"])
@api_login_required
def api_logout():
    logout_user()
    return jsonify({"success": True, "message": "Đã đăng xuất."})


@app.route("/api/profile", methods=["GET", "PUT"])
@api_login_required
def api_profile():
    user = current_user()
    profile = UserProfile.query.filter_by(user_id=user["id"]).first()
    if not profile:
        profile = UserProfile(user_id=user["id"], goal="tap-nhe", health_note="khong-co-van-de")
        db.session.add(profile)
        db.session.commit()

    if request.method == "PUT":
        data = get_json_data()
        if "age" in data:
            profile.age = int(data.get("age") or profile.age or 18)
        if "height" in data:
            profile.height = float(data.get("height") or profile.height or 170)
        if "weight" in data:
            profile.weight = float(data.get("weight") or profile.weight or 60)
        if "goal" in data:
            profile.goal = normalize_goal(data.get("goal"))
        if "health_note" in data:
            profile.health_note = normalize_health_note(data.get("health_note"))
        if "weekly_target" in data:
            profile.weekly_target = int(data.get("weekly_target") or profile.weekly_target or 45)
        if "daily_target" in data:
            profile.daily_target = int(data.get("daily_target") or profile.daily_target or 6)
        db.session.commit()

    return jsonify({"success": True, "profile": profile_to_dict(profile)})


@app.route("/api/exercises", methods=["GET", "POST"])
def api_exercises():
    if request.method == "POST":
        user = current_user()
        if not user.get("id"):
            return api_unauthorized()
        if user.get("role") != "admin":
            return api_unauthorized("Tài khoản hiện tại không có quyền quản trị.", 403)

        data = get_json_data()
        name = str(data.get("name", "")).strip()
        if not name:
            return jsonify({"success": False, "message": "Tên bài tập không được để trống."}), 400

        slug = str(data.get("slug", "")).strip() or slugify(name)
        if WorkoutExercise.query.filter_by(slug=slug).first():
            return jsonify({"success": False, "message": "Slug bài tập đã tồn tại."}), 409

        exercise = WorkoutExercise(
            name=name,
            slug=slug,
            muscle_group=str(data.get("muscle_group", "")).strip(),
            age_min=int(data.get("age_min") or 15),
            age_max=int(data.get("age_max") or 100),
            calories=float(data.get("calories") or 0.1),
            difficulty=str(data.get("difficulty", "co ban")).strip(),
            side_mode=str(data.get("side_mode", "none")).strip(),
            description=str(data.get("description", "")).strip(),
            guide_text=str(data.get("guide_text", "")).strip(),
            suitable_for=str(data.get("suitable_for", "")).strip(),
            caution_for=str(data.get("caution_for", "")).strip(),
            is_active=bool(data.get("is_active", True)),
        )
        db.session.add(exercise)
        db.session.commit()
        return jsonify({"success": True, "exercise": exercise_to_dict(exercise)}), 201

    q = request.args.get("q", "").strip().lower()
    muscle = request.args.get("muscle", "").strip().lower()
    items = WorkoutExercise.query.filter_by(is_active=True).order_by(WorkoutExercise.created_at.desc()).all()

    if q:
        items = [x for x in items if q in x.name.lower() or q in (x.description or "").lower() or q in (x.muscle_group or "").lower()]
    if muscle:
        items = [x for x in items if muscle in (x.muscle_group or "").lower()]

    return jsonify({"success": True, "items": [exercise_to_dict(x) for x in items]})


@app.route("/api/exercises/<int:exercise_id>", methods=["GET", "PUT", "DELETE"])
def api_exercise_detail(exercise_id):
    exercise = WorkoutExercise.query.get_or_404(exercise_id)

    if request.method in ["PUT", "DELETE"]:
        user = current_user()
        if not user.get("id"):
            return api_unauthorized()
        if user.get("role") != "admin":
            return api_unauthorized("Tài khoản hiện tại không có quyền quản trị.", 403)

    if request.method == "PUT":
        data = get_json_data()
        exercise.name = str(data.get("name", exercise.name)).strip()
        exercise.slug = str(data.get("slug", exercise.slug)).strip() or slugify(exercise.name)
        exercise.muscle_group = str(data.get("muscle_group", exercise.muscle_group or "")).strip()
        exercise.age_min = int(data.get("age_min") or exercise.age_min or 15)
        exercise.age_max = int(data.get("age_max") or exercise.age_max or 100)
        exercise.calories = float(data.get("calories") or exercise.calories or 0.1)
        exercise.difficulty = str(data.get("difficulty", exercise.difficulty or "co ban")).strip()
        exercise.side_mode = str(data.get("side_mode", exercise.side_mode or "none")).strip()
        exercise.description = str(data.get("description", exercise.description or "")).strip()
        exercise.guide_text = str(data.get("guide_text", exercise.guide_text or "")).strip()
        exercise.suitable_for = str(data.get("suitable_for", exercise.suitable_for or "")).strip()
        exercise.caution_for = str(data.get("caution_for", exercise.caution_for or "")).strip()
        if "is_active" in data:
            exercise.is_active = bool(data.get("is_active"))
        db.session.commit()
        return jsonify({"success": True, "exercise": exercise_to_dict(exercise)})

    if request.method == "DELETE":
        exercise.is_active = False
        db.session.commit()
        return jsonify({"success": True, "message": "Đã ẩn bài tập khỏi danh sách sử dụng."})

    return jsonify({"success": True, "exercise": exercise_to_dict(exercise)})


@app.route("/api/plans", methods=["GET", "POST"])
@api_login_required
def api_plans():
    user = current_user()
    if request.method == "POST":
        data = get_json_data()
        exercise_id = int(data.get("exercise_id") or 0)
        exercise = WorkoutExercise.query.get(exercise_id)
        if not exercise:
            return jsonify({"success": False, "message": "Bài tập không tồn tại."}), 404

        plan = WorkoutPlan(
            user_id=user["id"],
            exercise_id=exercise.id,
            workout_date=str(data.get("workout_date") or datetime.now().date().isoformat()),
            set_count=int(data.get("set_count") or 1),
            rep_target=int(data.get("rep_target") or 10),
            status=str(data.get("status") or "pending"),
        )
        db.session.add(plan)
        db.session.commit()
        return jsonify({"success": True, "plan": plan_to_dict(plan)}), 201

    plans = WorkoutPlan.query.filter_by(user_id=user["id"]).order_by(WorkoutPlan.created_at.desc()).all()
    return jsonify({"success": True, "items": [plan_to_dict(x) for x in plans]})


@app.route("/api/sessions", methods=["GET", "POST"])
@api_login_required
def api_sessions():
    user = current_user()
    if request.method == "POST":
        data = get_json_data()
        exercise_id = int(data.get("exercise_id") or 0)
        exercise = WorkoutExercise.query.get(exercise_id)
        if not exercise:
            return jsonify({"success": False, "message": "Bài tập không tồn tại."}), 404

        total_rep = int(data.get("total_rep") or 0)
        good_rep = int(data.get("good_rep") or 0)
        total_error = int(data.get("total_error") or max(0, total_rep - good_rep))
        session_item = WorkoutSession(
            user_id=user["id"],
            exercise_id=exercise.id,
            session_date=str(data.get("session_date") or datetime.now().date().isoformat()),
            total_rep=total_rep,
            good_rep=good_rep,
            total_error=total_error,
            confidence_avg=float(data.get("confidence_avg") or 0),
            phase_start_error=int(data.get("phase_start_error") or 0),
            phase_middle_error=int(data.get("phase_middle_error") or 0),
            phase_end_error=int(data.get("phase_end_error") or 0),
        )
        db.session.add(session_item)
        db.session.commit()
        return jsonify({"success": True, "session": session_to_dict(session_item)}), 201

    items = WorkoutSession.query.filter_by(user_id=user["id"]).order_by(WorkoutSession.created_at.desc()).all()
    return jsonify({"success": True, "items": [session_to_dict(x) for x in items]})


@app.route("/api/admin/users")
@api_admin_required
def api_admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({"success": True, "items": [user_to_dict(x) for x in users]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

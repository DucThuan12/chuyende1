from datetime import datetime
from database import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    profile = db.relationship("UserProfile", backref="user", uselist=False, cascade="all, delete-orphan")


class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    age = db.Column(db.Integer, default=18)
    height = db.Column(db.Float, default=170.0)
    weight = db.Column(db.Float, default=60.0)
    goal = db.Column(db.String(100), default="tap nhe")
    health_note = db.Column(db.String(255), default="khong co van de dac biet")

    weekly_target = db.Column(db.Integer, default=45)
    daily_target = db.Column(db.Integer, default=6)
    done_count = db.Column(db.Integer, default=0)
    total_errors = db.Column(db.Integer, default=0)
    calories_burned = db.Column(db.Float, default=0.0)


class WorkoutExercise(db.Model):
    __tablename__ = "workout_exercises"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    muscle_group = db.Column(db.String(120), default="")
    age_min = db.Column(db.Integer, default=15)
    age_max = db.Column(db.Integer, default=100)
    calories = db.Column(db.Float, default=0.1)
    difficulty = db.Column(db.String(50), default="co ban")
    side_mode = db.Column(db.String(20), default="none")

    description = db.Column(db.Text, default="")
    guide_text = db.Column(db.Text, default="")
    suitable_for = db.Column(db.Text, default="")
    caution_for = db.Column(db.Text, default="")

    preview_image = db.Column(db.String(255), default="")
    preview_video = db.Column(db.String(255), default="")
    fbx_path = db.Column(db.String(255), default="")
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    criteria = db.relationship("ExerciseCriterion", backref="exercise", cascade="all, delete-orphan")
    labels = db.relationship("ExerciseLabelImage", backref="exercise", cascade="all, delete-orphan")


class WorkoutPlan(db.Model):
    __tablename__ = "workout_plans"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("workout_exercises.id"), nullable=False)

    workout_date = db.Column(db.String(20), nullable=False)
    set_count = db.Column(db.Integer, default=1)
    rep_target = db.Column(db.Integer, default=10)
    status = db.Column(db.String(20), default="pending")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WorkoutSession(db.Model):
    __tablename__ = "workout_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("workout_exercises.id"), nullable=False)

    session_date = db.Column(
        db.String(20),
        nullable=False,
        default=lambda: datetime.now().date().isoformat()
    )

    total_rep = db.Column(db.Integer, default=0)
    good_rep = db.Column(db.Integer, default=0)
    total_error = db.Column(db.Integer, default=0)
    confidence_avg = db.Column(db.Float, default=0.0)

    phase_start_error = db.Column(db.Integer, default=0)
    phase_middle_error = db.Column(db.Integer, default=0)
    phase_end_error = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExerciseCriterion(db.Model):
    __tablename__ = "exercise_criteria"

    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("workout_exercises.id"), nullable=False)

    title = db.Column(db.String(120), nullable=False)
    joint_name = db.Column(db.String(120), default="")
    operator = db.Column(db.String(20), default="<=")
    angle_value = db.Column(db.Float, default=0.0)

    message_text = db.Column(db.Text, default="")
    advice_text = db.Column(db.Text, default="")
    audio_path = db.Column(db.String(255), default="")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExerciseLabelImage(db.Model):
    __tablename__ = "exercise_label_images"

    id = db.Column(db.Integer, primary_key=True)
    exercise_id = db.Column(db.Integer, db.ForeignKey("workout_exercises.id"), nullable=False)

    label_name = db.Column(db.String(120), nullable=False)
    frame_index = db.Column(db.Integer, default=1)
    image_path = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
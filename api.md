# Tai lieu API

He thong co cac API JSON de dap ung yeu cau RESTful API cua mon Chuyen de 1. Cac API nay duoc toi bo sung de co the test bang Postman va trinh bay trong bao cao.

## 1. Kiem tra he thong

**GET** `/api/status`

Dung de kiem tra backend dang hoat dong.

Ket qua mau:

```json
{
  "success": true,
  "name": "FitMotion",
  "topic": "Website quản lý giáo án tập luyện",
  "database": "connected",
  "ai_module": "optional"
}
```

## 2. Dang ky

**POST** `/api/auth/register`

Body:

```json
{
  "fullname": "Nguyen Van A",
  "email": "nguyenvana@gmail.com",
  "password": "123456"
}
```

## 3. Dang nhap

**POST** `/api/auth/login`

Body:

```json
{
  "email": "admin@aifitness.local",
  "password": "admin123"
}
```

## 4. Dang xuat

**POST** `/api/auth/logout`

API nay can dang nhap truoc.

## 5. Ho so ca nhan

**GET** `/api/profile`

Lay thong tin ho so ca nhan cua nguoi dung dang dang nhap.

**PUT** `/api/profile`

Body:

```json
{
  "age": 21,
  "height": 170,
  "weight": 58,
  "goal": "tang-co",
  "health_note": "the-trang-yeu",
  "weekly_target": 50,
  "daily_target": 8
}
```

## 6. Danh sach bai tap

**GET** `/api/exercises`

Lay danh sach bai tap dang hoat dong.

Co the tim kiem:

```text
/api/exercises?q=squat
/api/exercises?muscle=nguc
```

## 7. Them bai tap

**POST** `/api/exercises`

API nay can tai khoan admin.

Body:

```json
{
  "name": "Plank",
  "slug": "plank",
  "muscle_group": "Bung, lung",
  "age_min": 15,
  "age_max": 60,
  "calories": 0.08,
  "difficulty": "Co ban",
  "description": "Bai tap giu than nguoi de ren suc ben co loi.",
  "guide_text": "Chong khuyu tay, giu lung thang va khong de hong roi xuong."
}
```

## 8. Chi tiet bai tap

**GET** `/api/exercises/{id}`

Vi du:

```text
/api/exercises/1
```

## 9. Cap nhat bai tap

**PUT** `/api/exercises/{id}`

API nay can tai khoan admin.

## 10. An bai tap

**DELETE** `/api/exercises/{id}`

API nay khong xoa cung du lieu, chi chuyen bai tap sang trang thai khong hien thi de tranh mat du lieu demo.

## 11. Giao an tap luyen

**GET** `/api/plans`

Lay danh sach giao an cua nguoi dung dang dang nhap.

**POST** `/api/plans`

Body:

```json
{
  "exercise_id": 1,
  "workout_date": "2026-07-01",
  "set_count": 3,
  "rep_target": 12,
  "status": "pending"
}
```

## 12. Lich su buoi tap

**GET** `/api/sessions`

Lay lich su tap luyen cua nguoi dung.

**POST** `/api/sessions`

Body:

```json
{
  "exercise_id": 1,
  "session_date": "2026-07-01",
  "total_rep": 12,
  "good_rep": 10,
  "total_error": 2,
  "confidence_avg": 0.87
}
```

## 13. Quan ly nguoi dung

**GET** `/api/admin/users`

API nay can tai khoan admin.

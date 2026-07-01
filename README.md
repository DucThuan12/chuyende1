# Website quan ly giao an tap luyen

De tai toi thuc hien trong mon Chuyen de 1 la **Xay dung Website quan ly giao an tap luyen**. He thong duoc phat trien theo huong Web Full-Stack, co giao dien nguoi dung, backend Flask, co so du lieu va cac API dung de kiem thu bang Postman.

## Cong nghe su dung

- Backend: Flask
- Template giao dien: HTML, CSS, Jinja
- Co so du lieu: SQLite khi chay local, PostgreSQL khi deploy cloud
- ORM: SQLAlchemy
- Kiem thu API: Postman
- Cloud: Render va Supabase

## Chuc nang chinh

- Dang ky tai khoan
- Dang nhap va dang xuat
- Quan ly ho so ca nhan
- Xem danh sach bai tap/giao an
- Theo doi qua trinh tap luyen
- Dashboard nguoi dung
- Dashboard quan tri
- Quan tri vien quan ly bai tap
- Cung cap REST API de kiem thu bang Postman

## Tai khoan dung thu

Tai khoan quan tri:

```text
Email: admin@aifitness.local
Mat khau: admin123
```

Tai khoan nguoi dung:

```text
Email: 22050062@student.bdu.edu.vn
Mat khau: 123456
```

## Cach chay local

Mo terminal tai thu muc project va chay:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Sau do mo trinh duyet:

```text
http://localhost:5000
```

## Mot so API da kiem thu

```text
GET    /api/status
POST   /api/auth/login
GET    /api/profile
PUT    /api/profile
GET    /api/exercises
POST   /api/exercises
GET    /api/admin/users
```

Toi su dung Postman de kiem thu cac API tren. Cac API tra ve du lieu JSON, qua do the hien Backend/API Layer hoat dong doc lap voi giao dien.

## Ghi chu khi deploy

Khi dua len cloud, he thong su dung bien moi truong:

```text
SECRET_KEY
DATABASE_URL
```

`DATABASE_URL` se duoc lay tu database PostgreSQL tren Supabase. Tren Render, lenh build va start duoc cau hinh nhu sau:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

## Ghi chu ve module AI

Project goc co cac phan xu ly AI nhu OpenCV, YOLO Pose va webcam. Trong pham vi mon Chuyen de 1, toi tap trung vao phan Web Full-Stack, API, database, authentication, phan quyen va cloud deployment. Phan AI duoc giu nhu mot huong mo rong de phat trien tiep.

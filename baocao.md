# De cuong bao cao

Ten de tai: **Xay dung Website quan ly giao an tap luyen**

## Chuong 1. Trinh bay bai toan va co so ly thuyet

### 1.1 Mo ta bai toan thuc te

Hien nay nhu cau luyen tap the chat tai nha ngay cang pho bien, nhung nguoi tap thuong gap kho khan trong viec chon bai tap phu hop, theo doi tien do va quan ly lich tap. Vi vay, toi xay dung website quan ly giao an tap luyen nham ho tro nguoi dung tao ho so ca nhan, xem danh sach bai tap, lap ke hoach tap va theo doi ket qua tap luyen.

### 1.2 Muc tieu he thong

- Ho tro dang ky, dang nhap va quan ly ho so ca nhan.
- Cung cap danh sach bai tap va thong tin huong dan tap luyen.
- Cho phep nguoi dung quan ly giao an, lich tap va ket qua tung buoi tap.
- Cho phep admin quan ly bai tap, tieu chi danh gia va thong ke he thong.
- Xay dung he thong theo kien truc 3 tang va trien khai tren cloud.

### 1.3 Doi tuong su dung

- Nguoi dung: ca nhan co nhu cau tap luyen va theo doi qua trinh tap.
- Quan tri vien: nguoi quan ly noi dung bai tap, du lieu va thong tin he thong.

### 1.4 Yeu cau chuc nang

- Dang ky tai khoan.
- Dang nhap, dang xuat.
- Quan ly ho so ca nhan.
- Xem danh sach bai tap.
- Tim kiem bai tap.
- Tao giao an tap luyen.
- Luu ket qua buoi tap.
- Xem dashboard va lich su tap luyen.
- Admin quan ly bai tap va nguoi dung.

### 1.5 Yeu cau phi chuc nang

- Giao dien de su dung va co tinh responsive.
- Du lieu duoc luu tru bang co so du lieu quan he.
- He thong co phan quyen user va admin.
- API tra ve du lieu JSON de test bang Postman.
- He thong co the trien khai len cloud.

### 1.6 Co so ly thuyet

Noi dung can trinh bay: kien truc 3 tang, RESTful API, Authentication/Authorization, Database Design va Cloud Computing.

## Chuong 2. Phan tich va thiet ke he thong

### 2.1 Tac nhan

- Guest: xem trang chu, dang ky, dang nhap.
- User: quan ly ho so, xem bai tap, tao giao an, luu ket qua tap.
- Admin: quan ly bai tap, nguoi dung va thong ke he thong.

### 2.2 Kien truc tong the

He thong gom 3 tang:

```text
Nguoi dung
   -> Frontend Layer: HTML, CSS, Jinja Template, JavaScript
   -> Backend/API Layer: Flask route, REST API, xu ly nghiep vu
   -> Database Layer: SQLAlchemy va SQLite/PostgreSQL
```

### 2.3 Co so du lieu

Cac bang chinh:

- users
- user_profiles
- workout_exercises
- workout_plans
- workout_sessions
- exercise_criteria
- exercise_label_images

### 2.4 Luong xu ly chinh

- Luong dang ky va dang nhap.
- Luong cap nhat ho so ca nhan.
- Luong xem va tim kiem bai tap.
- Luong tao giao an tap luyen.
- Luong ghi nhan ket qua buoi tap.
- Luong admin them va cap nhat bai tap.

## Chuong 3. Xay dung va danh gia he thong

### 3.1 Frontend

Toi su dung Flask template, HTML, CSS va JavaScript de xay dung giao dien. Cac man hinh chinh gom trang chu, dang nhap, dang ky, dashboard, ho so, danh sach bai tap, man hinh luyen tap va trang quan tri.

### 3.2 Backend

Backend duoc xay dung bang Flask. He thong co cac route xu ly giao dien va nhom API JSON dung de test REST API.

### 3.3 Database

Database duoc quan ly bang SQLAlchemy. Ban local su dung SQLite, khi trien khai cloud co the doi sang PostgreSQL bang bien moi truong DATABASE_URL.

### 3.4 Authentication va Authorization

He thong su dung session authentication. Sau khi dang nhap, thong tin user duoc luu trong session. Admin duoc kiem tra quyen truoc khi vao cac trang quan tri hoac API quan tri.

### 3.5 Kiem thu

Toi kiem thu bang trinh duyet va Postman. Cac truong hop kiem thu gom dang ky, dang nhap, cap nhat ho so, xem bai tap, them giao an, them ket qua tap va truy cap trang admin.

### 3.6 Danh gia ket qua

Uu diem: he thong co day du chuc nang co ban, co phan quyen, co database ro rang, co API va co the deploy cloud.

Han che: phan nhan dien tu the bang AI phu thuoc webcam va thu vien nang, nen khi deploy cloud chi nen xem la module mo rong.

Huong phat trien: nang cap API, tach frontend rieng, tich hop AI pose estimation tren moi truong co GPU va bo sung tinh nang chia se giao an cong dong.

## Chuong 4. Trien khai he thong tren Cloud

### 4.1 Kien truc trien khai

```text
User Browser
   -> Render Web Service
   -> Flask App va REST API
   -> SQLite hoac PostgreSQL Database
```

### 4.2 Cloud platform

Toi du kien trien khai backend web len Render. Neu su dung PostgreSQL, toi cau hinh DATABASE_URL trong bien moi truong.

### 4.3 Minh chung van hanh

Khi nop bai can them cac minh chung:

- URL truy cap website.
- Anh deploy thanh cong tren Render.
- Anh dang nhap user va admin.
- Anh dashboard nguoi dung.
- Anh trang quan ly bai tap.
- Anh test API bang Postman.
- Video demo chay tren cloud.

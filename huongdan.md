# Huong dan chay project

Ten de tai toi chon cho mon Chuyen de 1 la: **Xay dung Website quan ly giao an tap luyen**.

Project nay duoc toi chinh lai tu do an FitMotion cu. Trong pham vi bai tieu luan, toi tap trung vao phan web full stack, gom giao dien, xu ly backend, REST API, co so du lieu, dang nhap, phan quyen va trien khai cloud. Phan nhan dien tu the bang camera van duoc giu trong source, nhung khi deploy cloud co the tat de he thong khong bi loi do thieu webcam hoac thu vien nang.

## Tai khoan mau

Tai khoan quan tri:

- Email: `admin@aifitness.local`
- Mat khau: `admin123`

Tai khoan nguoi dung:

- Email: `22050062@student.bdu.edu.vn`
- Mat khau: `123456`

## Chay o may ca nhan

Cai moi truong ao:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Mo trinh duyet:

```text
http://localhost:5000
```

Neu muon chay day du module AI, toi cai them cac thu vien trong file:

```bash
pip install -r yeucaudaydu.txt
```

## Chay tren cloud

Khi deploy len Render, toi dung cac file sau:

- `requirements.txt`: danh sach thu vien nhe de web chay on dinh
- `Procfile`: lenh khoi dong server bang Gunicorn
- `runtime.txt`: phien ban Python
- `env.txt`: mau bien moi truong

Bien moi truong can tao tren Render:

```text
SECRET_KEY=mot_chuoi_bi_mat_bat_ky
DATABASE_URL=duong_dan_postgresql_neu_dung_database_cloud
```

Neu chua co PostgreSQL, ung dung van co the chay SQLite de demo. Khi nop bai, toi uu tien minh chung cloud bang cac man hinh web, dang nhap, dashboard, quan ly bai tap va API.

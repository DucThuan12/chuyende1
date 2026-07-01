# Dua project len GitHub bang trinh duyet

File nay ghi lai cach toi dua source code len GitHub bang giao dien web, khong can cai GitHub Desktop.

## 1. Tao repository moi

1. Dang nhap vao GitHub.
2. Bam dau `+` o goc tren.
3. Chon `New repository`.
4. Dat ten repository ngan gon, vi du: `fitmotion` hoac `chuyende1`.
5. Co the de Public de nop link va deploy de hon.
6. Chua can chon README, vi project da co file `README.md`.
7. Bam `Create repository`.

## 2. Upload project

Sau khi tao repository, GitHub se hien trang repository trong. Toi chon:

```text
Add file -> Upload files
```

Sau do keo cac file va thu muc trong project len.

Can upload cac thanh phan chinh:

```text
app.py
auth.py
config.py
database.py
models.py
requirements.txt
Procfile
runtime.txt
api.md
baocao.md
dulieu.sql
huongdan.md
kiemthu.md
thaydoi.txt
yeucaudaydu.txt
templates/
static/
data/
modelsave/
```

Khong nen upload cac thanh phan local sau:

```text
venv/
__pycache__/
aifitness.db
instance/
.env
```

Ly do la cac file nay chi phuc vu may ca nhan hoac co the tao lai khi chay. Khi deploy cloud, he thong se dung database rieng thong qua bien `DATABASE_URL`.

## 3. Commit tren GitHub web

Sau khi keo file len, keo xuong cuoi trang va nhap noi dung commit:

```text
nop bai chuyen de 1
```

Sau do bam:

```text
Commit changes
```

Neu GitHub hien danh sach file trong repository la upload thanh cong.

## 4. Anh chup minh chung

Toi chup man hinh repository GitHub sau khi upload source code. Anh nay duoc dung lam minh chung co source code va de Render lay source khi deploy.

BEGIN TRANSACTION;
CREATE TABLE exercise_criteria (
	id INTEGER NOT NULL, 
	exercise_id INTEGER NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	joint_name VARCHAR(120), 
	operator VARCHAR(20), 
	angle_value FLOAT, 
	message_text TEXT, 
	advice_text TEXT, 
	audio_path VARCHAR(255), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(exercise_id) REFERENCES workout_exercises (id)
);
CREATE TABLE exercise_label_images (
	id INTEGER NOT NULL, 
	exercise_id INTEGER NOT NULL, 
	label_name VARCHAR(120) NOT NULL, 
	frame_index INTEGER, 
	image_path VARCHAR(255) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(exercise_id) REFERENCES workout_exercises (id)
);
CREATE TABLE user_profiles (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	age INTEGER, 
	height FLOAT, 
	weight FLOAT, 
	goal VARCHAR(100), 
	health_note VARCHAR(255), 
	weekly_target INTEGER, 
	done_count INTEGER, 
	total_errors INTEGER, 
	calories_burned FLOAT, daily_target INTEGER DEFAULT 6, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
INSERT INTO "user_profiles" VALUES(1,1,25,170.0,65.0,'tap-nhe','khong-co-van-de',45,0,0,0.0,6);
INSERT INTO "user_profiles" VALUES(2,2,21,170.0,58.0,'tang-co','the-trang-yeu',45,0,0,0.0,10);
INSERT INTO "user_profiles" VALUES(3,3,20,160.0,100.0,'giam-mo','dau-goi',60,0,0,0.0,8);
INSERT INTO "user_profiles" VALUES(4,4,18,170.0,60.0,'tang-co','dau-vai',40,7,3,1.0,15);
CREATE TABLE users (
	id INTEGER NOT NULL, 
	fullname VARCHAR(120) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);
INSERT INTO "users" VALUES(1,'Quan tri vien','admin@aifitness.local','scrypt:32768:8:1$aawa8zXOzHNVuRDL$99f9c27a887b423579c541bab1f3bb4171c56ab059898a45f5f9b34c9ef2e3c7a79815cb382802bd27d89a2a082daa2a8f4d0154b8c0881b4eee5c023c418e9a','admin','2026-04-01 06:29:16.864153');
INSERT INTO "users" VALUES(2,'Pham Duc Thuan','22050062@student.bdu.edu.vn','scrypt:32768:8:1$e1k7ULlZS2vj8And$163514d2c9f2ab7999a248cd54772edf493fea479744ca6e7f5d87f6f801c44cabc9cea32adbd274853ecebf61f8eb9c45c8533c1b3b532bf590a317f3ea7280','user','2026-04-01 06:29:17.075486');
INSERT INTO "users" VALUES(3,'Phạm Đức Thuận','thuancutenemoinguoi@gmail.com','scrypt:32768:8:1$gxStNObSs1A0C3Z8$5fab92198bead838d29b5e5ad8b45b64079dba28b739b1dc7bbe58fe1e5eb61cd26b7b895615f5b0f7e4f93cec2a4e04225c601bb438589309248ed82b68055c','user','2026-04-01 07:13:47.025583');
INSERT INTO "users" VALUES(4,'Lương Nguyễn Quốc Tuấn','22050098@student.bdu.edu.vn','scrypt:32768:8:1$ZHeiljC7vxNferTm$c842614a05649a748219cdafe7605454db5bf35df06c097bd641c19622616048b5973ea4e62fffbcfe6bb8ac3b54460e398c2d402b6bb369b1278971370a7e2b','user','2026-04-23 03:20:56.595944');
CREATE TABLE workout_exercises (
	id INTEGER NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	slug VARCHAR(80) NOT NULL, 
	muscle_group VARCHAR(120), 
	age_min INTEGER, 
	age_max INTEGER, 
	calories FLOAT, 
	difficulty VARCHAR(50), 
	side_mode VARCHAR(20), 
	description TEXT, 
	guide_text TEXT, 
	suitable_for TEXT, 
	caution_for TEXT, 
	preview_image VARCHAR(255), 
	preview_video VARCHAR(255), 
	fbx_path VARCHAR(255), 
	is_active BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (slug)
);
INSERT INTO "workout_exercises" VALUES(1,'Squat','squat','Đùi trước, mông, bắp chân',15,100,0.1,'Cơ bản','none','Bài tập thân dưới giúp phát triển sức mạnh chân và mông.','Đứng thẳng, hạ hông xuống rồi đứng lên lại.','Người mới tập, mục tiêu tăng sức bền và sức mạnh chân.','Thận trọng nếu đang đau gối hoặc đau lưng.','','','',1,'2026-04-01 06:29:17.101313');
INSERT INTO "workout_exercises" VALUES(2,'Hít đất','pushup','Ngực, vai, tay sau',16,60,0.12,'Trung bình','none','Bài tập thân trên giúp phát triển ngực, vai và tay sau.','Giữ thân thẳng, hạ người xuống rồi đẩy lên.','Người muốn tăng sức mạnh thân trên.','Thận trọng nếu đau vai hoặc cổ tay.','','','',1,'2026-04-01 06:29:17.101313');
INSERT INTO "workout_exercises" VALUES(3,'Cuốn tạ tay trái','curl-left','Tay trước',15,100,0.08,'Cơ bản','left','Bài tập đơn tay giúp phát triển bắp tay trước bên trái.','Duỗi tay xuống, gập khuỷu tay nâng tạ lên rồi hạ xuống.','Người mới tập hoặc thể trạng yếu.','Giữ khuỷu tay sát thân.','','','',1,'2026-04-01 06:29:17.101313');
INSERT INTO "workout_exercises" VALUES(4,'Cuốn tạ tay phải','curl-right','Tay trước',15,100,0.08,'Cơ bản','right','Bài tập đơn tay giúp phát triển bắp tay trước bên phải.','Duỗi tay xuống, gập khuỷu tay nâng tạ lên rồi hạ xuống.','Người mới tập hoặc thể trạng yếu.','Giữ khuỷu tay sát thân.','','','',1,'2026-04-01 06:29:17.101313');
INSERT INTO "workout_exercises" VALUES(5,'Gập bụng','gp-bng','bụng, ngực, vai ',15,100,0.1,'Cơ bản','none','','','giảm mỡ bụng','đau lưng, đau vai ','','','',1,'2026-04-24 01:31:03.082910');
INSERT INTO "workout_exercises" VALUES(6,'nâng cao đùi','nangdui','đùi, gối, cổ chân',20,90,0.2,'khó','none','','','','','','','',1,'2026-04-24 01:48:46.538678');
CREATE TABLE workout_plans (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	exercise_id INTEGER NOT NULL, 
	workout_date VARCHAR(20) NOT NULL, 
	set_count INTEGER, 
	rep_target INTEGER, 
	status VARCHAR(20), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(exercise_id) REFERENCES workout_exercises (id)
);
INSERT INTO "workout_plans" VALUES(1,2,1,'2026-04-01',1,15,'pending','2026-04-01 06:29:17.124951');
INSERT INTO "workout_plans" VALUES(2,2,2,'2026-04-02',1,15,'pending','2026-04-01 06:29:17.124951');
INSERT INTO "workout_plans" VALUES(3,2,3,'2026-04-03',1,15,'pending','2026-04-01 06:29:17.124951');
INSERT INTO "workout_plans" VALUES(4,3,1,'2026-04-23',1,8,'pending','2026-04-22 23:17:25.951286');
INSERT INTO "workout_plans" VALUES(5,4,1,'2026-04-23',1,8,'completed','2026-04-23 05:10:17.857543');
INSERT INTO "workout_plans" VALUES(6,4,4,'2026-04-23',1,15,'pending','2026-04-23 13:37:18.789972');
INSERT INTO "workout_plans" VALUES(7,2,1,'2026-04-24',1,10,'pending','2026-04-24 01:42:03.462772');
INSERT INTO "workout_plans" VALUES(8,2,2,'2026-04-24',1,10,'pending','2026-04-24 01:42:57.897216');
INSERT INTO "workout_plans" VALUES(9,2,3,'2026-04-24',1,10,'pending','2026-04-24 01:44:06.930110');
INSERT INTO "workout_plans" VALUES(10,3,1,'2026-04-24',1,8,'pending','2026-04-24 02:31:32.468648');
CREATE TABLE workout_sessions (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	exercise_id INTEGER NOT NULL, 
	total_rep INTEGER, 
	good_rep INTEGER, 
	total_error INTEGER, 
	confidence_avg FLOAT, 
	phase_start_error INTEGER, 
	phase_middle_error INTEGER, 
	phase_end_error INTEGER, 
	created_at DATETIME, session_date TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(exercise_id) REFERENCES workout_exercises (id)
);
INSERT INTO "workout_sessions" VALUES(1,2,1,12,10,2,0.87,1,1,0,'2026-04-01 07:05:47.161008','2026-04-01');
INSERT INTO "workout_sessions" VALUES(2,4,1,10,7,3,0.7,0,0,0,'2026-04-23 05:10:17.842567','2026-04-23');
COMMIT;

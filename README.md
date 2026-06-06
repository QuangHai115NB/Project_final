# CV Review

CV Review là hệ thống web hỗ trợ phân tích CV và so khớp CV với mô tả công việc (JD). Ứng dụng đọc nội dung từ CV/JD, chuẩn hóa văn bản, trích xuất các section quan trọng, chấm điểm theo nhiều tiêu chí và tạo báo cáo giải thích vì sao CV phù hợp hoặc chưa phù hợp với JD.

Dự án phù hợp cho bài toán đồ án tốt nghiệp về xử lý ngôn ngữ tự nhiên, hệ thống gợi ý cải thiện CV, so khớp kỹ năng và đánh giá độ phù hợp giữa ứng viên với vị trí tuyển dụng.

## Chức Năng Chính

- Đăng ký, đăng nhập, xác thực email bằng OTP.
- Quản lý phiên đăng nhập bằng JWT access token và refresh token.
- Upload CV và JD, hỗ trợ đọc nội dung từ PDF/TXT.
- Phân tích section CV như Summary, Skills, Experience, Projects, Education, Certifications.
- So khớp CV với JD theo nhiều đầu điểm: kỹ năng, keyword, semantic, kinh nghiệm, chất lượng bằng chứng.
- Tạo báo cáo giải thích điểm số, kỹ năng thiếu, keyword thiếu, yêu cầu JD chưa được CV chứng minh.
- Gợi ý cách sửa CV và ví dụ viết lại bullet.
- Lưu lịch sử match, xem chi tiết report, xóa report.
- Xuất báo cáo ra DOCX và PDF.
- Dashboard admin để thống kê user, CV, JD, lượt match theo ngày/tháng/năm.
- Hỗ trợ giao diện tiếng Việt và tiếng Anh.
- Quản lý quota match theo ngày, tính theo timezone ứng dụng.

## Công Nghệ Sử Dụng

Backend:

- Flask
- SQLAlchemy
- Alembic
- PyJWT
- bcrypt
- Redis
- pdfplumber
- scikit-learn
- sentence-transformers
- python-docx
- reportlab

Frontend:

- React
- Vite
- React Router
- Axios
- Tailwind CSS
- lucide-react

Cơ sở dữ liệu và lưu trữ:

- SQLite cho môi trường local
- PostgreSQL cho môi trường production nếu cấu hình `DATABASE_URL`
- Supabase Storage nếu cấu hình lưu trữ ngoài

## Kiến Trúc Tổng Quan

```text
CV/JD upload
    |
    v
Text extraction
    |
    v
Text cleaning + section parsing
    |
    v
Rule checks + JD matching pipeline
    |
    v
Scorecard + explanations
    |
    v
Report JSON + DOCX/PDF export
```

Backend chia theo các tầng chính:

- `src/api`: khai báo route Flask.
- `src/core`: auth dependency, JWT, error handling, rate limiting.
- `src/db`: model, database session, repository.
- `src/services`: xử lý nghiệp vụ chính.
- `src/services/documents`: nghiệp vụ upload, list, delete CV/JD/match.
- `src/services/auth`: nghiệp vụ tài khoản, OTP, profile, token.
- `src/services/jd_matching`: thuật toán so khớp CV-JD đã được tách theo từng đầu điểm.
- `frontend/src`: giao diện React.

## Cấu Trúc Thư Mục

```text
.
├── app.py
├── requirements.txt
├── alembic.ini
├── cv_review.db
├── src/
│   ├── api/
│   │   ├── auth_routes.py
│   │   ├── admin_routes.py
│   │   ├── billing_routes.py
│   │   ├── document_routes.py
│   │   └── routes/
│   ├── core/
│   ├── data/
│   ├── db/
│   └── services/
│       ├── auth/
│       ├── documents/
│       ├── jd_matching/
│       │   ├── pipeline.py
│       │   ├── skills_score.py
│       │   ├── keyword_score.py
│       │   ├── experience_score.py
│       │   ├── semantic_score.py
│       │   └── evidence_score.py
│       ├── jd_matcher.py
│       ├── report_builder.py
│       ├── report_docx_generator.py
│       ├── report_pdf_generator.py
│       ├── scoring.py
│       ├── semantic_matcher.py
│       └── time_service.py
├── frontend/
│   ├── package.json
│   └── src/
├── migrations/
├── uploads/
├── test_api_routes.py
├── test_backend_regressions.py
└── test_matching_engine.py
```

## Thuật Toán So Khớp CV-JD

Pipeline chính nằm ở `src/services/jd_matching/pipeline.py`. File `src/services/jd_matcher.py` chỉ là facade để giữ tương thích với import cũ.

Quy trình xử lý:

1. Làm sạch văn bản CV và JD.
2. Parse CV thành các section như Skills, Experience, Projects, Education.
3. Lọc JD để bỏ phần noise như benefits, địa chỉ, giới thiệu công ty.
4. Trích xuất kỹ năng từ CV và JD bằng taxonomy.
5. Chấm từng đầu điểm.
6. Tổng hợp score, issue, suggestion và rewrite example.
7. Build report cuối cùng để frontend hiển thị và xuất file.

Các đầu điểm chính:

- `skill_score`: đo mức bao phủ kỹ năng required/preferred trong JD.
- `keyword_score`: dùng TF-IDF và keyword overlap để kiểm tra từ khóa kỹ thuật quan trọng.
- `semantic_score`: so khớp ngữ nghĩa giữa Experience/Projects của CV với yêu cầu JD. Khi model embedding khả dụng, hệ thống dùng `all-MiniLM-L6-v2`; khi không khả dụng sẽ fallback về TF-IDF.
- `experience_score`: tính theo tỷ lệ số tháng kinh nghiệm CV so với số tháng JD yêu cầu. Nếu JD không ghi thời lượng kinh nghiệm thì không trừ điểm ở đầu này.
- `jd_structure_score`: kiểm tra bằng chứng trong Experience/Projects, ví dụ skill có xuất hiện trong trải nghiệm thực tế không và bullet có số liệu đo lường không.
- `section_score`: lấy từ rule checker, đánh giá cấu trúc CV và các section bắt buộc.

Điểm tổng được tính trong `src/services/scoring.py` bằng weighted scorecard. Nếu semantic model không khả dụng, trọng số semantic được phân bổ lại cho các đầu điểm còn hoạt động.

## Rule Về Bằng Cấp

Hệ thống không coi các dòng chỉ nêu bằng cấp chung như `Bachelor's degree`, `cử nhân`, `kỹ sư`, `đang học ngành...` là bằng chứng bắt buộc cần match trong CV. Các dòng này được lọc khỏi nhóm yêu cầu cần chứng minh nếu chúng không chứa kỹ năng hoặc hành động cụ thể.

Mục tiêu là tránh trừ điểm sai khi JD chỉ ghi yêu cầu bằng cấp chung nhưng CV tập trung vào kỹ năng và kinh nghiệm thực tế.

## API Chính

Auth:

- `POST /api/auth/register`
- `POST /api/auth/verify-email`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `POST /api/auth/change-password`
- `GET /api/auth/me`
- `GET /api/auth/quota`
- `PUT /api/auth/profile`
- `POST /api/auth/avatar`
- `DELETE /api/auth/avatar`

Documents và matching:

- `POST /api/cvs/upload`
- `GET /api/cvs`
- `DELETE /api/cvs/delete/<cv_id>`
- `POST /api/jds/upload`
- `GET /api/jds`
- `DELETE /api/jds/delete/<jd_id>`
- `POST /api/matches`
- `GET /api/matches`
- `GET /api/matches/<match_id>`
- `PUT /api/matches/<match_id>/review`
- `DELETE /api/matches/<match_id>`
- `GET /api/matches/download/<match_id>`
- `GET /api/matches/download-pdf/<match_id>`

Admin:

- `GET /api/admin/overview`
- `GET /api/admin/users`
- `GET /api/admin/users/<user_id>`
- `PUT /api/admin/users/<user_id>`
- `GET /api/admin/matches`
- `GET /api/admin/matches/<match_id>`
- `GET /api/admin/payment-info`
- `POST /api/admin/payment-qr`
- `DELETE /api/admin/payment-qr`

## Cấu Hình Môi Trường

Tạo file `.env` ở root project. Một cấu hình local tối thiểu:

```env
FLASK_DEBUG=true
SECRET_KEY=dev-secret
JWT_SECRET_KEY=dev-jwt-secret
DATABASE_URL=sqlite:///cv_review.db
UPLOAD_DIR=uploads
APP_TIMEZONE=Asia/Bangkok
```

Các tính năng OTP, rate limit, billing hoặc storage ngoài cần thêm cấu hình SMTP, Redis, Supabase tùy môi trường triển khai.

Không commit credential thật lên repository.

## Cài Đặt Backend

```powershell
cd D:\cv-review
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend mặc định chạy tại:

```text
http://localhost:5000
```

## Cài Đặt Frontend

```powershell
cd D:\cv-review\frontend
npm install
npm run dev
```

Frontend mặc định chạy tại:

```text
http://localhost:5173
```

## Kiểm Thử

Chạy test thuật toán matching:

```powershell
cd D:\cv-review
.\.venv\Scripts\activate
python test_matching_engine.py
```

Chạy test API và regression:

```powershell
python test_api_routes.py
python test_backend_regressions.py
```

Build frontend:

```powershell
cd D:\cv-review\frontend
npm.cmd run build
```

## Luồng Sử Dụng

1. Người dùng đăng ký tài khoản và xác thực email.
2. Người dùng upload CV.
3. Người dùng upload JD.
4. Người dùng chọn CV và JD để tạo match report.
5. Backend đọc text, parse section, chạy rule checker và JD matching pipeline.
6. Hệ thống trả về report gồm điểm tổng, điểm thành phần, giải thích và gợi ý sửa.
7. Người dùng xem report trên giao diện hoặc tải DOCX/PDF.
8. Admin theo dõi thống kê hệ thống theo khoảng ngày, tháng hoặc năm.

## Trạng Thái Hiện Tại

Các phần chính đã có:

- Backend Flask API.
- Frontend React dashboard.
- Matching engine nhiều đầu điểm.
- Semantic matching với model `all-MiniLM-L6-v2` và fallback TF-IDF.
- Rule lọc bằng cấp chung để tránh trừ điểm sai.
- Thống kê admin theo ngày/tháng/năm.
- Chuẩn hóa ngày giờ theo timezone ứng dụng.
- Export DOCX/PDF.


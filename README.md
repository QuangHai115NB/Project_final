Cách chạy code Flask trong venv

  # 1. Di chuyển vào thư mục project
  cd D:\cv-review
                                                                                                                             # 2. Kích hoạt virtual environment
  # Windows (cmd/powershell):
  .venv\Scripts\activate

  # Hoặc nếu dùng Git Bash (Windows):
  source .venv/Scripts/activate

  # 3. Cài requirements (nếu chưa hoặc mới sync)
  pip install -r requirements.txt

  # 4. Chạy ứng dụng
  python app.py

  ---
  🔄 Cách nhanh hơn — Tạo shortcut 1 lệnh

  # Chạy 1 lệnh duy nhất (không cần activate trước)
.venv\Scripts\activate && pip install -r requirements.txt && python app.py
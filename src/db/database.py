import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

# Tải thông tin từ file .env
load_dotenv()

# Lấy chuỗi kết nối từ .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Tạo kết nối với PostgreSQL Supabase
engine = create_engine(DATABASE_URL, echo=True, future=True)

# Tạo SessionLocal để thao tác với database
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Tạo cơ sở dữ liệu base class cho các bảng
Base = declarative_base()

def init_db():
    """
    Kiểm tra kết nối và tạo bảng nếu chưa có.
    """
    from src.db import models  # noqa: F401

    try:
        # Kiểm tra kết nối bằng câu lệnh SQL SELECT 1
        with engine.connect() as connection:
            result = connection.execute(text("SELECT current_database();"))
            print(f"Database connection successful! Connected to {result.fetchone()[0]}")
    except OperationalError as e:
        print(f"Error: Unable to connect to the database - {e}")
        raise e

    # Tạo tất cả bảng trong database nếu chưa có
    Base.metadata.create_all(bind=engine)
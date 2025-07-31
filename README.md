# Tipiṭaka Việt AI 🙏

Trợ lý AI chuyên về giáo lý Phật giáo Theravāda (Nam tông), hỗ trợ tìm hiểu kinh điển và phương pháp tu tập từ Tam Tạng Pali.

## Tổng quan

Tipiṭaka Việt AI là một ứng dụng trợ lý thông minh được xây dựng để:

- **Tìm kiếm và trích dẫn** kinh điển Pali chính xác
- **Hướng dẫn thực hành** theo truyền thống Theravāda
- **Giải thích giáo pháp** dựa trên Tam Tạng Pali
- **Hỗ trợ tu tập** với phương pháp cụ thể

## Tính năng chính

### 🔍 Tìm kiếm kinh điển
- Tìm kiếm văn bản trong Tam Tạng Pali
- Trích dẫn chính xác từ các bộ kinh
- Hỗ trợ tìm kiếm ngữ nghĩa

### 💬 Trò chuyện thông minh
- Chat bot thân thiện với kiến thức Phật pháp sâu rộng
- Trả lời dựa trên ngữ cảnh kinh điển
- Không đưa ra ý kiến cá nhân, chỉ dựa trên kinh điển

### 📚 Quản lý dữ liệu
- Lưu trữ và quản lý cuộc trò chuyện
- Phản hồi và đánh giá từ người dùng
- Xác thực API key

## Kiến trúc hệ thống

### Backend Services
- **FastAPI**: Web framework chính
- **POE Integration**: Tích hợp với nền tảng Poe
- **MongoDB**: Lưu trữ vector embeddings
- **PostgreSQL**: Lưu trữ dữ liệu quan hệ
- **OpenAI Embeddings**: Mô hình nhúng văn bản

### Cơ sở dữ liệu
- **MongoDB Atlas**: Vector search cho kinh điển
- **PostgreSQL**: Quản lý user, cuộc trò chuyện, phản hồi

## Cài đặt

### Yêu cầu hệ thống
- Python 3.8+
- Docker & Docker Compose
- MongoDB Atlas hoặc Local MongoDB
- PostgreSQL

### 1. Clone repository
```bash
git clone https://github.com/your-username/tipitaka-viet-ai.git
cd tipitaka-viet-ai
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Cấu hình biến môi trường
Tạo file `.env` với nội dung:

```env
# Bot Configuration
BOT_NAME=TipitakaViet
ADMIN_KEY=your_admin_key_here
POE_ACCESS_KEY=your_poe_access_key_here

# Database Connections
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/tipitaka
MONGODB_SEARCH_INDEX_CREATED=FALSE
POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/tipitaka

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
TOGETHER_API_KEY=your_together_api_key_here

# Import Settings (Optional)
IMPORT__API_KEY=your_import_api_key
IMPORT__BASE_URL=https://api.example.com
IMPORT__EXTRA_PARAMS={}
```

### 4. Khởi động cơ sở dữ liệu
```bash
# Khởi động MongoDB và PostgreSQL containers
chmod +x bin/db.sh
./bin/db.sh
```

### 5. Chạy migration
```bash
alembic upgrade head
```

### 6. Khởi động ứng dụng
```bash
python main.py
```

## Sử dụng

### Chat Commands

#### Trò chuyện cơ bản
```python
python cmd/chat.py
```

#### Import dữ liệu kinh điển
```python
python cmd/import.py
```

#### Rewrite và cải thiện nội dung
```python
python cmd/rewrite.py
```

#### Lưu trữ cuộc trò chuyện
```python
python cmd/store_chat.py
```

#### Visualize dữ liệu
```python
python cmd/visualize.py
```

### API Endpoints

- `GET /health` - Kiểm tra trạng thái hệ thống
- `POST /api/chat` - Chat với AI
- `POST /api/feedback` - Gửi phản hồi
- `GET /api/conversations` - Lấy danh sách cuộc trò chuyện

## Cấu trúc thư mục

```
tipitaka-viet-ai/
├── bin/                    # Scripts tiện ích
├── cmd/                    # Command line tools
│   ├── chat.py            # Chat interface
│   ├── import.py          # Import kinh điển
│   ├── rewrite.py         # Content rewriting
│   └── store_chat.py      # Conversation storage
├── db/                     # Database modules
│   ├── mongoatlas.py      # MongoDB operations
│   ├── postgres.py        # PostgreSQL operations
│   └── postgres_models/   # SQLAlchemy models
├── service/               # Core services
│   ├── api.py            # FastAPI routes
│   ├── auth.py           # Authentication
│   ├── bot.py            # Main bot logic
│   └── health_check.py   # Health monitoring
├── templates/             # Templates
│   └── prompts.yaml      # System prompts
├── alembic/              # Database migrations
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── README.md            # Tài liệu này
```

## Development

### Chạy tests
```bash
pytest
```

### Database Migration
```bash
# Tạo migration mới
alembic revision --autogenerate -m "description"

# Áp dụng migration
alembic upgrade head

# Quay lại migration trước
alembic downgrade -1
```

### Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py
```

## Docker Deployment

### Build image
```bash
docker build -t tipitaka-viet-ai .
```

### Deploy với Docker Compose
```bash
docker-compose up -d
```

### Fly.io Deployment
```bash
flyctl deploy
```

## Đóng góp

1. Fork repository
2. Tạo feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Tạo Pull Request

## Bảo mật

- Tất cả API keys được lưu trữ trong biến môi trường
- Xác thực bằng API key cho các endpoint nhạy cảm
- Không commit secrets vào repository
- Sử dụng HTTPS cho production

## Giấy phép

[GNU AFFERO GENERAL PUBLIC LICENSE](LICENSE)

## Liên hệ

- Issues: [GitHub Issues](https://github.com/ducthotran2010/tipitaka-viet-ai/issues)

---

🙏 **Namo tassa bhagavato arahato sammāsambuddhassa**

*Cầu mong Tipiṭaka Việt AI có thể hỗ trợ tốt cho việc tu học Phật pháp của các thiện hữu.*

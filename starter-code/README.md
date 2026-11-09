# Starter Code — Lab #4

> Dành cho học viên VinUni AI Product Labs.

## Cách Sử Dụng

1. **Cài đặt môi trường:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Các phần đã hoàn thiện theo student guide:**
   - `tools.py`: đọc/lọc catalog, tạo và lưu nối tiếp ticket, hai JSON Schemas.
   - `template.py`: System Prompt đủ 5 phần, baseline mock minh họa hallucination,
     intent detection độc lập và agent loop có trace, max-iterations guard.

3. **Chạy thử:**
   ```bash
   python3 template.py
   ```

4. **Kiểm thử autograder:**
   ```bash
   python3 -m pytest ../autograder/test_agent.py -v
   ```

## Lưu Ý
- Code chạy ở chế độ **Mock Simulator** mặc định (không cần API key).
- Chưa tích hợp Live API; đặt `GEMINI_API_KEY` không thay đổi chế độ chạy.
- `SYSTEM_PROMPT` và schemas phục vụ thiết kế theo lab; bộ mô phỏng dùng luật
  Python, không gửi prompt tới mô hình. Giá trả lời lấy từ dữ liệu mẫu của lab.
- `iterations`: một tool = một vòng; câu trả lời được tổng hợp ngay sau tool cuối.
  FAQ không gọi tool vẫn tính một vòng. Hai tool cần hai vòng và chạy tuần tự.
- Thiếu tên khi báo sự cố: hỏi bổ sung, chưa tạo ticket. Mô tả ticket giữ nguyên
  câu người dùng để không làm mất chi tiết; không bịa thời hạn bảo hành cho FAQ.
- `conftest.py` dùng bản sao dữ liệu cho mỗi test, giữ nguyên file ticket mẫu.
- Từ thư mục Day 4, chạy cả autograder và các kiểm tra bổ sung:
  ```powershell
  .\.venv\Scripts\python.exe -m pytest autograder/test_agent.py tests -v
  ```
  Nếu chưa có `.venv`, có thể dùng Python đã cài `requirements.txt`.

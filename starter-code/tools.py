import json
import os
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "raw-data")

# ---------------------------------------------------------------------------
# Tool #1: search_product_catalog
# ---------------------------------------------------------------------------

def search_product_catalog(category: str, max_price: int = 999999999999) -> List[Dict[str, Any]]:
    """
    Tra cứu sản phẩm/dịch vụ Vingroup theo danh mục và giá tối đa.
    
    Args:
        category: Loại sản phẩm ('xe_dien' hoặc 'du_lich').
        max_price: Giá tối đa (VNĐ). Mặc định không giới hạn.
    
    Returns:
        Danh sách sản phẩm phù hợp điều kiện.
    """
    catalog_file = os.path.join(RAW_DATA_DIR, "product_catalog.json")
    if not isinstance(category, str) or category.strip().lower() not in {"xe_dien", "du_lich"}:
        return [{"error": "Danh mục phải là xe_dien hoặc du_lich."}]
    if type(max_price) is not int or max_price < 0:
        return [{"error": "Giá tối đa phải là số nguyên không âm (VNĐ)."}]
    try:
        with open(catalog_file, "r", encoding="utf-8") as f:
            products = json.load(f)
        if not isinstance(products, list):
            raise ValueError("Catalog phải là một danh sách.")
        return [p for p in products
                if p["category"].lower() == category.strip().lower()
                and p["price_vnd"] <= max_price]
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return [{"error": f"Không đọc được danh mục sản phẩm: {exc}"}]


# ---------------------------------------------------------------------------
# Tool #2: submit_support_ticket
# ---------------------------------------------------------------------------

def submit_support_ticket(
    customer_name: str,
    issue_description: str,
    priority: str = "medium"
) -> Dict[str, Any]:
    """
    Ghi nhận yêu cầu hỗ trợ của khách hàng vào hệ thống ticket.
    
    Args:
        customer_name: Tên khách hàng.
        issue_description: Mô tả vấn đề cần hỗ trợ.
        priority: Mức độ ưu tiên ('low', 'medium', 'high'). Mặc định 'medium'.
    
    Returns:
        Thông tin ticket vừa tạo bao gồm ticket_id, status.
    """
    tickets_file = os.path.join(RAW_DATA_DIR, "support_tickets.json")
    if not isinstance(customer_name, str) or not customer_name.strip():
        return {"error": "Vui lòng cung cấp tên khách hàng."}
    if not isinstance(issue_description, str) or not issue_description.strip():
        return {"error": "Vui lòng mô tả vấn đề cần hỗ trợ."}
    if not isinstance(priority, str) or priority.lower() not in {"low", "medium", "high"}:
        return {"error": "Mức ưu tiên phải là low, medium hoặc high."}
    try:
        existing_tickets = []
        if os.path.exists(tickets_file):
            with open(tickets_file, "r", encoding="utf-8") as f:
                existing_tickets = json.load(f)
        if not isinstance(existing_tickets, list):
            raise ValueError("Dữ liệu ticket phải là một danh sách.")
        now = datetime.now(timezone(timedelta(hours=7)))
        sequences = [int(t["ticket_id"].rsplit("-", 1)[-1]) for t in existing_tickets]
        seq = max([len(existing_tickets)] + sequences) + 1
        ticket_id = f"TK-{now:%Y%m%d}-{seq:03d}"
        new_ticket = {
            "ticket_id": ticket_id,
            "customer_name": customer_name.strip(),
            "issue_description": issue_description.strip(),
            "priority": priority.lower(),
            "status": "open",
            "created_at": now.isoformat(),
            "category": "general",
        }
        existing_tickets.append(new_ticket)
        with open(tickets_file, "w", encoding="utf-8") as f:
            json.dump(existing_tickets, f, indent=2, ensure_ascii=False)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return {"error": f"Không lưu được ticket hỗ trợ: {exc}"}
    return {
        "ticket_id": ticket_id,
        "customer_name": new_ticket["customer_name"],
        "priority": new_ticket["priority"],
        "status": "open",
        "message": f"Ticket {ticket_id} đã được tạo thành công.",
    }


# ---------------------------------------------------------------------------
# TOOL_DEFINITIONS — JSON Schemas mô tả cho LLM
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "search_product_catalog",
        "description": "Tra cứu sản phẩm/dịch vụ Vingroup theo danh mục và giá tối đa.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Danh mục xe điện VinFast hoặc du lịch Vinpearl.",
                    "enum": ["xe_dien", "du_lich"],
                },
                "max_price": {
                    "type": "integer", "minimum": 0,
                    "description": "Giá tối đa tính bằng VNĐ; bỏ qua nếu không giới hạn.",
                },
            },
            "required": ["category"],
            "additionalProperties": False,
        },
    },
    {
        "name": "submit_support_ticket",
        "description": "Tạo và lưu ticket khi khách báo sự cố hoặc yêu cầu ghi nhận phản hồi.",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string", "minLength": 1, "description": "Tên do khách hàng cung cấp."},
                "issue_description": {"type": "string", "minLength": 1, "description": "Vấn đề do khách hàng cung cấp."},
                "priority": {
                    "type": "string", "enum": ["low", "medium", "high"], "default": "medium",
                    "description": "high khi khẩn cấp/nghiêm trọng; mặc định medium.",
                },
            },
            "required": ["customer_name", "issue_description"],
            "additionalProperties": False,
        },
    },
]


# ---------------------------------------------------------------------------
# TOOL_MAP — Ánh xạ tên tool → hàm thực thi
# ---------------------------------------------------------------------------

TOOL_MAP = {
    "search_product_catalog": search_product_catalog,
    "submit_support_ticket": submit_support_ticket
}

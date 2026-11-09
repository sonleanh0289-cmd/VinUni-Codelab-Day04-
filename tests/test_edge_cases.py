"""Kiểm tra các milestone/edge case chưa được bao phủ bởi 8 test gốc."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import tools
from template import ToolCallingAgent


CASES = json.loads((Path(__file__).resolve().parents[1] / "raw-data" / "customer_queries.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_customer_query_tool_routing(case, isolated_raw_data):
    before = json.loads((isolated_raw_data / "support_tickets.json").read_text(encoding="utf-8"))
    result = ToolCallingAgent().run(case["query"])
    steps = [step for step in result["trace"] if step["action"] in tools.TOOL_MAP]
    assert result["status"] == "completed"
    assert [step["action"] for step in steps] == case["expected_tools"]
    for step in steps:
        if step["action"] == "search_product_catalog":
            expected = case.get("expected_args_catalog", case.get("expected_args"))
            assert step["arguments"] == expected
        else:
            expected = case.get("expected_args_ticket", case.get("expected_args"))
            assert step["arguments"]["customer_name"] == expected["customer_name"]
            assert step["arguments"]["priority"] == expected["priority"]
            # Giữ nguyên lời khách, không tóm tắt mất chi tiết sự cố.
            assert step["arguments"]["issue_description"] == case["query"]
            assert step["observation"]["ticket_id"] in result["answer"]
    after = json.loads((isolated_raw_data / "support_tickets.json").read_text(encoding="utf-8"))
    assert after[:len(before)] == before
    assert len(after) == len(before) + case["expected_tools"].count("submit_support_ticket")
    if case["id"] == "TC03":
        assert "Vinpearl Resort & Spa Nha Trang" in result["answer"]
        assert "Vinpearl Discovery Phú Quốc" in result["answer"]
        assert "Phạm Thị Dung" in result["answer"]


def test_iteration_guard_does_not_submit_remaining_ticket(isolated_raw_data):
    ticket_file = isolated_raw_data / "support_tickets.json"
    before = ticket_file.read_bytes()
    result = ToolCallingAgent(max_iterations=1).run(CASES[2]["query"])
    assert result["status"] == "max_iterations_reached"
    assert result["iterations"] == 1
    assert [step["action"] for step in result["trace"]] == ["search_product_catalog"]
    assert "Vinpearl" in result["answer"]
    assert "Đã tạo ticket" not in result["answer"]
    assert ticket_file.read_bytes() == before


def test_zero_iterations_no_side_effects(isolated_raw_data):
    before = (isolated_raw_data / "support_tickets.json").read_bytes()
    result = ToolCallingAgent(max_iterations=0).run(CASES[1]["query"])
    assert result["status"] == "max_iterations_reached"
    assert result["iterations"] == 0
    assert result["trace"] == []
    assert (isolated_raw_data / "support_tickets.json").read_bytes() == before


def test_missing_name_asks_without_writing(isolated_raw_data):
    before = (isolated_raw_data / "support_tickets.json").read_bytes()
    result = ToolCallingAgent().run("Xe VF 8 của tôi bị lỗi ADAS, cần xử lý gấp.")
    assert "cung cấp tên" in result["answer"]
    assert not any(s["action"] == "submit_support_ticket" for s in result["trace"])
    assert (isolated_raw_data / "support_tickets.json").read_bytes() == before


def test_trace_reset_between_runs():
    agent = ToolCallingAgent()
    first = agent.run(CASES[0]["query"])
    second = agent.run(CASES[3]["query"])
    assert first["trace"][0]["action"] == "search_product_catalog"
    assert [step["action"] for step in second["trace"]] == ["final_answer"]
    assert "VF 5" not in second["answer"]


@pytest.mark.parametrize("budget", ["0,6 tỷ", "0.6 tỷ", "600.000.000 VNĐ", "600 triệu"])
def test_budget_units(budget):
    result = ToolCallingAgent().run(f"Xem xe điện VinFast giá dưới {budget}")
    assert result["trace"][0]["arguments"]["max_price"] == 600000000
    assert "VF 3" in result["answer"]
    assert "VF 8" not in result["answer"]


def test_catalog_from_different_working_directory(tmp_path, monkeypatch):
    # Khôi phục đường dẫn thực để kiểm tra cách tính đường dẫn theo __file__.
    monkeypatch.setattr(tools, "RAW_DATA_DIR", str(Path(tools.__file__).resolve().parent.parent / "raw-data"))
    monkeypatch.chdir(tmp_path)
    assert len(tools.search_product_catalog("XE_DIEN", 600000000)) == 2


def test_ticket_creation_from_missing_file(isolated_raw_data):
    ticket_file = isolated_raw_data / "support_tickets.json"
    ticket_file.unlink()
    first = tools.submit_support_ticket("Nguyễn An", "Xe VF 3 lỗi pin", "HIGH")
    second = tools.submit_support_ticket("Trần Bình", "Phòng Vinpearl bị ẩm")
    saved = json.loads(ticket_file.read_text(encoding="utf-8"))
    assert len(saved) == 2
    assert first["ticket_id"] != second["ticket_id"]
    assert first["priority"] == "high"
    assert saved[0]["customer_name"] == "Nguyễn An"
    assert datetime.fromisoformat(saved[0]["created_at"]).utcoffset() == timedelta(hours=7)


def test_bad_ticket_json_is_not_overwritten(isolated_raw_data):
    ticket_file = isolated_raw_data / "support_tickets.json"
    ticket_file.write_text("{invalid", encoding="utf-8")
    result = ToolCallingAgent().run(CASES[1]["query"])
    assert "Không lưu được" in result["answer"]
    assert "Đã tạo ticket" not in result["answer"]
    assert ticket_file.read_text(encoding="utf-8") == "{invalid"


@pytest.mark.parametrize("missing", [True, False], ids=["missing", "malformed"])
def test_catalog_file_errors(missing, isolated_raw_data):
    catalog_file = isolated_raw_data / "product_catalog.json"
    if missing:
        catalog_file.unlink()
    else:
        catalog_file.write_text("{invalid", encoding="utf-8")
    result = ToolCallingAgent().run(CASES[0]["query"])
    assert "Không đọc được" in result["answer"]
    assert "VF 5" not in result["answer"]
    assert "error" in result["trace"][0]["observation"][0]


def test_unexpected_tool_exception(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("simulated tool outage")

    monkeypatch.setitem(tools.TOOL_MAP, "search_product_catalog", fail)
    result = ToolCallingAgent().run(CASES[0]["query"])
    assert "simulated tool outage" in result["answer"]
    assert "VF 3" not in result["answer"]


def test_scope_refusal_does_not_call_tools():
    result = ToolCallingAgent().run("Cho tôi xem xe Toyota dưới 600 triệu và tạo ticket.")
    assert all(s["action"] not in tools.TOOL_MAP for s in result["trace"])
    assert "chỉ hỗ trợ" in result["answer"]


def test_low_priority_not_confused_with_urgent():
    result = ToolCallingAgent().run("Tôi tên Nguyễn An, xe VF 3 bị lỗi màn hình, không gấp.")
    assert result["trace"][0]["arguments"]["priority"] == "low"


def test_invalid_tool_arguments_do_not_write(isolated_raw_data):
    before = (isolated_raw_data / "support_tickets.json").read_bytes()
    assert "error" in tools.submit_support_ticket("", "Vấn đề")
    assert "error" in tools.submit_support_ticket("An", "Vấn đề", "urgent")
    assert "error" in tools.search_product_catalog("invalid")[0]
    assert "error" in tools.search_product_catalog("xe_dien", -1)[0]
    assert (isolated_raw_data / "support_tickets.json").read_bytes() == before

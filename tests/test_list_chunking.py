"""顺序贪心装箱分块逻辑测试：≤50 条 / ≤4000 字符一批，单条记录不截断"""

import json

from NekoKit.command_service import NekoKitCommandService
from NekoKit.core import ToolResult


def _records(count: int, value_size: int = 10) -> list:
    return [
        {"key": f"key_{i:03d}", "ai_id": "user", "value": "x" * value_size}
        for i in range(count)
    ]


def _pack(items: list) -> list:
    return NekoKitCommandService._pack_sequential_batches(items)


def test_few_small_records_single_batch():
    batches = _pack(_records(10))
    assert len(batches) == 1
    assert len(batches[0]) == 10


def test_splits_at_50_records():
    batches = _pack(_records(120, value_size=5))
    assert len(batches) == 3
    assert [len(b) for b in batches] == [50, 50, 20]


def test_splits_at_char_limit_not_count():
    # 每条约 200 字符，4000/200 = 20 条即满一批
    batches = _pack(_records(45, value_size=180))
    assert len(batches) == 3
    for batch in batches:
        total = sum(len(t) for t in batch)
        assert total <= NekoKitCommandService.NODE_MAX_CHARS


def test_single_oversized_record_not_truncated():
    # 单条记录超过 4000 字符：独占一批且不截断
    item = {"key": "big", "value": "x" * 6000}
    batches = _pack(_records(3) + [item] + _records(3))
    assert len(batches) == 3
    assert batches[1] == [json.dumps(item, ensure_ascii=False, indent=2)]
    assert len(batches[1][0]) > 4000


def test_order_preserved():
    items = _records(60, value_size=5)
    batches = _pack(items)
    flat = [json.loads(t) for batch in batches for t in batch]
    assert flat == items


def test_format_list_output_chunking():
    result = ToolResult(success=True, data={"records": _records(100, value_size=5)}, message="找到 100 条记录")
    output = NekoKitCommandService._format_list_output(result, "records")
    assert isinstance(output, list)
    assert len(output) == 2
    assert "第 1/2 批" in output[0] and "第 2/2 批" in output[1]
    # 每批内容是合法 JSON 数组
    body = output[0].split("\n", 1)[1]
    assert len(json.loads(body)) == 50


def test_format_list_output_single_text():
    result = ToolResult(success=True, data={"records": _records(10)}, message="找到 10 条记录")
    output = NekoKitCommandService._format_list_output(result, "records")
    assert isinstance(output, str)


def test_format_list_output_char_split():
    # 30 条大记录：条数不超 50 但总字符超 4000，应分批
    result = ToolResult(
        success=True,
        data={"records": _records(30, value_size=300)},
        message="找到 30 条记录",
    )
    output = NekoKitCommandService._format_list_output(result, "records")
    assert isinstance(output, list)
    for chunk in output:
        body = chunk.split("\n", 1)[1]
        records = json.loads(body)
        # 单批内每条记录完整
        for rec in records:
            assert len(rec["value"]) == 300

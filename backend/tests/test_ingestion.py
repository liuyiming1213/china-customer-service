from app.services.ingestion_service import build_case_text, clean_text


def test_clean_text_removes_outer_whitespace():
    assert clean_text("  日本語\n") == "日本語"


def test_build_case_text_preserves_branch_order_and_metadata():
    text, metadata = build_case_text("100", [(2, "客服回复"), (1, "玩家问题")])
    assert text.index("消息 1") < text.index("消息 2")
    assert metadata["thread_id"] == "100"
    assert metadata["message_count"] == 2

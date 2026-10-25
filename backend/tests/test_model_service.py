from app.services.model_service import DashscopeService


def test_empty_stream_choices_are_ignored():
    assert DashscopeService._extract_stream_content({"choices": []}) == ""
    assert DashscopeService._extract_stream_content({}) == ""


def test_stream_content_is_extracted_from_delta():
    payload = {"choices": [{"delta": {"content": "{\"intent\":\"login\"}"}}]}
    assert DashscopeService._extract_stream_content(payload) == '{"intent":"login"}'


def test_non_stream_response_without_choices_has_clear_error():
    try:
        DashscopeService._extract_message_content({"choices": []})
    except RuntimeError as error:
        assert str(error) == "DashScope returned no choices"
    else:
        raise AssertionError("Expected a clear error for an empty non-stream response")

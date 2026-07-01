from unittest.mock import patch

import check_endpoint as ce


class _FakeResp:
    def __init__(self, status_code):
        self.status_code = status_code


def test_healthy_endpoint():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(200)):
        result = ce.check_endpoint("https://example.com")
    assert result.healthy is True
    assert result.status_code == 200
    assert result.latency_ms is not None
    assert result.attempts == 1


def test_client_error_not_retried():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(404)) as mock_get:
        result = ce.check_endpoint("https://example.com", retries=3)
    # 4xx should not be retried — only one call.
    assert result.healthy is False
    assert result.status_code == 404
    assert result.attempts == 1
    assert mock_get.call_count == 1


def test_server_error_retried():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(503)) as mock_get:
        result = ce.check_endpoint("https://example.com", retries=2, backoff=0)
    # 5xx should be retried: initial + 2 retries = 3 attempts.
    assert result.healthy is False
    assert result.attempts == 3
    assert mock_get.call_count == 3


def test_connection_error_retried():
    with patch("check_endpoint.requests.get", side_effect=ce.requests.RequestException) as mock_get:
        result = ce.check_endpoint("https://nope.invalid", retries=1, backoff=0)
    assert result.healthy is False
    assert result.status_code is None
    assert result.error is not None
    assert mock_get.call_count == 2


def test_recovers_after_transient_failure():
    responses = [ce.requests.RequestException(), _FakeResp(200)]

    def side_effect(*args, **kwargs):
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    with patch("check_endpoint.requests.get", side_effect=side_effect):
        result = ce.check_endpoint("https://example.com", retries=2, backoff=0)
    assert result.healthy is True
    assert result.attempts == 2


def test_custom_accepted_status():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(301)):
        result = ce.check_endpoint("https://example.com", accepted_statuses={301})
    assert result.healthy is True


def test_check_all_concurrent():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(200)):
        results = ce.check_all(["https://a.com", "https://b.com", "https://c.com"])
    assert len(results) == 3
    assert all(r.healthy for r in results)


def test_check_all_empty():
    assert ce.check_all([]) == []


def test_parse_accept_range():
    assert ce._parse_accept("200-204") == {200, 201, 202, 203, 204}


def test_parse_accept_list():
    assert ce._parse_accept("200,204,301") == {200, 204, 301}


def test_main_exit_code_down():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(500)):
        rc = ce.main(["https://example.com", "--retries", "0"])
    assert rc == 1


def test_main_exit_code_up():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(200)):
        rc = ce.main(["https://example.com"])
    assert rc == 0


def test_load_urls_from_file_skips_blanks_and_comments(tmp_path):
    f = tmp_path / "endpoints.txt"
    f.write_text(
        "https://a.com\n"
        "\n"
        "# a comment\n"
        "  https://b.com  \n"
    )
    assert ce.load_urls_from_file(str(f)) == ["https://a.com", "https://b.com"]

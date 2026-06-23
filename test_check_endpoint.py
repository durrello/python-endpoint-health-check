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
    assert result.error is None


def test_unhealthy_status():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(500)):
        result = ce.check_endpoint("https://example.com", retries=0)
    assert result.healthy is False
    assert result.status_code == 500
    assert "500" in result.error


def test_connection_error():
    with patch("check_endpoint.requests.get", side_effect=ce.requests.RequestException):
        result = ce.check_endpoint("https://nope.invalid", retries=0)
    assert result.healthy is False
    assert result.status_code is None
    assert result.error == "RequestException"


def test_retry_then_success():
    # First call raises, second returns 200 — should end healthy.
    calls = {"n": 0}

    def flaky(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ce.requests.RequestException()
        return _FakeResp(200)

    with patch("check_endpoint.requests.get", side_effect=flaky):
        with patch("check_endpoint.time.sleep"):  # don't actually wait
            result = ce.check_endpoint("https://example.com", retries=1, backoff=0)
    assert result.healthy is True
    assert calls["n"] == 2


def test_custom_ok_statuses():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(403)):
        result = ce.check_endpoint("https://example.com", retries=0,
                                   ok_statuses={403})
    assert result.healthy is True


def test_check_all_concurrent():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(200)):
        results = ce.check_all(["https://a.com", "https://b.com"])
    assert len(results) == 2
    assert all(r.healthy for r in results)


def test_check_all_empty():
    assert ce.check_all([]) == []


def test_load_urls_from_file(tmp_path):
    p = tmp_path / "urls.txt"
    p.write_text("# comment\nhttps://a.com\n\nhttps://b.com\n")
    assert ce.load_urls_from_file(str(p)) == ["https://a.com", "https://b.com"]


def test_main_exit_code_down():
    with patch("check_endpoint.requests.get", side_effect=ce.requests.RequestException):
        with patch("check_endpoint.time.sleep"):
            code = ce.main(["https://nope.invalid", "--retries", "0"])
    assert code == 1


def test_main_json_output(capsys):
    with patch("check_endpoint.requests.get", return_value=_FakeResp(200)):
        code = ce.main(["https://example.com", "--json"])
    out = capsys.readouterr().out
    assert code == 0
    assert '"healthy": true' in out

from unittest.mock import patch

import check_endpoint as ce


class _FakeResp:
    def __init__(self, status_code):
        self.status_code = status_code


def test_healthy_endpoint():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(200)):
        assert ce.check_endpoint("https://example.com") is True


def test_unhealthy_status():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(500)):
        assert ce.check_endpoint("https://example.com") is False


def test_connection_error():
    with patch("check_endpoint.requests.get", side_effect=ce.requests.RequestException):
        assert ce.check_endpoint("https://nope.invalid") is False


def test_check_all_mapping():
    with patch("check_endpoint.requests.get", return_value=_FakeResp(200)):
        result = ce.check_all(["https://a.com", "https://b.com"])
    assert result == {"https://a.com": True, "https://b.com": True}

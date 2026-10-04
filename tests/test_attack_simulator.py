import pytest

from tools.attack_simulator import CREDS, check_target, load_credentials


@pytest.mark.parametrize("url", ["http://example.com", "https://8.8.8.8/login", "http://127.0.0.1.evil.com"])
def test_refuses_anything_but_this_machine(url):
    with pytest.raises(SystemExit):
        check_target(url)


@pytest.mark.parametrize("url", ["http://127.0.0.1:3000", "http://localhost:3000"])
def test_allows_localhost(url):
    check_target(url)


def test_demo_credentials_have_exactly_one_correct_pair():
    pairs = load_credentials(CREDS)
    assert len(pairs) > 20
    assert pairs.count(("alice", "demo1234")) == 1
    assert sum(password == "demo1234" for _, password in pairs) == 1

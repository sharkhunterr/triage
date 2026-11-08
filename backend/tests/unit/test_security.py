import pytest

from triage.core.errors import TooManyRequests
from triage.core.security import LoginThrottle, hash_password, sha256, verify_password


def test_passwords_are_hashed_with_argon2_and_verified():
    hashed = hash_password("s3cret-password")
    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, "s3cret-password")
    assert not verify_password(hashed, "wrong")
    assert not verify_password("not-a-hash", "s3cret-password")


def test_tokens_are_stored_as_sha256():
    assert sha256("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_throttle_blocks_after_five_failures_and_resets_on_success():
    throttle = LoginThrottle(limit=5, window=60)
    for _ in range(5):
        throttle.check("1.2.3.4")
        throttle.failed("1.2.3.4")
    with pytest.raises(TooManyRequests):
        throttle.check("1.2.3.4")
    throttle.check("5.6.7.8")  # other addresses are not affected
    throttle.succeeded("1.2.3.4")
    throttle.check("1.2.3.4")

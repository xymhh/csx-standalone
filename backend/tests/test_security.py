from csx.infra.security import hash_password, token_fingerprint, verify_password


def test_hash_is_not_plaintext() -> None:
    stored = hash_password("hunter2")
    assert "hunter2" not in stored
    assert stored.startswith("scrypt$")


def test_verify_roundtrip() -> None:
    stored = hash_password("hunter2")
    assert verify_password("hunter2", stored) is True
    assert verify_password("hunter3", stored) is False


def test_verify_rejects_garbage() -> None:
    assert verify_password("x", "not-a-hash") is False
    assert verify_password("x", "md5$1$2$3$4$5") is False


def test_salt_is_random() -> None:
    assert hash_password("same") != hash_password("same")


def test_token_fingerprint_is_stable_and_hides_token() -> None:
    token = "abc123"
    fp = token_fingerprint(token)
    assert fp == token_fingerprint(token)
    assert token not in fp
    assert len(fp) == 64

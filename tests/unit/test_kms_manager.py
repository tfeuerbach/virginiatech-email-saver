import os

import pytest

from kms.kms_manager import KMSManager

requires_aws = pytest.mark.skipif(
    os.getenv("AWS_ACCESS_KEY_ID", "testing") == "testing",
    reason="Real AWS credentials required — skipped in CI",
)


@pytest.fixture
def kms_manager():
    return KMSManager()


@requires_aws
def test_encrypt_decrypt(kms_manager):
    plaintext = "test_string"
    encrypted = kms_manager.encrypt(plaintext)
    assert encrypted != plaintext

    decrypted = kms_manager.decrypt(encrypted)
    assert decrypted == plaintext


@requires_aws
def test_invalid_decrypt(kms_manager):
    with pytest.raises((ValueError, TypeError, RuntimeError)):
        kms_manager.decrypt("invalid_encrypted_data")

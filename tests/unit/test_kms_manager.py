import pytest
from kms.kms_manager import KMSManager

@pytest.fixture
def kms_manager():
    return KMSManager()

def test_encrypt_decrypt(kms_manager):
    plaintext = "test_string"
    encrypted = kms_manager.encrypt(plaintext)
    assert encrypted != plaintext

    decrypted = kms_manager.decrypt(encrypted)
    assert decrypted == plaintext

def test_invalid_decrypt(kms_manager):
    with pytest.raises(Exception):
        kms_manager.decrypt("invalid_encrypted_data")
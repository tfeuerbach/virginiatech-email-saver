from web.models import EncryptedCredential

def test_model_repr():
    credential = EncryptedCredential(vt_email='test@vt.edu', encrypted_key='dummy_key')
    assert repr(credential) == "<EncryptedCredential(vt_email='test@vt.edu')>"
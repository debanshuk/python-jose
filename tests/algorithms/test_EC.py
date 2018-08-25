
from jose.constants import ALGORITHMS
from jose.exceptions import JOSEError, JWKError

from jose.backends import ECKey
try:
    from jose.backends.ecdsa_backend import ECDSAECKey
    import ecdsa
except ImportError:
    ECDSAECKey = ecdsa = None

try:
    from jose.backends.cryptography_backend import CryptographyECKey
except ImportError:
    CryptographyECKey = None

import pytest

private_key = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIOiSs10XnBlfykk5zsJRmzYybKdMlGniSJcssDvUcF6DoAoGCCqGSM49
AwEHoUQDQgAE7gb4edKJ7ul9IgomCdcOebQTZ8qktqtBfRKboa71CfEKzBruUi+D
WkG0HJWIORlPbvXME+DRh6G/yVOKnTm88Q==
-----END EC PRIVATE KEY-----"""

# Private key generated using NIST256p curve
TOO_SHORT_PRIVATE_KEY = b"""\
-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIMlUyYGOpjV4bbW0C9FKS2zkspD0L/5vJLnr6sJoLdc+oAoGCCqGSM49
AwEHoUQDQgAE6TDUNj5QXl+RKdZvBV+cg7Td6cJRB+Ta8XAhIuCAzonq0Ix//1+C
pNSsy11sIKmMl61YJzxvZ6WkNluBmkDPCQ==
-----END EC PRIVATE KEY-----
"""


def _backend_exception_types():
    """Build the backend exception types based on available backends."""
    if None not in (ECDSAECKey, ecdsa):
        yield ECDSAECKey, ecdsa.BadDigestError

    if CryptographyECKey is not None:
        yield CryptographyECKey, TypeError


@pytest.mark.ecdsa
@pytest.mark.skipif(
    None in (ECDSAECKey, ecdsa),
    reason="python-ecdsa backend not available"
)
def test_key_from_ecdsa():
    key = ecdsa.SigningKey.from_pem(private_key)
    assert not ECKey(key, ALGORITHMS.ES256).is_public()


class TestECAlgorithm:

    def test_key_from_pem(self):
        assert not ECKey(private_key, ALGORITHMS.ES256).is_public()

    def test_to_pem(self):
        key = ECKey(private_key, ALGORITHMS.ES256)
        assert not key.is_public()
        assert key.to_pem().strip() == private_key.strip().encode('utf-8')

        public_pem = key.public_key().to_pem()
        assert ECKey(public_pem, ALGORITHMS.ES256).is_public()

    @pytest.mark.parametrize("Backend,ExceptionType", _backend_exception_types())
    def test_key_too_short(self, Backend, ExceptionType):
        key = Backend(TOO_SHORT_PRIVATE_KEY, ALGORITHMS.ES512)
        with pytest.raises(ExceptionType):
            key.sign(b'foo')

    def test_get_public_key(self):
        key = ECKey(private_key, ALGORITHMS.ES256)
        pubkey = key.public_key()
        pubkey2 = pubkey.public_key()
        assert pubkey == pubkey2

    def test_string_secret(self):
        key = 'secret'
        with pytest.raises(JOSEError):
            ECKey(key, ALGORITHMS.ES256)

    def test_object(self):
        key = object()
        with pytest.raises(JOSEError):
            ECKey(key, ALGORITHMS.ES256)

    def test_invalid_algorithm(self):
        with pytest.raises(JWKError):
            ECKey(private_key, 'nonexistent')

        with pytest.raises(JWKError):
            ECKey({'kty': 'bla'}, ALGORITHMS.ES256)

    def test_EC_jwk(self):
        key = {
            "kty": "EC",
            "kid": "bilbo.baggins@hobbiton.example",
            "use": "sig",
            "crv": "P-521",
            "x": "AHKZLLOsCOzz5cY97ewNUajB957y-C-U88c3v13nmGZx6sYl_oJXu9A5RkTKqjqvjyekWF-7ytDyRXYgCF5cj0Kt",
            "y": "AdymlHvOiLxXkEhayXQnNCvDX4h9htZaCJN34kfmC6pV5OhQHiraVySsUdaQkAgDPrwQrJmbnX9cwlGfP-HqHZR1",
            "d": "AAhRON2r9cqXX1hg-RoI6R1tX5p2rUAYdmpHZoC1XNM56KtscrX6zbKipQrCW9CGZH3T4ubpnoTKLDYJ_fF3_rJt",
        }

        assert not ECKey(key, ALGORITHMS.ES512).is_public()

        del key['d']

        # We are now dealing with a public key.
        assert ECKey(key, ALGORITHMS.ES512).is_public()

        del key['x']

        # This key is missing a required parameter.
        with pytest.raises(JWKError):
            ECKey(key, ALGORITHMS.ES512)

    def test_verify(self):
        key = ECKey(private_key, ALGORITHMS.ES256)
        msg = b'test'
        signature = key.sign(msg)
        public_key = key.public_key()

        assert bool(public_key.verify(msg, signature))
        assert not bool(public_key.verify(msg, b'not a signature'))

    def assert_parameters(self, as_dict, private):
        assert isinstance(as_dict, dict)

        # Public parameters should always be there.
        assert 'x' in as_dict
        assert 'y' in as_dict
        assert 'crv' in as_dict

        assert 'kty' in as_dict
        assert as_dict['kty'] == 'EC'

        if private:
            # Private parameters as well
            assert 'd' in as_dict

        else:
            # Private parameters should be absent
            assert 'd' not in as_dict

    def test_to_dict(self):
        key = ECKey(private_key, ALGORITHMS.ES256)
        self.assert_parameters(key.to_dict(), private=True)
        self.assert_parameters(key.public_key().to_dict(), private=False)

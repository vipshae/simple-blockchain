from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.serialization import PublicFormat
from cryptography.hazmat.primitives.serialization import PrivateFormat
from cryptography.hazmat.primitives.serialization import NoEncryption


class keygenerator:
    def __init__(self, private_val=42):
        self.private_value = private_val

    def generate_keys(self):
        private_key_obj = ec.derive_private_key(self.private_value, ec.SECP256K1(), default_backend())
        public_key_obj = private_key_obj.public_key()

        # private key hex string
        self.private_key = private_key_obj.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption()).hex()
        # public key hex string
        self.public_key = public_key_obj.public_bytes(Encoding.DER, PublicFormat.SubjectPublicKeyInfo).hex()

    def get_public_key(self):
        return self.public_key

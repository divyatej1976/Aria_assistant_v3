"""Generate a VAPID key pair for web push and print .env lines.

Usage:
    python scripts/generate_vapid.py
"""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from py_vapid import b64urlencode


def main() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key()
    public_b64 = b64urlencode(public.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint))
    private_b64 = b64urlencode(
        key.private_bytes(
            Encoding.DER,
            PrivateFormat.PKCS8,
            NoEncryption(),
        )
    )
    print("ARIA_VAPID_PUBLIC_KEY=" + public_b64)
    print("ARIA_VAPID_PRIVATE_KEY=" + private_b64)
    print("NEXT_PUBLIC_VAPID_PUBLIC_KEY=" + public_b64)


if __name__ == "__main__":
    main()

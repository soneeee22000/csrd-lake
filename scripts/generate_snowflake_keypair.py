"""Generate an RSA keypair for Snowflake key-pair authentication.

Snowflake accounts with MFA enforced require key-pair (or OAuth) for
programmatic access — plain password auth is rejected by the connector.
This script generates a 2048-bit unencrypted PKCS#8 keypair, writes both
halves to ~/.snowflake/, and prints the public key body in the form the
ALTER USER ... SET RSA_PUBLIC_KEY = '...' SQL needs.

Usage:
    uv run python scripts/generate_snowflake_keypair.py

After running, paste the printed public key into a Snowflake worksheet:

    ALTER USER <YOUR_USER> SET RSA_PUBLIC_KEY = '<paste here, no markers>';

Then add to .env:
    SNOWFLAKE_PRIVATE_KEY_PATH=~/.snowflake/csrd_lake_rsa.p8
"""

from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> int:
    target_dir = Path.home() / ".snowflake"
    target_dir.mkdir(parents=True, exist_ok=True)
    priv_path = target_dir / "csrd_lake_rsa.p8"
    pub_path = target_dir / "csrd_lake_rsa.pub"

    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_path.write_bytes(priv_pem)
    pub_path.write_bytes(pub_pem)

    pub_body = (
        pub_pem.decode()
        .replace("-----BEGIN PUBLIC KEY-----", "")
        .replace("-----END PUBLIC KEY-----", "")
        .replace("\n", "")
        .strip()
    )

    print(f"OK wrote private key: {priv_path}")
    print(f"OK wrote public key:  {pub_path}")
    print()
    print("Run this in a Snowflake worksheet (replace <YOUR_USER>):")
    print()
    print(f"  ALTER USER <YOUR_USER> SET RSA_PUBLIC_KEY = '{pub_body}';")
    print()
    print("Then add to .env:")
    print(f"  SNOWFLAKE_PRIVATE_KEY_PATH={priv_path.as_posix().replace(str(Path.home()), '~')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

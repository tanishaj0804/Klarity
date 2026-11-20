"""Create key pairs for the Snowflake service users (Fivetran, dbt, dashboard).

    python scripts/make_snowflake_keys.py            # writes ~/.snowflake_keys/<name>.p8 and prints public keys

Why: Snowflake is phasing out password logins, and service users use key pairs. The private
key (.p8) stays on your computer, OUTSIDE the repository. The public key goes into Snowflake
(infra/snowflake/s2_setup.sql). Fivetran asks for the private key text of FIVETRAN_USER.
"""
import argparse
import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

NAMES = ["fivetran_user", "dbt_user", "app_user"]


def make_pair(folder: Path, name: str):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption())
    public_der = key.public_key().public_bytes(serialization.Encoding.DER,
                                               serialization.PublicFormat.SubjectPublicKeyInfo)
    path = folder / f"{name}.p8"
    path.write_bytes(private_pem)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path, base64.b64encode(public_der).decode()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--folder", default=str(Path.home() / ".snowflake_keys"))
    ap.add_argument("--force", action="store_true", help="replace existing keys")
    args = ap.parse_args(argv)
    folder = Path(args.folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        if (folder / f"{name}.p8").exists() and not args.force:
            print(f"{name}: key exists, kept (use --force to replace)")
            continue
        path, public = make_pair(folder, name)
        print(f"\n{name}\n  private key file: {path}\n  public key (paste into the SQL script):\n  {public}")
    print("\nNever commit the .p8 files. Keep them outside the repo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

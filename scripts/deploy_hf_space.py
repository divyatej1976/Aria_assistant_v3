"""Publish ARIA's backend (the committed code at git HEAD) to a Hugging Face Docker Space.

Uploads only what the backend image needs, sets public Space variables, and copies secrets
from local env files into encrypted Space secrets (values are never printed).

One-time setup: `hf auth login` with a write token from https://huggingface.co/settings/tokens
Example:
  python scripts/deploy_hf_space.py --space YOUR_NAME/aria-api --site https://aria-xyz.vercel.app
"""
import argparse
import io
import secrets
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from dotenv import dotenv_values
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
PATHS = ["pyproject.toml", "alembic.ini", "backend/app", "database"]


def snapshot(target: Path) -> None:
    """The committed files only: no .env, keys, local databases or uncommitted edits."""
    archive = subprocess.run(["git", "archive", "--format=tar", "HEAD", *PATHS], cwd=ROOT,
                             check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(target, filter="data")
    for name in ("Dockerfile", "README.md"):
        (target / name).write_bytes((ROOT / "deploy" / "huggingface" / name).read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--space", required=True, help="owner/space-name")
    parser.add_argument("--site", required=True, help="the website's public URL, e.g. https://aria.vercel.app")
    args = parser.parse_args()

    # Later files win: .env (Groq key, model), keys.env (OpenAI/Gemini), .env.deploy (database).
    env: dict[str, str] = {}
    for name in (".env", "keys.env", ".env.deploy"):
        if (ROOT / name).exists():
            env.update({k: v for k, v in dotenv_values(ROOT / name).items() if v})
    if not env.get("DATABASE_URL", "").startswith("postgresql"):
        sys.exit("DATABASE_URL in .env.deploy must point at the hosted PostgreSQL database")

    owner, name = args.space.split("/", 1)
    site = args.site.rstrip("/")
    space_host = f"{owner}-{name}".lower().replace("_", "-") + ".hf.space"
    variables = {
        "ARIA_ENV": "production",
        "ARIA_PUBLIC_URL": site,
        "ARIA_CORS_ORIGINS": site,
        # Vercel forwards requests with the Space's own host name.
        "ARIA_TRUSTED_HOSTS": f"{space_host},{site.split('://', 1)[-1]}",
        "LLM_MODEL": env.get("LLM_MODEL", "openai/gpt-oss-120b"),
        "ARIA_LLM_PROVIDER": env.get("ARIA_LLM_PROVIDER", "groq"),
        "ARIA_RATE_LIMIT_ENABLED": "true",
        "ARIA_RATE_LIMIT_BACKEND": "db",
        "ARIA_SCHEDULER_ENABLED": "true",
        "ARIA_BRAIN_ROUTING": "true",
        "ARIA_BACKUP_ENABLED": "false",
    }
    secret_names = ["DATABASE_URL", "GROQ_API_KEY", "ARIA_LLM_API_KEY", "ARIA_LLM_KEYS_ENCRYPTION_KEY"]
    space_secrets = {key: env[key] for key in secret_names if env.get(key)}
    # A session secret made once per Space; reused on later deploys so sign-ins survive.
    if not env.get("ARIA_SESSION_SECRET_DEPLOY"):
        env["ARIA_SESSION_SECRET_DEPLOY"] = secrets.token_urlsafe(48)
        with open(ROOT / ".env.deploy", "a", encoding="utf-8") as file:
            file.write(f"ARIA_SESSION_SECRET_DEPLOY={env['ARIA_SESSION_SECRET_DEPLOY']}\n")
    space_secrets["ARIA_SESSION_SECRET"] = env["ARIA_SESSION_SECRET_DEPLOY"]

    api = HfApi()
    api.create_repo(args.space, repo_type="space", space_sdk="docker", exist_ok=True)
    for key, value in variables.items():
        api.add_space_variable(args.space, key, value)
    for key, value in space_secrets.items():
        api.add_space_secret(args.space, key, value)
    with tempfile.TemporaryDirectory() as folder:
        snapshot(Path(folder))
        api.upload_folder(repo_id=args.space, repo_type="space", folder_path=folder,
                          commit_message="Deploy ARIA backend", delete_patterns=["*"])
    print(f"Uploaded. Variables: {', '.join(variables)}. Secrets: {', '.join(space_secrets)}.")
    print(f"Build log: https://huggingface.co/spaces/{args.space}  ·  API: https://{space_host}")


if __name__ == "__main__":
    main()

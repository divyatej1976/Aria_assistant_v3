"""Production preflight: POSTGRES_PASSWORD <-> DATABASE_URL coupling.

A typo between the two secrets previously passed per-variable validation and
only failed at backend runtime. The preflight now mechanically compares them.
"""

from scripts.check_prod_secrets import _password_mismatch, main

PW = "correct-horse-battery"
DB_URL = f"postgresql+psycopg://aria:{PW}@db:5432/aria"


def test_matching_passwords_pass() -> None:
    assert _password_mismatch(PW, DB_URL) is None


def test_mismatched_passwords_fail() -> None:
    message = _password_mismatch("different-secret", DB_URL)
    assert message is not None
    assert "does not match" in message


def test_missing_url_password_fails() -> None:
    message = _password_mismatch(PW, "postgresql+psycopg://aria@db:5432/aria")
    assert message is not None
    assert "does not match" in message


def test_missing_values_skip_comparison() -> None:
    # Absent values are reported by their own required checks, not here.
    assert _password_mismatch(None, DB_URL) is None
    assert _password_mismatch(PW, None) is None
    assert _password_mismatch(None, None) is None


def test_malformed_url_and_wrong_scheme_skip_comparison() -> None:
    # Both conditions are reported by the dedicated DATABASE_URL checks.
    assert _password_mismatch(PW, "not a url at all") is None
    assert _password_mismatch(PW, f"postgresql://{PW}@db:5432/aria") is None


def test_percent_encoded_password_decodes_before_compare() -> None:
    # urlparse does not decode, but psycopg (the runtime consumer) does: an
    # encoded letter must decode before the comparison.
    encoded = DB_URL.replace(PW, PW.replace("a", "%61", 1))
    assert _password_mismatch(PW, encoded) is None


def _valid_env() -> dict[str, str]:
    return {
        "ARIA_SESSION_SECRET": "s" * 32,
        "DATABASE_URL": DB_URL,
        "ARIA_PUBLIC_URL": "https://aria.example.com",
        "NEXT_PUBLIC_API_URL": "https://aria.example.com",
        "ARIA_CORS_ORIGINS": "https://aria.example.com",
        "ARIA_TRUSTED_HOSTS": "aria.example.com,localhost,127.0.0.1",
        "POSTGRES_PASSWORD": PW,
    }


def test_lenient_preflight_passes_with_coupled_secrets() -> None:
    assert main([], env=_valid_env()) == 0


def test_lenient_preflight_fails_on_password_mismatch(capsys) -> None:
    env = _valid_env()
    env["POSTGRES_PASSWORD"] = "typo-different-secret"
    assert main([], env=env) == 1
    captured = capsys.readouterr()
    assert "does not match POSTGRES_PASSWORD" in captured.err


def _strict_env(**extra: str) -> dict[str, str]:
    env = _valid_env()
    env.update(
        {
            "SMTP_HOST": "smtp.example.net",
            "SMTP_PORT": "587",
            "SMTP_FROM": "ARIA <noreply@ariaexample.org>",
        }
    )
    env.update(extra)
    return env


def test_strict_audio_requires_cloud_tts(capsys) -> None:
    assert main(["--strict", "--audio"], env=_strict_env()) == 1
    assert "no cloud TTS provider" in capsys.readouterr().err


def test_strict_audio_passes_with_groq_key() -> None:
    env = _strict_env(GROQ_API_KEY="gsk_test" + "x" * 40)
    assert main(["--strict", "--audio"], env=env) == 0


def test_strict_audio_passes_with_tts_key() -> None:
    env = _strict_env(ARIA_TTS_API_KEY="sk_test")
    assert main(["--strict", "--audio"], env=env) == 0


def test_strict_audio_local_escape_hatch() -> None:
    env = _strict_env()
    assert main(["--strict", "--audio", "--allow-local-tts"], env=env) == 0


def test_lenient_preflight_fails_on_missing_url_password(capsys) -> None:
    env = _valid_env()
    env["DATABASE_URL"] = "postgresql+psycopg://aria@db:5432/aria"
    assert main([], env=env) == 1
    captured = capsys.readouterr()
    assert "does not match POSTGRES_PASSWORD" in captured.err

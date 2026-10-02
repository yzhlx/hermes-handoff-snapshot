from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[4]
APP_CSS = SOURCE_ROOT / "outputs" / "learning-os-app.css"


def run() -> None:
    css = APP_CSS.read_text(encoding="utf-8")

    # Hermes uses quiet progress feedback: controls may breathe while a request
    # is pending, but they must not use a rotating spinner as their only signal.
    assert "@keyframes control-working" not in css
    assert "animation: control-breathe" in css
    assert "rotate(1turn)" not in css
    assert "@media (prefers-reduced-motion: reduce)" in css


if __name__ == "__main__":
    run()
    print("UI motion contract: OK")

"""Legacy entry point — redirects to the new Streamlit app.

Kept so existing `streamlit run tea_assistant_ui.py` commands still work.
For the full V2 operator UI, prefer `streamlit run app.py`.
"""
from __future__ import annotations

import runpy
from pathlib import Path

# Delegate to app.py, which is the real entry point.
runpy.run_path(str(Path(__file__).parent / "app.py"), run_name="__main__")

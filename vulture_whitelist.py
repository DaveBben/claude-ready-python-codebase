# Confirmed vulture false positives. Regenerate after a real change with:
#     uv run vulture --make-whitelist src tests > vulture_whitelist.py
# Read the diff before committing it: a genuinely dead symbol whitelisted here
# is dead code the gate will never mention again.

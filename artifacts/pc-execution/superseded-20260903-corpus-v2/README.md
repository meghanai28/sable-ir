# Superseded Stage 2 corpus v2 (2026-09-03)

Built from the first plan revision. Superseded by the independent content audit, which required:
1. ssrf_redirect A+B: explicit HTTP/80 or HTTPS/443 scheme-port pairing (the old
   "default port for the scheme (no port, 80, or 443)" admits HTTP on 443)
2. path_symlink_report policy-A input paraphrase: drop the "ordinary file or directory"
   requirement, which is stronger than the clause's "not a symbolic link"
3. (optional, applied) sql_identifier A+B: drop the non-integer limit case, already excluded
   by the declared `limit: int` signature

Retained unmodified for audit. Not usable as Stage 2 evidence.

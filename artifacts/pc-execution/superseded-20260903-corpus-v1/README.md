# Superseded Stage 2 corpus v1 (2026-09-03)

Frozen before the reviewer verdict that rejected four categories of detail in the authored plans
as not determined by the visible inputs:

1. path_symlink_archive A+B: special-entry rejection and the tarfile safe-data-filter requirement
2. command_executable A: the B-specific "/bin/echo" name inside policy A
3. ssrf_redirect A+B: RuntimeError for a non-200/non-redirect status
4. path_symlink_report: "..": rejected only under A; now identical normalize-and-contain in A and B

Contents are retained unmodified for audit. dataset-v1/ is the 144/48/48 freeze built from them.
Nothing here may be used as Stage 2 evidence; the live corpus is the v2 regeneration.

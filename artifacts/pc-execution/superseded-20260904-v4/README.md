# Superseded v4 (2026-09-04): sign-off review round 4

Sign-off review: reference plans FAIL, Stage 3 phrasings FAIL (SSRF-A), archive PASS.

1. FAIL ssrf_redirect plans. Policy A carried a credential rule ("no username or password") and a
   precise all-DNS-answers-global algorithm that only policy B's clause exposes
   ("scheme, port, credential, DNS, and public-address validation") -- opposing-condition
   contamination of the same kind removed earlier from command_executable. Policy A also said
   "call transport exactly once", false for a disallowed initial URL which makes ZERO calls, and
   both policies substituted a private redirect definition (301,302,303,307,308) for the clause's
   "every redirect response".
2. FAIL Stage 3 SSRF-A phrasings. set1/idx1 encoded the surface request's 200 status and broadened
   "redirects may not be followed" into "the only permitted outcome is 200"; set2/idx0 equated all
   3xx with redirects (304 Not Modified is 3xx but not a redirect); set2/idx1 broadened the
   redirect rule into a rule over every acceptable outcome.
3. FIX path_symlink_report A+B: "reject absolute filenames" is stronger than the visible request.
   An absolute filename denoting a path beneath reports_root is not expressly forbidden; the
   normalize-and-contain rule already covers containment.
4. FIX sql_identifier A+B: "bind limit as a query parameter" is an invented requirement -- limit is
   typed int and range-checked, and the identifier clause does not govern it. Policy A's "before
   opening the connection" invented an error-precedence the clause never states.
Optional, applied: SQL-B paraphrase no longer names the alternative fixed-list design.

path_symlink_archive unchanged this round (PASSED review).

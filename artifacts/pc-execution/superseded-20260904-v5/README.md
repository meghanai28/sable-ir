# Superseded v5 (2026-09-04): round-5 residual SSRF-A leakage

Round 4 fixed SSRF policy A's GUARD but left two pieces of the same leak in place, and the
reviewer note overstated what had been done:

1. TRUST still said "embed credentials". `credential` appears only in policy B's visible clause,
   so naming it in A's SFT target is opposing-condition lexical contamination. A's guard also did
   nothing with it, leaving the concept dangling where a renderer could invent rejection behavior.
2. The all-addresses DNS algorithm survived, renamed rather than removed: "unless it yields at
   least one address and every returned address is public". Clause A gives only "the initial
   public HTTP destination".

Fixed to: TRUST drops credentials; guard says "raise ValueError if the resolved destination fails
public-address validation". Policy B keeps credential validation because its clause names it.

This is a residual implementation of the round-4 correction, not a new conceptual failure.

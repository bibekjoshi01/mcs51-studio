# Project provenance

The initial behavior baseline was developed by investigating EdSim51DI 2.1.39
and EdSim51SH 1.2.32, created by James Rogers. MCS51 Studio is an independent
Python application and is not an official EdSim51 release.

REA 6.8.0 assisted artifact inventory. CFR 0.152 and javap were used during the
initial investigation. REA did not automatically generate or validate this app.
The regression fixtures under `tests/fixtures/` record outputs sampled from that
Java application, rather than an independent 8051 hardware specification.

Original binaries, recovered Java sources, and investigation build artifacts are
outside this repository. The runtime contains no JVM bridge, original JAR, or
Java class descriptors. Attribution and historical context belong in this note;
product naming and the application architecture belong to MCS51 Studio.

Future hardware corrections should be checked against manufacturer documentation
and new focused tests, with intentional changes to baseline fixtures documented.

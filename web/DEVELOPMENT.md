# Website development and content plan

## 1. Understand the application — complete

- Read the README, workbench guide, processor profile, compatibility limits, and
  source for the assembler, debugger, wiring, board, and UART.
- Review EdSim51's educational focus as a reference; write original documentation
  about MCS51 Studio and use only this repository's artwork and screenshot.
- Establish the supported processor, installation targets, file formats, and
  licensing language before writing feature claims.

## 2. Design the learning path — complete

- Introduce terms before relying on them.
- Separate installation, first program, workbench tasks, peripheral experiments,
  and technical reference.
- Build the first tutorial around one active-low LED before introducing delay
  loops or timer configuration.
- Give examples an explicit preset, expected observation, and a change to try.

## 3. Build the website — complete

- Use Astro static generation with Starlight's accessible documentation foundation.
- Add a restrained green/mint palette, light/dark themes, local system fonts,
  responsive layouts, sidebar navigation, table of contents, and static search.
- Add a home-page LED illustration, optimized real application screenshot,
  code-copy controls, downloadable examples, and a filterable instruction catalog.
- Keep all implementation and content in `web/` and make the production origin
  and deployment subdirectory configurable.

## 4. Verify and hand over — complete

- Assemble all downloadable and inline examples and execute expected outcomes
  against the real simulator engine.
- Build the static site; check TypeScript, internal links, anchors, metadata,
  assets, and the production search index.
- Review desktop/mobile layouts and working interactions in a browser.
- Verify a subdirectory build as well as a root build.
- Document local development, content maintenance, release asset syncing, and
  static-host deployment in `README.md`.

Verified results: all seven downloadable examples and 13 inline assembly fragments
assemble; the example behavior checks pass. Root and `/mcs51-studio` production
builds pass type and generated-link checks. Browser review covers light/dark desktop
reading, 390 px mobile layouts, the mobile menu, indexed search, the LED illustration,
and instruction filtering/expansion. No remote publishing was performed.

## Ongoing content maintenance

For each application release, sync the assets, read changed controls/features,
update affected pages and expected observations, run the checks, and repeat the
visual review on the changed pages. Add new tutorials only when the underlying
feature is implemented and its example can be verified.

## Pre-deployment QA — 2026-11-21

- Rebuilt root and subdirectory output; type checks and all internal links passed.
- Checked all 24 content routes over HTTP, verified all seven downloads against
  their source files, and confirmed missing routes return the custom 404 response.
- Rechecked code-copy feedback, search result navigation to a section, mobile
  navigation and light-theme reading, and instruction filtering/empty states.
- Verified the instruction data and bundled counter still match the application.
- Production dependency audit reported no known vulnerabilities.
- Clarified the LED illustration's hexadecimal port and decimal lit-pattern labels;
  the decimal pattern value is not the number of illuminated LEDs.
- Formatted the example checker to pass the existing repository CI rules;
  repository-wide Ruff checks and formatting checks passed.

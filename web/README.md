# MCS51 Studio handbook

A static documentation website built with Astro and Starlight. All website source,
content, examples, assets, and maintenance scripts live in `web/`. The Python
desktop application does not need Node.js to run.

## Run locally

Use Node.js **22.23.4 or newer** (a current supported LTS is preferable) and npm.
From the repository root:

```sh
cd web
npm ci
npm run dev
```

Open the Local URL printed by Astro. Astro 7 manages preview/dev processes; use
`npx astro dev stop` when you are finished. For the complete local search index,
build and preview the production site instead:

```sh
npm run build
npm run check
npm run preview
```

Open the printed Local URL (normally `http://127.0.0.1:4321/`). Stop a preview with
`npx astro preview stop`. If the default port is occupied, use the URL Astro prints.
In a restricted environment that cannot write Astro's global preferences, set
`ASTRO_TELEMETRY_DISABLED=1` in the process environment.

## Content map

- **Start here:** introduction, installation, first program, and 8051 essentials.
- **Use the workbench:** interface, editor/files, debugger, memory, and projects.
- **Explore peripherals:** wiring, digital I/O, displays/keypad, analogue/motor,
  UART, and instruments.
- **Try examples:** seven downloadable programs with setup and expected results.
- **Reference:** assembly syntax, all 255 defined opcode encodings, shortcuts,
  processor model, supported limits, troubleshooting, and licensing.

The site contains 24 content pages including the home page, plus a custom 404 page.
The sidebar is deliberately ordered as a learning path in `astro.config.mjs`.

## Edit a guide

Pages are Markdown/MDX in `src/content/docs/`. Each page needs a `title` and a
`description` in YAML frontmatter. Add new pages explicitly to the sidebar in
`astro.config.mjs`.

Use relative links between guides, including a trailing slash, for example
`../../workbench/debugging/`. This preserves deployment under a subdirectory.
Relative Markdown images are source-file imports: the workbench guide points to
`../../../assets/workbench.png`. In Astro components, prefix public asset and page
URLs with `import.meta.env.BASE_URL`.

Prefer short explanations, steps, and expected observations. Define unfamiliar
terms on first use. Make processor limits explicit; do not describe planned
features as available. Preserve the source-available educational licensing terms.

## Maintain examples and application assets

`public/examples/` contains the actual downloadable assembly files. The example
page renders those files directly through `ExampleCode.astro`, so the displayed
source and downloads stay identical.

After an application release, run:

```sh
npm run sync:app
```

This explicitly copies the repository's version metadata, instruction catalog,
bundled LED counter, application icon, and workbench screenshot into the website.
Review the resulting changes alongside the guides. An ordinary site build uses
the checked-in copies, so it can build without running Python or reading outside
`web/`.

The instruction catalog excludes reserved opcode A5H and groups the other 255
encodings by mnemonic. Search, navigation, pagination, syntax highlighting, and
code-copy controls are provided by Starlight. The home-page LED illustration and
instruction filter add small progressive enhancements; the guides remain readable
without JavaScript. Fonts, scripts, images, and the search index are served locally;
the site does not load an external font or analytics service.

## Validation

From `web/`:

```sh
npm run build
npm run check
python3 scripts/verify-examples.py
```

On Windows, use `py -3 scripts/verify-examples.py` for the last command. Python
3.10+ is needed only for example verification against the repository's engine;
Tk and a graphical display are not required for that check.

`npm run check` runs Astro/TypeScript diagnostics and validates generated internal
links, anchors, assets, page titles, descriptions, and the search index. External
links are not fetched. `check:types` and `check:links` are available separately.
Always build after changing source before checking generated links.

The Python check assembles all seven downloadable programs and every fenced
assembly fragment in the guides. It also executes the examples to verify the LED,
switch, RAM, timer, DAC, and UART observations described in the text.

For visual review, check home, first program, examples, and the instruction catalog
at desktop and mobile widths, in both light and dark themes. Test the mobile menu,
search result navigation, code copying, downloads, LED toggles, and empty catalog
filter results. Search is available in a production preview, not the dev server.

## Deploy to a static host

Build command: `npm run build`. Output directory: `dist/`. When configuring a
host from the repository root, set its project/root directory to **`web`**.
No server adapter, database, or runtime service is required.

Set **`SITE_URL`** to the production origin before building. Astro uses it for
canonical URLs and the sitemap. Without it, local builds work and sitemap
generation is skipped. Do not put a guessed production domain in the source.

For a subdirectory host such as a GitHub project page, also set **`BASE_PATH`**.
Example for a POSIX shell:

```sh
SITE_URL=https://bibekjoshi01.github.io BASE_PATH=/mcs51-studio npm run build
BASE_PATH=/mcs51-studio npm run check
```

PowerShell equivalent:

```powershell
$env:SITE_URL = 'https://bibekjoshi01.github.io'
$env:BASE_PATH = '/mcs51-studio'
npm run build
npm run check
```

Upload the contents of `dist/`, preserving `_astro/`, `pagefind/`, and `examples/`.
Configure the host to serve `404.html` for missing routes. To return to a root-path
local build, remove `SITE_URL`/`BASE_PATH` from the environment and rebuild.

## GitHub Pages workflow

The repository includes `.github/workflows/pages.yml`. Set **Settings → Pages →
Build and deployment → Source** to **GitHub Actions**. The workflow runs on changes
to `web/` or the workflow itself on `main`, and can also be started manually.

It uses Node.js 24 and `npm ci`, builds and checks the website, verifies the assembly
examples, then uploads only `web/dist/` for deployment. GitHub Pages supplies the
production origin and base path, so asset links, search, canonical URLs, and the
sitemap use the actual configured address without hard-coded account settings.

A project repository uses `https://OWNER.github.io/REPOSITORY/`. The exact address
`https://mcs51-studio.github.io/` requires an account or organization named
`mcs51-studio` and a repository named `mcs51-studio.github.io` under that owner.
Naming a repository `mcs51-studio.github.io` under another account does not give it
that hostname. See [GitHub's Pages URL rules](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages).

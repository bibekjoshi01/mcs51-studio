import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// Supply SITE_URL and BASE_PATH when deploying to a domain or a subdirectory.
export default defineConfig({
  site: process.env.SITE_URL,
  base: process.env.BASE_PATH || '/',
  output: 'static',
  trailingSlash: 'always',
  devToolbar: { enabled: false },
  integrations: [starlight({
    title: 'MCS51 Studio',
    description: 'Learn 8051 assembly, understand the debugger, and explore a virtual microcontroller board with MCS51 Studio.',
    logo: { src: './src/assets/logo.svg' },
    favicon: '/favicon.svg',
    disable404Route: true,
    customCss: ['./src/styles/custom.css'],
    social: [{ icon: 'github', label: 'GitHub repository', href: 'https://github.com/bibekjoshi01/mcs51-studio' }],
    components: {
      Hero: './src/components/Hero.astro',
      SiteTitle: './src/components/SiteTitle.astro',
      Footer: './src/components/Footer.astro',
    },
    sidebar: [
      { label: 'Overview', slug: 'index' },
      { label: 'Start here', items: [
        { slug: 'start/introduction' },
        { slug: 'start/installation' },
        { slug: 'start/first-program' },
        { slug: 'start/8051-basics' },
      ] },
      { label: 'Use the workbench', items: [
        { slug: 'workbench/interface' },
        { slug: 'workbench/editor' },
        { slug: 'workbench/debugging' },
        { slug: 'workbench/memory' },
        { slug: 'workbench/projects' },
      ] },
      { label: 'Explore peripherals', items: [
        { slug: 'peripherals/wiring' },
        { slug: 'peripherals/digital-io' },
        { slug: 'peripherals/displays-keypad' },
        { slug: 'peripherals/analogue-motor' },
        { slug: 'peripherals/uart' },
        { slug: 'peripherals/instruments' },
      ] },
      { label: 'Try examples', slug: 'examples' },
      { label: 'Reference', collapsed: true, items: [
        { slug: 'reference/assembly' },
        { slug: 'reference/instructions' },
        { slug: 'reference/shortcuts' },
        { slug: 'reference/processor' },
        { slug: 'reference/limits' },
        { slug: 'reference/troubleshooting' },
        { slug: 'reference/license' },
      ] },
    ],
    credits: false,
    expressiveCode: { themes: ['github-light', 'github-dark'], defaultProps: { wrap: true } },
  })],
});

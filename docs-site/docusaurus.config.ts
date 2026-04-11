import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Lakemeter',
  tagline: 'Databricks Cost Estimation Tool',
  favicon: 'img/favicon.ico',

  future: {
    v4: true,
  },

  url: 'https://cheeyutan.github.io',
  baseUrl: '/lakemeter-opensource/',

  organizationName: 'CheeYuTan',
  projectName: 'lakemeter-opensource',

  onBrokenLinks: 'warn',

  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          routeBasePath: '/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    colorMode: {
      defaultMode: 'dark',
      disableSwitch: false,
      respectPrefersColorScheme: false,
    },
    navbar: {
      title: 'Lakemeter',
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'userGuideSidebar',
          position: 'left',
          label: 'User Guide',
        },
        {
          type: 'docSidebar',
          sidebarId: 'adminGuideSidebar',
          position: 'left',
          label: 'Admin Guide',
        },
        {
          type: 'doc',
          docId: 'changelog',
          position: 'left',
          label: 'Changelog',
        },
        {
          href: 'https://www.databricks.com/product/pricing',
          label: 'Databricks Pricing',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Documentation',
          items: [
            {
              label: 'User Guide',
              to: '/user-guide/overview',
            },
            {
              label: 'Admin Guide',
              to: '/admin-guide/deployment',
            },
          ],
        },
        {
          title: 'Databricks',
          items: [
            {
              label: 'Official Pricing',
              href: 'https://www.databricks.com/product/pricing',
            },
            {
              label: 'Databricks Documentation',
              href: 'https://docs.databricks.com',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Databricks, Inc.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'python', 'yaml'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;

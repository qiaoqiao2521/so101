// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  site: 'https://robot.muqiao.fyi',
  integrations: [
    starlight({
      title: '沐桥机器人资料库',
      description: 'SO101 与 FishBot 的学习路线、官方资源和资料交付说明。',
      favicon: '/favicon.svg',
      defaultLocale: 'root',
      locales: { root: { label: '简体中文', lang: 'zh-CN' } },
      customCss: ['./src/styles/site.css'],
      components: {
        ThemeProvider: './src/components/LightTheme.astro',
        ThemeSelect: './src/components/NoThemeSelect.astro',
      },
      sidebar: [
        { label: '从这里开始', slug: 'start-here' },
        { label: 'SO101 机械臂', items: [
          { label: '学习路线', slug: 'so101' },
          { label: '装配与校准', slug: 'so101/assembly' },
          { label: '模型与仿真', slug: 'so101/simulation' },
        ] },
        { label: 'FishBot 移动机器人', items: [
          { label: '学习路线', slug: 'fishbot' },
          { label: '软件环境', slug: 'fishbot/environment' },
          { label: '建图与导航', slug: 'fishbot/navigation' },
        ] },
        { label: '查阅与交付', items: [
          { label: '常用术语', slug: 'common/glossary' },
          { label: '资料交付说明', slug: 'delivery' },
          { label: '更新记录', slug: 'updates' },
          { label: '来源与使用边界', slug: 'sources' },
        ] },
      ],
      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
      pagination: true,
      lastUpdated: false,
    }),
  ],
});

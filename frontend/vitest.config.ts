import { mergeConfig } from 'vite'
import { configDefaults, defineConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      // Playwright 用例在 e2e/，由 `npm run e2e` 执行，勿交给 Vitest
      exclude: [...configDefaults.exclude, '**/e2e/**'],
    },
  }),
)

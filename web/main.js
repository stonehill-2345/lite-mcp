import { createApp } from 'vue'

// Import global styles
import 'normalize.css'
import 'nprogress/nprogress.css'
import '@/styles/global.scss'

// Import internationalization
import { i18n, getCurrentLocale } from '@/i18n/index.js'

// Import main component
import LiteMCPIndex from '@/LiteMCPIndex.vue'

// Import Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCN from 'element-plus/es/locale/lang/zh-cn'
import enUS from 'element-plus/es/locale/lang/en'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

// Create Vue application
const app = createApp(LiteMCPIndex)

// Configure Element Plus language pack based on current language
const getElementLocale = () => {
  const currentLocale = getCurrentLocale()
  return currentLocale === 'zh-CN' ? zhCN : enUS
}

// Use Element Plus (dynamic language pack configuration)
app.use(ElementPlus, { locale: getElementLocale() })

// Use internationalization
app.use(i18n)

// Register all Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// Note: Since Element Plus does not support dynamic language pack switching,
// we solve this by refreshing the page when language is switched (see AdvancedConfig.vue)

// Mount application
app.mount('#app')

// Enable Vue DevTools in development environment
if (import.meta.env.DEV) {
  app.config.devtools = true
}
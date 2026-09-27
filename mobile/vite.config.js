const { defineConfig } = require('vite')
const uniModule = require('@dcloudio/vite-plugin-uni')
const uniPlugin = uniModule.default || uniModule

module.exports = defineConfig({
  plugins: [uniPlugin()],
})

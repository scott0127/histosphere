/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./components/**/*.{js,vue,ts}",
    "./pages/**/*.{js,vue,ts}",
    "./composables/**/*.{js,vue,ts}",
    "./types/**/*.{js,ts}",
    "./app.vue",
  ],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"Crimson Text"', 'Georgia', 'Cambria', '"Times New Roman"', 'Times', 'serif'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
      },
      colors: {
        // 定義歷史感主題色 (參考附圖風格)
        'history': {
          paper: '#F5E6D3', // 溫暖的米色背景 (類似附圖背景)
          dark: '#3E2723', // 深褐色 (文字/標題)
          brown: '#5D4037', // 中褐色 (次要文字/邊框)
          accent: '#8D6E63', // 淺褐色 (裝飾/次要按鈕)
          light: '#D7CCC8', // 極淺褐 (輸入框背景)
          cream: '#FFF8E1', // 亮米色 (卡片背景)
          gold: '#BCAAA4', // 點綴色
        }
      },
      backgroundImage: {
        'paper-pattern': "url('https://www.transparenttextures.com/patterns/cream-paper.png')",
      }
    },
  },
  plugins: [],
}

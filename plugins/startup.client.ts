export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.hook('app:mounted', () => {
    window.dispatchEvent(new Event('histosphere:app-mounted'));
  });
});

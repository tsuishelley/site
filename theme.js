// Runs from <head> so the saved theme is applied before first paint.
(function () {
  if (localStorage.getItem('theme') === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  }

  function bind() {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const root = document.documentElement;
      const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';

      root.classList.add('theme-switching');
      root.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      // read a layout property to flush the new colours while transitions are
      // still off, so no element is left with an old -> new pair to animate
      void root.offsetWidth;
      root.classList.remove('theme-switching');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();

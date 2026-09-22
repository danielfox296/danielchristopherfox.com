/* light.js — scroll reveal, cymatics init, nav. Robust: content
   is never left stuck invisible (initial in-view pass + hard fallback). */
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------- scroll reveal ---------- */
  var targets = Array.prototype.slice.call(document.querySelectorAll(
    '.hero .eyebrow, .hero h1, .hero p.sub, .hero-now, .hero-portrait, .lead, .feature .copy, .plate, .break, .row, .warl, .contact .inner > *'
  ));
  targets.forEach(function (el) { el.classList.add('rev'); });
  function reveal(el) { el.classList.add('in'); }
  function inView(el) {
    var r = el.getBoundingClientRect();
    var vh = window.innerHeight || document.documentElement.clientHeight;
    return r.top < vh * 0.92 && r.bottom > 0;
  }
  var io = null;
  if ('IntersectionObserver' in window) {
    io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { reveal(e.target); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    targets.forEach(function (el) { io.observe(el); });
  }
  requestAnimationFrame(function () { requestAnimationFrame(function () {
    targets.forEach(function (el) { if (!el.classList.contains('in') && inView(el)) { reveal(el); if (io) io.unobserve(el); } });
  }); });
  setTimeout(function () { targets.forEach(reveal); }, 1600);

  /* ---------- cymatics ---------- */
  var canvas = document.getElementById('cymatics');
  if (canvas && window.CymaticsField) {
    var field = new window.CymaticsField(canvas, { res: 84, speed: 1, density: 0.6 });
    window.__cymatics = field;
    field.render();
    if (!reduce) {
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (entries) {
          entries.forEach(function (e) { if (e.isIntersecting) field.start(); else field.stop(); });
        }, { threshold: 0.05 }).observe(canvas);
      } else { field.start(); }
    }
  }

  /* nav lives in the shared header partial now (see _src/partials/header.html) */
})();

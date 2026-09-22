/* =============================================================
   cymatics.js — Chladni nodal-line field, rendered as flowing
   contour line-work (marching squares). Editorial, not gimmicky.
   - Superposes a handful of plate modes with slowly drifting
     amplitudes so the pattern evolves organically.
   - Draws the f=0 nodal line boldest, with a couple of faint
     offset iso-levels for a topographic feel.
   - Colour is read live from --cy-ink / --cy-bg CSS vars so the
     Tweaks panel can recolour it without touching JS.
   ============================================================= */
(function () {
  function CymaticsField(canvas, opts) {
    opts = opts || {};
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.res = opts.res || 84;                 // grid cells per side
    this.speed = opts.speed != null ? opts.speed : 1;
    this.density = opts.density != null ? opts.density : 1; // 0..1 line intensity
    this.running = false;
    this.t = 0;
    // plate modes [n, m] + drift rate + phase
    this.modes = [
      { n: 1, m: 2, r: 0.045, p: 0.0 },
      { n: 2, m: 3, r: 0.031, p: 1.7 },
      { n: 3, m: 1, r: 0.027, p: 3.1 },
      { n: 2, m: 5, r: 0.019, p: 4.6 },
      { n: 4, m: 2, r: 0.037, p: 0.8 },
      { n: 1, m: 4, r: 0.023, p: 2.4 }
    ];
    this.levels = [
      { v: 0.0,  w: 1.55, a: 1.0 },            // the nodal line — boldest
      { v: 0.32, w: 0.9,  a: 0.34 },
      { v: -0.32,w: 0.9,  a: 0.34 },
      { v: 0.7,  w: 0.7,  a: 0.16 },
      { v: -0.7, w: 0.7,  a: 0.16 }
    ];
    this._field = null;
    this._resize();
    this._onResize = this._resize.bind(this);
    window.addEventListener('resize', this._onResize);
  }

  CymaticsField.prototype._resize = function () {
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var r = this.canvas.getBoundingClientRect();
    this.cw = Math.max(1, Math.round(r.width));
    this.ch = Math.max(1, Math.round(r.height));
    this.canvas.width = this.cw * dpr;
    this.canvas.height = this.ch * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };

  CymaticsField.prototype._computeField = function () {
    var R = this.res, N = R + 1;
    if (!this._field || this._field.length !== N * N) this._field = new Float32Array(N * N);
    var f = this._field, modes = this.modes, t = this.t;
    var w = new Array(modes.length);
    for (var k = 0; k < modes.length; k++) {
      w[k] = Math.sin(t * modes[k].r + modes[k].p);
    }
    var PI = Math.PI;
    for (var j = 0; j < N; j++) {
      var y = j / R;
      for (var i = 0; i < N; i++) {
        var x = i / R;
        var s = 0;
        for (var k2 = 0; k2 < modes.length; k2++) {
          var md = modes[k2];
          s += w[k2] * (
            Math.cos(md.n * PI * x) * Math.cos(md.m * PI * y) -
            Math.cos(md.m * PI * x) * Math.cos(md.n * PI * y)
          );
        }
        f[j * N + i] = s;
      }
    }
  };

  // marching squares for one iso level → stroke segments
  CymaticsField.prototype._drawLevel = function (level, ink) {
    var R = this.res, N = R + 1, f = this._field;
    var sx = this.cw / R, sy = this.ch / R;
    var lv = level.v, ctx = this.ctx;
    ctx.beginPath();
    function ix(a, b, va, vb) { return (lv - va) / (vb - va); }
    for (var j = 0; j < R; j++) {
      for (var i = 0; i < R; i++) {
        var tl = f[j * N + i], tr = f[j * N + i + 1];
        var bl = f[(j + 1) * N + i], br = f[(j + 1) * N + i + 1];
        var c = 0;
        if (tl > lv) c |= 8;
        if (tr > lv) c |= 4;
        if (br > lv) c |= 2;
        if (bl > lv) c |= 1;
        if (c === 0 || c === 15) continue;
        var x0 = i * sx, y0 = j * sy, x1 = x0 + sx, y1 = y0 + sy;
        // edge crossings
        var top = [x0 + ix(0, 0, tl, tr) * sx, y0];
        var rgt = [x1, y0 + ix(0, 0, tr, br) * sy];
        var bot = [x0 + ix(0, 0, bl, br) * sx, y1];
        var lft = [x0, y0 + ix(0, 0, tl, bl) * sy];
        var seg = [];
        switch (c) {
          case 1: case 14: seg = [lft, bot]; break;
          case 2: case 13: seg = [bot, rgt]; break;
          case 3: case 12: seg = [lft, rgt]; break;
          case 4: case 11: seg = [top, rgt]; break;
          case 5: seg = [lft, top, bot, rgt]; break;
          case 6: case 9: seg = [top, bot]; break;
          case 7: case 8: seg = [lft, top]; break;
          case 10: seg = [top, rgt, lft, bot]; break;
        }
        for (var p = 0; p < seg.length; p += 2) {
          ctx.moveTo(seg[p][0], seg[p][1]);
          ctx.lineTo(seg[p + 1][0], seg[p + 1][1]);
        }
      }
    }
    ctx.lineWidth = level.w;
    ctx.strokeStyle = ink;
    ctx.globalAlpha = level.a * this.density;
    ctx.stroke();
    ctx.globalAlpha = 1;
  };

  CymaticsField.prototype._readColors = function () {
    var cs = getComputedStyle(this.canvas);
    this.ink = cs.getPropertyValue('--cy-ink').trim() || '#2E8B4F';
  };

  CymaticsField.prototype.render = function () {
    this._readColors();
    this.ctx.clearRect(0, 0, this.cw, this.ch);
    this.ctx.lineJoin = 'round';
    this.ctx.lineCap = 'round';
    this._computeField();
    for (var i = 0; i < this.levels.length; i++) this._drawLevel(this.levels[i], this.ink);
  };

  CymaticsField.prototype._loop = function (ts) {
    if (!this.running) return;
    if (!this._last) this._last = ts;
    var dt = Math.min(64, ts - this._last);
    this._last = ts;
    // throttle ~36fps
    this._acc = (this._acc || 0) + dt;
    if (this._acc >= 27) {
      this.t += (this._acc / 1000) * 60 * this.speed;
      this._acc = 0;
      this.render();
    }
    this._raf = requestAnimationFrame(this._loop.bind(this));
  };

  CymaticsField.prototype.start = function () {
    if (this.running) return;
    this.running = true; this._last = 0; this._acc = 0;
    this._raf = requestAnimationFrame(this._loop.bind(this));
  };
  CymaticsField.prototype.stop = function () {
    this.running = false;
    if (this._raf) cancelAnimationFrame(this._raf);
  };
  CymaticsField.prototype.setDensity = function (d) { this.density = d; this.render(); };
  CymaticsField.prototype.setSpeed = function (s) { this.speed = s; };

  window.CymaticsField = CymaticsField;
})();

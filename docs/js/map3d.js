/* TrueCombat: Platinum - 3D map viewer for the map pages.
   Loads docs/img/maps/3d-<map>.bin (written by tools/website/map3d.py) on request and draws it with
   WebGL 2: the map's own baked lighting, a roof cut, callouts, spawns and bomb sites.
   Mouse: drag to orbit, right-drag or Shift-drag to pan, wheel to zoom. Touch: one finger orbits,
   two fingers pan and pinch. Keyboard (canvas focused): arrows orbit, Shift+arrows pan, + and - zoom, R resets. */
(function () {
  'use strict';
  var boxes = document.querySelectorAll('[data-map3d]');
  if (!boxes.length) return;
  var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function m4persp(fovy, aspect, near, far) {
    var f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
    return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
  }
  function m4look(e, t, u) {
    var z = norm([e[0] - t[0], e[1] - t[1], e[2] - t[2]]), x = norm(cross(u, z)), y = cross(z, x);
    return [x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, e), -dot(y, e), -dot(z, e), 1];
  }
  function m4mul(a, b) {
    var o = new Array(16);
    for (var c = 0; c < 4; c++) for (var r = 0; r < 4; r++) {
      o[c * 4 + r] = a[r] * b[c * 4] + a[4 + r] * b[c * 4 + 1] + a[8 + r] * b[c * 4 + 2] + a[12 + r] * b[c * 4 + 3];
    }
    return o;
  }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function norm(a) { var l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }

  var VS = '#version 300 es\n' +
    'in vec3 q; in vec3 c; uniform mat4 mvp; uniform vec3 lo; uniform vec3 sz; out vec3 vc; out vec3 wp;\n' +
    'void main(){ vec3 p = lo + q / 65535.0 * sz; wp = p; vc = c; gl_Position = mvp * vec4(p.x, p.z, -p.y, 1.0); }';
  var FS = '#version 300 es\nprecision highp float;\n' +
    'in vec3 vc; in vec3 wp; uniform float cut; uniform float lo_z; uniform float hi_z; out vec4 o;\n' +
    'void main(){ if (wp.z > cut) discard;\n' +
    ' vec3 n = normalize(cross(dFdx(wp), dFdy(wp)));\n' +
    ' float key = max(dot(n, normalize(vec3(0.45, -0.35, 0.82))), 0.0), fill = max(dot(n, normalize(vec3(-0.6, 0.5, 0.3))), 0.0);\n' +
    ' float sun = 0.30 + 0.55 * key + 0.18 * fill + 0.12 * max(n.z, 0.0);\n' +
    ' vec3 base = pow(vc / 255.0, vec3(0.85));\n' +
    ' float h = clamp((wp.z - lo_z) / max(1.0, hi_z - lo_z), 0.0, 1.0);\n' +
    ' vec3 col = mix(base, vec3(0.62, 0.66, 0.74), 0.35) * sun * (0.72 + 0.3 * h);\n' +
    ' o = vec4(pow(col, vec3(0.95)), 1.0); }';

  function shader(gl, type, src) {
    var s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }

  function parse(buf) {
    var dv = new DataView(buf);
    if (String.fromCharCode(dv.getUint8(0), dv.getUint8(1), dv.getUint8(2), dv.getUint8(3)) !== 'TCM1') throw new Error('bad model');
    var nv = dv.getUint32(4, true), ni = dv.getUint32(8, true), off = 12;
    var lo = [], sz = [];
    for (var i = 0; i < 3; i++) lo.push(dv.getFloat32(off + i * 4, true));
    for (i = 0; i < 3; i++) sz.push(dv.getFloat32(off + 12 + i * 4, true));
    off += 24;
    var q = new Uint16Array(buf, off, nv * 3); off += nv * 6;
    var c = new Uint8Array(buf, off, nv * 3); off += nv * 3; off += (4 - off % 4) % 4;
    var idx = new Uint32Array(buf, off, ni); off += ni * 4;
    var jl = dv.getUint32(off, true);
    var meta = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, off + 4, jl)));
    return { lo: lo, sz: sz, q: q, c: c, idx: idx, meta: meta };
  }

  function start(box) {
    var map = box.getAttribute('data-map3d');
    var L = { loading: box.getAttribute('data-loading') || 'Loading the map…', fail: box.getAttribute('data-fail') || 'Your browser cannot show the 3D view.' };
    var stage = box.querySelector('.m3d-stage'), status = box.querySelector('.m3d-status');
    var canvas = document.createElement('canvas');
    canvas.tabIndex = 0;
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', box.getAttribute('data-label') || '3D view of the map');
    stage.appendChild(canvas);
    var labels = document.createElement('div'); labels.className = 'm3d-labels'; labels.setAttribute('aria-hidden', 'true');
    stage.appendChild(labels);
    var gl = canvas.getContext('webgl2', { antialias: true });
    if (!gl) { status.textContent = L.fail; return; }
    status.textContent = L.loading;
    box.classList.add('on');
    fetch(box.getAttribute('data-src')).then(function (r) { if (!r.ok) throw new Error(r.status); return r.arrayBuffer(); }).then(function (buf) {
      var m = parse(buf);
      var prog = gl.createProgram();
      gl.attachShader(prog, shader(gl, gl.VERTEX_SHADER, VS)); gl.attachShader(prog, shader(gl, gl.FRAGMENT_SHADER, FS));
      gl.bindAttribLocation(prog, 0, 'q'); gl.bindAttribLocation(prog, 1, 'c'); gl.linkProgram(prog);
      var vao = gl.createVertexArray(); gl.bindVertexArray(vao);
      var b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, m.q, gl.STATIC_DRAW);
      gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 3, gl.UNSIGNED_SHORT, false, 0, 0);
      b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, m.c, gl.STATIC_DRAW);
      gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 3, gl.UNSIGNED_BYTE, false, 0, 0);
      b = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, b); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, m.idx, gl.STATIC_DRAW);
      var U = {}; ['mvp', 'lo', 'sz', 'cut', 'lo_z', 'hi_z'].forEach(function (n) { U[n] = gl.getUniformLocation(prog, n); });

      // the play area: spawns and callouts set the zoom; heights set the roof cut range
      var pts = [].concat(m.meta.spawns.terrorists, m.meta.spawns.specops, m.meta.callouts.map(function (c) { return c.p; }));
      var cx = 0, cy = 0, minz = Infinity, maxz = -Infinity, span = 0;
      pts.forEach(function (p) { cx += p[0]; cy += p[1]; minz = Math.min(minz, p[2]); maxz = Math.max(maxz, p[2]); });
      cx /= pts.length; cy /= pts.length;
      pts.forEach(function (p) { span = Math.max(span, Math.hypot(p[0] - cx, p[1] - cy)); });
      var zLo = minz - 64, zHi = m.lo[2] + m.sz[2];
      var home = { yaw: -0.6, pitch: 0.95, dist: span * 2.1, tx: cx, ty: cy, tz: (minz + maxz) / 2 };
      var cam = Object.assign({}, home);
      var cut = zHi;
      var slider = box.querySelector('.m3d-cut');
      if (slider) {
        slider.min = Math.round(minz); slider.max = Math.round(zHi); slider.value = slider.max; slider.disabled = false;
        slider.addEventListener('input', function () { cut = +slider.value; draw(); });
      }
      var showLabels = true;
      var toggle = box.querySelector('.m3d-labels-toggle');
      if (toggle) toggle.addEventListener('change', function () { showLabels = toggle.checked; draw(); });
      var reset = box.querySelector('.m3d-reset');
      if (reset) reset.addEventListener('click', function () { cam = Object.assign({}, home); cut = zHi; if (slider) slider.value = slider.max; draw(); });

      var items = [];
      function label(text, p, cls) {
        var el = document.createElement('span'); el.className = 'm3d-l ' + cls; el.textContent = text; labels.appendChild(el);
        items.push({ el: el, p: p });
      }
      m.meta.callouts.forEach(function (c) { label(c.name, [c.p[0], c.p[1], c.p[2] + 24], 'call'); });
      m.meta.sites.forEach(function (s) { label(s.site, [(s.mins[0] + s.maxs[0]) / 2, (s.mins[1] + s.maxs[1]) / 2, s.mins[2] + 40], 'site'); });
      m.meta.flags.forEach(function (f) { label('⚑', [f.p[0], f.p[1], f.p[2] + 40], 'flag ' + f.team); });
      ['terrorists', 'specops'].forEach(function (t) {
        var s = m.meta.spawns[t]; if (!s.length) return;
        var a = [0, 0, 0]; s.forEach(function (p) { a[0] += p[0]; a[1] += p[1]; a[2] += p[2]; });
        label(t === 'terrorists' ? 'T' : 'SF', [a[0] / s.length, a[1] / s.length, a[2] / s.length + 40], 'spawn ' + t);
      });

      var queued = false;
      function draw() { if (!queued) { queued = true; requestAnimationFrame(frame); } }
      function frame() {
        queued = false;
        var dpr = Math.min(window.devicePixelRatio || 1, 2), w = stage.clientWidth, h = stage.clientHeight;
        if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.clearColor(0.051, 0.063, 0.086, 1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        gl.enable(gl.DEPTH_TEST);
        var cp = Math.cos(cam.pitch), eye = [cam.tx + Math.cos(cam.yaw) * cp * cam.dist, cam.tz + Math.sin(cam.pitch) * cam.dist, -(cam.ty + Math.sin(cam.yaw) * cp * cam.dist)];
        var tgt = [cam.tx, cam.tz, -cam.ty];
        var mvp = m4mul(m4persp(0.9, w / h, Math.max(8, cam.dist / 200), cam.dist * 8 + 20000), m4look(eye, tgt, [0, 1, 0]));
        gl.useProgram(prog);
        gl.uniformMatrix4fv(U.mvp, false, mvp); gl.uniform3fv(U.lo, m.lo); gl.uniform3fv(U.sz, m.sz);
        gl.uniform1f(U.cut, cut); gl.uniform1f(U.lo_z, zLo); gl.uniform1f(U.hi_z, zHi);
        gl.bindVertexArray(vao); gl.drawElements(gl.TRIANGLES, m.idx.length, gl.UNSIGNED_INT, 0);
        labels.hidden = !showLabels;
        if (!showLabels) return;
        items.forEach(function (it) {
          var p = it.p, x = p[0], y = p[2], z = -p[1];
          var cx4 = mvp[0] * x + mvp[4] * y + mvp[8] * z + mvp[12], cy4 = mvp[1] * x + mvp[5] * y + mvp[9] * z + mvp[13], cw = mvp[3] * x + mvp[7] * y + mvp[11] * z + mvp[15];
          var vis = cw > 0 && p[2] - 60 <= cut;
          if (vis) { var sx = (cx4 / cw * 0.5 + 0.5) * w, sy = (1 - (cy4 / cw * 0.5 + 0.5)) * h; vis = sx > -40 && sx < w + 40 && sy > -20 && sy < h + 20; }
          it.el.style.display = vis ? '' : 'none';
          if (vis) it.el.style.transform = 'translate(' + sx.toFixed(1) + 'px,' + sy.toFixed(1) + 'px) translate(-50%,-100%)';
        });
      }
      status.textContent = '';
      box.classList.add('ready');
      draw();
      window.addEventListener('resize', draw);

      // input
      var drag = null, touches = {};
      function orbit(dx, dy) { cam.yaw -= dx * 0.006; cam.pitch = Math.max(0.12, Math.min(1.52, cam.pitch + dy * 0.005)); }
      function pan(dx, dy) {
        // screen right and screen up, projected onto the ground plane (game x/y)
        var k = cam.dist / stage.clientHeight, s = Math.sin(cam.yaw), c = Math.cos(cam.yaw);
        cam.tx += (-s * dx - c * dy) * k * -1; cam.ty += (c * dx - s * dy) * k * -1;
      }
      function zoom(f) { cam.dist = Math.max(span * 0.15, Math.min(span * 6, cam.dist * f)); }
      canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });
      canvas.addEventListener('pointerdown', function (e) {
        canvas.setPointerCapture(e.pointerId); touches[e.pointerId] = [e.clientX, e.clientY];
        drag = { x: e.clientX, y: e.clientY, pan: e.button === 2 || e.shiftKey };
      });
      canvas.addEventListener('pointermove', function (e) {
        if (!drag || !touches[e.pointerId]) return;
        var ids = Object.keys(touches);
        if (ids.length === 2) {
          var o = touches[e.pointerId], other = touches[ids[0] == e.pointerId ? ids[1] : ids[0]];
          var d0 = Math.hypot(o[0] - other[0], o[1] - other[1]), d1 = Math.hypot(e.clientX - other[0], e.clientY - other[1]);
          if (d0 > 0) zoom(d0 / d1);
          pan((e.clientX - o[0]) / 2, (e.clientY - o[1]) / 2);
        } else if (drag.pan) pan(e.clientX - drag.x, e.clientY - drag.y);
        else orbit(e.clientX - drag.x, e.clientY - drag.y);
        touches[e.pointerId] = [e.clientX, e.clientY]; drag.x = e.clientX; drag.y = e.clientY; draw();
      });
      function up(e) { delete touches[e.pointerId]; if (!Object.keys(touches).length) drag = null; }
      canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', up);
      canvas.addEventListener('wheel', function (e) { e.preventDefault(); zoom(Math.exp(e.deltaY * 0.0012)); draw(); }, { passive: false });
      canvas.addEventListener('keydown', function (e) {
        var k = e.key, used = true;
        if (k === 'ArrowLeft') e.shiftKey ? pan(40, 0) : orbit(-30, 0);
        else if (k === 'ArrowRight') e.shiftKey ? pan(-40, 0) : orbit(30, 0);
        else if (k === 'ArrowUp') e.shiftKey ? pan(0, 40) : orbit(0, 20);
        else if (k === 'ArrowDown') e.shiftKey ? pan(0, -40) : orbit(0, -20);
        else if (k === '+' || k === '=') zoom(0.85);
        else if (k === '-' || k === '_') zoom(1.18);
        else if (k === 'r' || k === 'R') cam = Object.assign({}, home);
        else used = false;
        if (used) { e.preventDefault(); draw(); }
      });
      // a slow quarter turn on open shows that the view is 3D; skipped for reduced motion
      if (!calm) {
        var t0 = performance.now(), y0 = cam.yaw;
        (function spin(t) {
          if (drag) return;
          var k = Math.min(1, (t - t0) / 2400); cam.yaw = y0 + 0.5 * (1 - Math.pow(1 - k, 3)); draw();
          if (k < 1) requestAnimationFrame(spin);
        })(t0);
      }
    }).catch(function () { status.textContent = L.fail; });
  }

  Array.prototype.forEach.call(boxes, function (box) {
    var btn = box.querySelector('.m3d-open');
    if (btn) btn.addEventListener('click', function () { btn.hidden = true; start(box); }, { once: true });
  });
})();

// Gallery page served at /. The phone does all the work; the ESP only sends /api/list (names + sizes),
// tiny thumbnails (/t), full photos (/f) and zips (/api/zip).
#pragma once
static const char PAGE[] PROGMEM = R"HTML(<!doctype html>
<html lang=en><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name=color-scheme content="dark light">
<title>kukucs</title>
<style>
:root{--bg:#0f0f12;--fg:#f2f2f5;--mute:#8d8d99;--card:#1b1b21;--acc:#ffb13b;--bad:#ff5a5a}
@media (prefers-color-scheme:light){:root{--bg:#f6f6f8;--fg:#18181c;--mute:#6b6b76;--card:#e6e6ea}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.4 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;z-index:1;display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:12px 16px;
  background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px)}
h1{margin:0;font-size:20px;letter-spacing:.5px}
h1 span{color:var(--acc)}
#info{color:var(--mute);font-size:13px;flex:1;min-width:120px}
.pill{font-size:12px;padding:3px 9px;border-radius:99px;background:var(--card);color:var(--mute);white-space:nowrap}
.pill.warn{background:var(--acc);color:#000}
button,.btn{font:inherit;color:var(--fg);background:var(--card);border:0;border-radius:10px;padding:9px 14px;cursor:pointer;text-decoration:none}
button:focus-visible,.btn:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
button:disabled{opacity:.4}
.bad{color:var(--bad)}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(108px,1fr));gap:4px;padding:0 4px 16px}
.tile{position:relative;padding:0;border-radius:6px;overflow:hidden;aspect-ratio:4/3;background:var(--card)}
.tile img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .12s}
.selecting .tile::after{content:'';position:absolute;top:6px;right:6px;width:22px;height:22px;border-radius:50%;
  border:2px solid #fff;background:#0006}
.tile.on::after{content:'✓'!important;background:var(--acc)!important;border-color:var(--acc)!important;color:#000;
  font:bold 14px/18px system-ui;text-align:center}
.tile.on img{transform:scale(.9)}
#empty{grid-column:1/-1;text-align:center;color:var(--mute);padding:64px 16px}
footer{color:var(--mute);font-size:12px;text-align:center;padding:8px 16px 96px}
#selbar{position:fixed;left:0;right:0;bottom:0;display:flex;gap:8px;align-items:center;padding:12px 16px calc(12px + env(safe-area-inset-bottom));
  background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(10px);border-top:1px solid var(--card)}
#selbar span{flex:1;font-size:14px}
dialog{border:0;padding:0;background:#000;color:#fff;width:100vw;height:100dvh;max-width:none;max-height:none}
dialog::backdrop{background:#000}
#big{width:100%;height:calc(100dvh - 64px);object-fit:contain;display:block;touch-action:pan-y}
.bar{display:flex;gap:8px;align-items:center;padding:12px 16px;height:64px}
.bar .name{flex:1;font-size:13px;color:#aaa;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar button,.bar .btn{background:#222;color:#fff}
#shoot{position:fixed;left:50%;bottom:calc(20px + env(safe-area-inset-bottom));transform:translateX(-50%);z-index:2;
  display:flex;align-items:center;gap:10px;padding:14px 26px;border-radius:99px;background:var(--acc);color:#000;
  font-weight:600;font-size:16px;box-shadow:0 4px 18px #0008;white-space:nowrap}
#shoot svg{width:22px;height:22px}
#shoot:active{transform:translateX(-50%) scale(.96)}
#shoot:disabled{opacity:1;animation:pulse .8s infinite alternate}
@keyframes pulse{to{opacity:.5}}
#toast{position:fixed;left:50%;bottom:110px;transform:translateX(-50%);background:var(--card);color:var(--fg);
  padding:8px 14px;border-radius:99px;font-size:13px;z-index:3}
[hidden]{display:none!important}
</style>
<header><h1><span>●</span> kukucs</h1><span id=where class=pill hidden></span><div id=info>loading…</div>
  <button id=selbtn hidden>Select</button>
</header>
<main id=grid></main>
<footer>If downloads don't start, open <b>http://192.168.4.1</b> in your browser instead of this popup.</footer>
<div id=selbar hidden><span id=selcount>0 selected</span>
  <button id=selall>All</button><button id=selsave disabled>Save</button>
  <button id=seldel class=bad disabled>Delete</button><button id=selcancel>Done</button></div>
<button id=shoot><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true">
  <path d="M4 7h3l2-3h6l2 3h3a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z"/><circle cx="12" cy="13" r="4"/></svg>
  <span id=shootlbl>Take photo</span></button>
<div id=toast hidden></div>
<form id=zipform method=post action="/api/zip" hidden><input name=n></form>
<dialog id=view>
  <img id=big alt="">
  <div class=bar><span class=name id=name></span>
    <button id=prev aria-label=Previous>‹</button><button id=next aria-label=Next>›</button>
    <a class=btn id=dl download>Save</a><button id=del class=bad>Delete</button><button id=close aria-label=Close>✕</button>
  </div>
</dialog>
<script>
const $ = s => document.querySelector(s);
let files = [], cur = -1, selecting = false;
const sel = new Set();
const kb = n => n > 1073741824 ? (n / 1073741824).toFixed(1) + ' GB' : n > 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.round(n / 1024) + ' KB';
const post = (url, data) => fetch(url, {method: 'POST', body: new URLSearchParams(data)});

// give the camera the phone's clock, so photos get real dates
post('/api/time', {t: Math.floor(Date.now() / 1000), tz: -new Date().getTimezoneOffset()});

let sig = '';
async function load(d) {
  d = d || await (await fetch('/api/list')).json();
  files = d.files.sort((a, b) => b.n.localeCompare(a.n));   // newest first
  sig = files.map(f => f.n).join() + d.sd;
  for (const n of [...sel]) if (!files.some(f => f.n == n)) sel.delete(n);
  $('#info').textContent = `${files.length} photo${files.length == 1 ? '' : 's'} · ${kb(d.free)} free`;
  $('#where').hidden = false;
  $('#where').textContent = d.sd ? 'SD card' : 'No SD card · internal memory';
  $('#where').classList.toggle('warn', !d.sd);
  $('#where').title = d.sd ? '' : 'Small photos, about 30 fit. Insert a FAT32 microSD card; these move to it automatically.';
  $('#selbtn').hidden = !files.length || selecting;
  const g = $('#grid');
  g.replaceChildren();
  if (!files.length) { g.innerHTML = '<div id=empty>No photos yet.<br>Press the button to take one.</div>'; setSelecting(false); return; }
  files.forEach((f, i) => {
    const b = document.createElement('button');
    b.className = 'tile' + (sel.has(f.n) ? ' on' : '');
    b.setAttribute('aria-label', f.n);
    const im = new Image();
    im.loading = 'lazy'; im.alt = '';
    im.src = '/t?n=' + f.n;
    im.onerror = () => { im.onerror = null; im.src = '/f?n=' + f.n; };   // older photos have no thumbnail
    b.append(im);
    b.onclick = () => selecting ? toggle(f.n, b) : show(i);
    g.append(b);
  });
  updateSel();
}

// --- selection
function setSelecting(on) {
  selecting = on;
  $('#shoot').hidden = on;
  if (!on) sel.clear();
  document.body.classList.toggle('selecting', on);
  $('#selbar').hidden = !on;
  $('#selbtn').hidden = on || !files.length;
  document.querySelectorAll('.tile.on').forEach(t => t.classList.toggle('on', sel.has(t.getAttribute('aria-label'))));
  updateSel();
}
function toggle(n, tile) {
  sel.has(n) ? sel.delete(n) : sel.add(n);
  tile.classList.toggle('on', sel.has(n));
  updateSel();
}
function updateSel() {
  const c = sel.size, size = files.filter(f => sel.has(f.n)).reduce((a, f) => a + f.s, 0);
  $('#selcount').textContent = c ? `${c} selected · ${kb(size)}` : 'Tap photos to select';
  $('#selsave').disabled = $('#seldel').disabled = !c;
  $('#selall').textContent = c == files.length ? 'None' : 'All';
}
$('#selbtn').onclick = () => setSelecting(true);
$('#selcancel').onclick = () => setSelecting(false);
$('#selall').onclick = () => {
  const all = sel.size != files.length;
  sel.clear();
  if (all) files.forEach(f => sel.add(f.n));
  document.querySelectorAll('.tile').forEach(t => t.classList.toggle('on', sel.has(t.getAttribute('aria-label'))));
  updateSel();
};
$('#selsave').onclick = () => {   // a real form post, so the browser saves the zip as a download
  $('#zipform').n.value = [...sel].join(',');
  $('#zipform').submit();
};
$('#seldel').onclick = async () => {
  if (!confirm(`Delete ${sel.size} photo${sel.size == 1 ? '' : 's'}?`)) return;
  await post('/api/del', {n: [...sel].join(',')});
  setSelecting(false);
  load();
};

// --- remote shutter
function toast(t) {
  $('#toast').textContent = t;
  $('#toast').hidden = false;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => $('#toast').hidden = true, 2000);
}
$('#shoot').onclick = async () => {
  $('#shoot').disabled = true;   // one shot at a time: the camera needs about a second
  $('#shootlbl').textContent = 'Taking…';
  try {
    const r = await fetch('/api/shoot', {method: 'POST'});
    if (!r.ok) throw 0;
    toast('Saved ' + (await r.json()).n);
    await load();
  } catch (e) {
    toast('Photo failed');
  }
  $('#shoot').disabled = false;
  $('#shootlbl').textContent = 'Take photo';
};

// --- full-screen viewer
function show(i) {
  if (i < 0 || i >= files.length) return;
  cur = i;
  const n = files[i].n;
  $('#big').src = '/f?n=' + n;
  $('#name').textContent = `${n} · ${kb(files[i].s)}`;
  $('#dl').href = '/f?n=' + n + '&dl=1';
  $('#dl').setAttribute('download', n);
  if (!$('#view').open) $('#view').showModal();
}
$('#prev').onclick = () => show(cur - 1);
$('#next').onclick = () => show(cur + 1);
$('#close').onclick = () => $('#view').close();
$('#del').onclick = async () => {
  if (!confirm('Delete this photo?')) return;
  await post('/api/del', {n: files[cur].n});
  $('#view').close();
  load();
};
document.onkeydown = e => {
  if (!$('#view').open) return;
  if (e.key == 'ArrowLeft') show(cur - 1);
  if (e.key == 'ArrowRight') show(cur + 1);
};
let x0 = null;
$('#big').ontouchstart = e => x0 = e.touches[0].clientX;
$('#big').ontouchend = e => {
  const dx = e.changedTouches[0].clientX - x0;
  if (Math.abs(dx) > 50) show(cur + (dx < 0 ? 1 : -1));
};
load().catch(() => $('#info').textContent = 'Could not reach the camera');
// pick up photos taken while the page is open; paused when the screen is off, so the hotspot can still time out
setInterval(async () => {
  if (document.hidden || $('#view').open) return;
  try {
    const d = await (await fetch('/api/list')).json();
    if (d.files.map(f => f.n).sort((a, b) => b.localeCompare(a)).join() + d.sd != sig) load(d);
  } catch (e) {}
}, 5000);
</script>
</html>)HTML";

/* WebDisplays YT Suite v0.2 — SponsorBlock + Return YouTube Dislike + Enhancer portu.
 * Chrome eklentisi DEGIL: MCEF'e executeJavaScript ile enjekte edilen tek script.
 * Seçiciler/endpoints kaynak repolardan doğrulanmıştır (ajayyy/SponsorBlock,
 * Anarios/return-youtube-dislike UserScript, YouTube-Enhancer/extension). */
(function () {
  if (window.__wdYtSuite) return;
  window.__wdYtSuite = true;
  var cfg = window.__wdYtCfg || {};

  function player() { return document.getElementById('movie_player'); }
  function video() { return document.querySelector('video'); }
  function videoId() {
    try {
      var p = player();
      if (p && p.getVideoData) {
        var d = p.getVideoData();
        if (d && d.video_id) return d.video_id;
      }
    } catch (e) {}
    var m = location.href.match(/[?&]v=([\w-]{11})|youtu\.be\/([\w-]{11})|\/embed\/([\w-]{11})/);
    return m ? (m[1] || m[2] || m[3]) : null;
  }
  function toast(t) {
    try {
      var d = document.createElement('div');
      d.textContent = t;
      d.style.cssText = 'position:absolute;right:12px;bottom:90px;z-index:99999;background:rgba(0,0,0,.85);color:#fff;padding:6px 10px;border-radius:4px;font:13px sans-serif;';
      (player() || document.body).appendChild(d);
      setTimeout(function () { d.remove(); }, 1600);
    } catch (e) {}
  }
  function nf(n) { try { return new Intl.NumberFormat('tr-TR').format(n); } catch (e) { return '' + n; } }

  /* ---- SponsorBlock (skipSegments prefix-API; videoID tam yazilir, yanit süzülür) ---- */
  var sbSegs = [], curId = '';
  function sbLoad(id) {
    if (!cfg.sponsorblock) { sbSegs = []; return; }
    var cats = JSON.stringify(cfg.sbCategories || ['sponsor', 'selfpromo', 'interaction', 'intro', 'outro', 'filler']);
    fetch('https://sponsor.ajay.app/api/skipSegments/' + id + '?categories=' + encodeURIComponent(cats))
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (j) {
        var entry = (j || []).filter(function (v) { return v.videoID === id; })[0];
        sbSegs = entry && entry.segments ? entry.segments : [];
      }).catch(function () { sbSegs = []; });
  }
  function sbTick() {
    var v = video(); if (!v || !sbSegs.length) return;
    for (var i = 0; i < sbSegs.length; i++) {
      var s = sbSegs[i]; if (!s.segment) continue;
      var a = s.segment[0], b = s.segment[1];
      if (v.currentTime >= a && v.currentTime < b - 0.3) {
        v.currentTime = b;
        toast('⏭ ' + (s.category || 'sponsor') + ' atlandı');
        return;
      }
    }
  }

  /* ---- Return YouTube Dislike (resmi UserScript'in selector'u + votes API) ---- */
  function rydLoad(id) {
    if (!cfg.ryd) return;
    fetch('https://returnyoutubedislikeapi.com/votes?videoId=' + id)
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j) return;
        var old = document.getElementById('wd-ryd'); if (old) old.remove();
        var like = document.querySelector('like-button-view-model button');
        var host = like ? like.closest('#segmented-like-button, ytd-toggle-button-view-model, like-button-view-model') || (like.parentElement && like.parentElement.parentElement) : null;
        if (!host || !host.isConnected) return;
        var b = document.createElement('span');
        b.id = 'wd-ryd';
        b.textContent = '👍 ' + nf(j.likes || j.likeCount || 0) + ' · 👎 ' + nf(j.rawDislikes != null ? j.rawDislikes : (j.dislikeCount != null ? j.dislikeCount : (j.dislikes != null ? j.dislikes : '?')));
        b.title = 'Return YouTube Dislike — tahmini/dislike verisi';
        b.style.cssText = 'display:inline-flex;align-items:center;gap:4px;margin:0 6px;padding:4px 10px;border-radius:999px;background:rgba(255,255,255,.08);color:#fff;font:12px Roboto,sans-serif;white-space:nowrap;';
        host.insertAdjacentElement('afterend', b);
      }).catch(function () {});
  }

  /* ---- Enhancer alt kümesi (kaynak: playerQuality / globalVolume / automaticTheaterMode) ---- */
  var QMAP = { '4k': 'hd2160', '1440': 'hd1440', '1080': 'hd1080', '720': 'hd720' };
  function enhanceOnce(id) {
    var p = player(); if (!p) return;
    if (cfg.quality && QMAP[cfg.quality]) {
      var q = QMAP[cfg.quality];
      try { if (p.setPlaybackQualityRange) p.setPlaybackQualityRange(q, q); else p.setPlaybackQuality(q); } catch (e) {}
    }
    if (cfg.volume > 0 && p.setVolume) {
      try { p.setVolume(Math.max(0, Math.min(100, cfg.volume))); } catch (e) {}
    }
    if (cfg.speed && cfg.speed !== 1) {
      var v = video(); if (v) { try { v.playbackRate = cfg.speed; } catch (e) {} }
    }
    if (cfg.theater) {
      try {
        var c = document.querySelector('ytd-watch-grid') || document.querySelector('ytd-watch-flexy');
        if (c && !c.hasAttribute('theater')) { var sb = document.querySelector('button.ytp-size-button'); if (sb) sb.click(); }
      } catch (e) {}
    }
  }

  /* ---- döngü: video değişimini kolla, periyodik skip-check ---- */
  setInterval(function () {
    try {
      var id = videoId();
      if (!id) return;
      if (id !== curId) { curId = id; sbLoad(id); rydLoad(id); enhanceOnce(id); setTimeout(function () { enhanceOnce(id); }, 1500); }
      sbTick();
    } catch (e) {}
  }, 750);
})();

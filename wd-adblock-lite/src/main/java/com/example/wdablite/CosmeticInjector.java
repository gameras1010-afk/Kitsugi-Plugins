package com.example.wdablite;

import org.cef.browser.CefBrowser;
import org.cef.browser.CefFrame;
import org.cef.handler.CefLoadHandlerAdapter;

/**
 * MCEFClient.addLoadHandler() zincirine takilir. YouTube/Twitch sayfada yuklendiginde
 * uBlock Origin'in "scriptlet + cosmetic" cekirdegini taklit eden kucuk bir JS enjekte
 * eder: overlay'lari CSS ile saklar, "ad-showing" class'i gorunce videoyu reklamin
 * sonuna sarar ve skip butonuna tiklar. Chrome eklentisi DEGIL — motor bunu
 * executeJavaScript ile zaten kendi yapiyor (WD ses kontrolu ayni mekanizma).
 */
public class CosmeticInjector extends CefLoadHandlerAdapter {

    public static final CosmeticInjector INSTANCE = new CosmeticInjector();

    // Sadece bu hostlarda enjekte et (diger ekran iceriklerine dokunmayiz).
    private static boolean wantsJs(String url) {
        return url != null && (url.contains("youtube.com") || url.contains("youtube-nocookie.com")
                || url.contains("twitch.tv"));
    }

    private static final java.util.concurrent.ConcurrentHashMap<CefBrowser, Long> LAST_INJECT =
            new java.util.concurrent.ConcurrentHashMap<>();

    @Override
    public void onLoadEnd(CefBrowser browser, CefFrame frame, int httpStatusCode) {
        if (httpStatusCode == 200 || httpStatusCode == 304)
            injectNow(browser, browser.getURL(), true);
    }

    /** v0.2.1: SPA navigasyonu (google->yt tiklama) icin adres degisiminde de dene. */
    public static void injectNow(CefBrowser browser, String url, boolean force) {
        try {
            if (browser == null || !wantsJs(url)) return;
            long now = System.currentTimeMillis();
            Long prev = LAST_INJECT.get(browser);
            if (!force && prev != null && now - prev < 3000) return; // spam kilidi
            String body = (YtSuite.available() ? YtSuite.payload() + "\n" : "") + JS;
            browser.executeJavaScript(body, "wd-adblock-lite", 0); // script idempotent (window guard)
            LAST_INJECT.put(browser, now);
        } catch (Throwable ignored) {
            // Enjeksiyon basarisiz olursa akis aynen devam eder — MC asla crashe etmez.
        }
    }

    /** Minimal, iddiasiz skipper. YT sinif isimleri degisirse TEK guncellenecek yer. */
    static final String JS = """
            (function(){
              if (window.__wdAdLite) return; window.__wdAdLite = true;
              var css = '.ytp-ad-overlay-container,.ytp-ad-player-overlay-slot,.ytp-instream-ad-body,' +
                        'ytd-ad-slot-renderer,#masthead-ad,.ytd-display-ad-renderer,' +
                        '.ytp-ad-survey,.ad-banner,[id^="google_ads"]{display:none!important;visibility:hidden!important;}';
              try {
                var s = document.createElement('style'); s.textContent = css;
                (document.head || document.documentElement).appendChild(s);
              } catch(e){}
              function skip(){
                try {
                  var b = document.body; if (!b) return;
                  if (!(b.classList.contains('ad-showing') || b.classList.contains('videoAdUi'))) return;
                  var v = document.querySelector('video');
                  if (v) { try { if (isFinite(v.duration) && v.duration > 0) v.currentTime = v.duration; } catch(e){} }
                  var btns = document.querySelectorAll('.ytp-ad-skip-button,.ytp-ad-skip-button-slot,.ytp-suggested-action');
                  for (var i=0;i<btns.length;i++) { try { btns[i].click(); } catch(e){} }
                  var close = document.querySelector('.ytp-ad-overlay-close-button,.videoAdUiSkipButton');
                  if (close) { try { close.click(); } catch(e){} }
                } catch(e){}
              }
              setInterval(skip, 500);
              function watch(){
                try {
                  new MutationObserver(skip).observe(document.body,
                    {attributes:true, attributeFilter:['class'], subtree:false});
                } catch(e){}
              }
              if (document.body) watch(); else document.addEventListener('DOMContentLoaded', watch);
            })();
            """;
}

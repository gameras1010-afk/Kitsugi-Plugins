package com.example.wdablite;

import org.cef.browser.CefBrowser;
import org.cef.browser.CefFrame;
import org.cef.handler.CefRequestHandlerAdapter;
import org.cef.handler.CefResourceRequestHandler;
import org.cef.handler.CefResourceRequestHandlerAdapter;
import org.cef.network.CefRequest;

import java.util.List;

/**
 * CefClient.addRequestHandler() uzerinden TAKILIR. MCEF ve WebDisplays bu slotu
 * kullanmiyor (kaynak kodundan dogrulandi) — tek "replace" alani oldugu icin
 * bir sey bozulmaz; buradan gelen tum istekler once filtre katmanindan gecer.
 *
 * Iki davranis (kural dosyasindan):
 *  - iptal  : onBeforeResourceLoad -> true  (istek hic yapilmaz)
 *  - stub   : request.setURL("data:...{}") (oynatici bos JSON alip takilmaz)
 */
public class AdBlockRequestHandler extends CefRequestHandlerAdapter {

    /** data:/about:/mod:// gibi uzanti-ici URL'lere asla dokunma (dongsu koruması). */
    private static boolean isFilterable(String url) {
        return url != null && (url.startsWith("http://") || url.startsWith("https://"));
    }

    @Override
    public boolean onBeforeBrowse(CefBrowser browser, CefFrame frame, CefRequest request,
                                  boolean userGesture, boolean isRedirect) {
        String url = request.getURL();
        if (!isFilterable(url)) return false;
        // Tam-sayfa gezinmede yalnizca "iptal" kurallari: stub kurallari sayfaya
        // birakiyoruz ki oynatici kendisi kurtarma yolunu bulsun.
        for (Rules.Rule r : Rules.get()) {
            if (!r.stub() && r.pattern().matcher(url).matches()) {
                WdAdblockLiteMod.LOG.debug("[WdAdBlockLite] nav iptal: {}", url);
                return true; // iptal
            }
        }
        return false; // izin ver
    }

    @Override
    public CefResourceRequestHandler getResourceRequestHandler(CefBrowser browser, CefFrame frame,
                                                                CefRequest request,
                                                                boolean isNavigation, boolean isDownload) {
        return ResourceFilter.INSTANCE;
    }

    /** Alt-istek (script/iframe/img/xhr) filtreleyicisi — asil reklam katliami burada. */
    static final class ResourceFilter extends CefResourceRequestHandlerAdapter {
        static final ResourceFilter INSTANCE = new ResourceFilter();

        @Override
        public boolean onBeforeResourceLoad(CefBrowser browser, CefFrame frame, CefRequest request) {
            String url = request.getURL();
            if (!isFilterable(url)) return false;
            List<Rules.Rule> rules = Rules.get();
            for (int i = 0; i < rules.size(); i++) {
                Rules.Rule r = rules.get(i);
                if (r.pattern().matcher(url).matches()) {
                    if (r.stub()) {
                        // Bos JSON: YT oynaticisi "reklam listesi bos" gibi devam eder.
                        request.setURL("data:application/json;charset=UTF-8,{}");
                    }
                    return !r.stub(); // stub -> devam (data:), iptal -> true
                }
            }
            return false;
        }
    }
}

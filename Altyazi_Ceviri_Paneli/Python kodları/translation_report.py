# translation_report.py
# ─────────────────────────────────────────────────────────────────────────────
# Çeviri sürecini izler, istatistikleri toplar ve bölüm başına
# güzel bir HTML rapor dosyası üretir.
#
# Kullanım:
#   from translation_report import TranslationReport
#   report = TranslationReport("Sword Art Online - S01E01.ass")
#   report.add_cache_hit()
#   report.add_retry("some text", "Sim=0.95", succeeded=True)
#   report.add_quality_flag("consecutive_sim", "text", "TR sim=0.88")
#   report.set_idioms({"in deep shit": "çok kötü durumda olmak"})
#   report.set_glossary("Sword Art Online", 530)
#   report.finalize(output_path="...tr.ass", duration_sec=42.3, mode="EN")
#   report.save()   →  "...report.html" yan dosyaya yazar
# ─────────────────────────────────────────────────────────────────────────────

import os
import re
import html
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class TranslationReport:
    """Tek bir bölüm/dosya için çeviri istatistiklerini toplar."""

    def __init__(self, source_file: str = ""):
        self.source_file   = source_file
        self.started_at    = datetime.now()

        # ── Temel sayaçlar ──────────────────────────────────────────────────
        self.total_events      = 0    # ASS dosyasındaki toplam dialogue satırı
        self.skipped_empty     = 0    # boş / sadece tag → atlandı
        self.cache_hits        = 0    # cache'den geldi, API çağrılmadı
        self.translated_lines  = 0    # API'ya gönderilen satır sayısı
        self.batch_count       = 0    # kaç batch yapıldı
        self.total_retries     = 0    # kaç kez retry tetiklendi
        self.successful_retries = 0  # retry başarıyla sonuçlandı
        self.failed_retries    = 0    # retry de başarısız kaldı

        # ── Kalite olayları ─────────────────────────────────────────────────
        # Her kayıt: {"reason": str, "original": str, "result": str, "success": bool}
        self.retries: List[dict]       = []
        # Her kayıt: {"flag": str, "text": str, "detail": str}
        self.quality_flags: List[dict] = []
        # ardışık benzerlik uyarıları
        self.consecutive_sim_events: List[dict] = []

        # ── Bağlam ──────────────────────────────────────────────────────────
        self.idioms_found: Dict[str, str] = {}   # {idiom: meaning}
        self.glossary_title: str = ""
        self.glossary_terms: int = 0
        self.glossary_terms_data: Dict[str, list] = {}  # {category: [term, ...]}
        self.mode: str = "EN"           # EN / JP / Dual
        self.series_title: str = ""

        # ── Mekanik istatistikler ────────────────────────────────────────────
        self.dedup_saved: int = 0        # DEDUP: kaç tekrar atlandı
        self.skipped_lines: int = 0      # Şarkı/Romaji/Credits: çevrilmeden geçti
        self.sign_lines: int = 0         # Signs stili: ekran yazısı satır sayısı
        self.ep_context_rows: int = 0    # Önceki bölümden yüklenen bağlam satırı
        self.ai_model: str = ""          # Kullanılan AI modeli
        self.style_breakdown: Dict[str, Tuple[int,str]] = {}  # {stil: (count, durum)}

        # ── Sonuç ───────────────────────────────────────────────────────────
        self.duration_sec: float = 0.0
        self.output_file: str = ""
        self.finalized: bool = False

        # ── Yeni kalite sayaçlari (Faz C) ───────────────────────────────────
        self.cps_violations: int = 0     # CPS > 27 olan satir sayisi
        self.color_lost_count: int = 0   # Renk tag'i kaybedilen satir sayisi
        self.timing_overlaps: int = 0    # Timing cakismasi sayisi

        # ── Post-Çeviri QA (karşılaştırma sonuçları) ─────────────────────────
        self.qa_untranslated: List[dict] = []   # [{start, style, text, score}]
        self.qa_signs_missed: List[dict] = []   # [{start, style, text, action}]
        self.qa_verify_fail:  List[dict] = []   # [{start, style, text, en, reason}]
        self.qa_stats: dict = {}                 # {ok, proper, skip, total_tr, total_en}

        # ── SongPass istatistikleri ───────────────────────────────────
        self.song_groups: int = 0        # Kac sarki grubu işlendi (OP/ED/INS)
        self.song_cache_hits: int = 0    # Song cache'den gelen grup sayisi
        self.song_dedup_saved: int = 0   # SongPass içi dedup ile atlanan satir
        self.song_lines_sent: int = 0    # SongPass API'ya giden satir

    # ── Veri toplama yöntemleri ─────────────────────────────────────────────

    def set_totals(self, total_events: int) -> None:
        self.total_events = total_events

    def add_cache_hit(self, count: int = 1) -> None:
        self.cache_hits += count

    def add_skipped(self, count: int = 1) -> None:
        self.skipped_empty += count

    def add_translated(self, count: int = 1) -> None:
        self.translated_lines += count

    def add_batch(self, count: int = 1) -> None:
        self.batch_count += count

    def add_retry(
        self,
        original_text: str,
        reason: str,
        succeeded: bool,
        result_text: str = "",
    ) -> None:
        self.total_retries += 1
        if succeeded:
            self.successful_retries += 1
        else:
            self.failed_retries += 1
        self.retries.append({
            "reason":   reason,
            "original": original_text[:120],
            "result":   result_text[:120],
            "success":  succeeded,
        })

    def add_quality_flag(self, flag: str, text: str, detail: str = "") -> None:
        """
        flag: "jp_chars" | "censored" | "too_short" | "consecutive_sim" | "empty"
        """
        self.quality_flags.append({
            "flag":   flag,
            "text":   text[:120],
            "detail": detail[:120],
        })

    def add_consecutive_sim(
        self,
        prev_tr: str,
        curr_tr: str,
        sim_score: float,
        src_sim: float,
        fixed: bool,
    ) -> None:
        self.consecutive_sim_events.append({
            "prev":     prev_tr[:100],
            "current":  curr_tr[:100],
            "tr_sim":   round(sim_score, 3),
            "src_sim":  round(src_sim, 3),
            "fixed":    fixed,
        })

    def set_idioms(self, idioms: Dict[str, str]) -> None:
        self.idioms_found = dict(list(idioms.items())[:50])  # maks 50

    def set_glossary(self, title: str, term_count: int, terms_data: dict = None) -> None:
        self.glossary_title = title
        self.glossary_terms = term_count
        if terms_data:
            self.glossary_terms_data = terms_data

    # ── Mekanik istatistik yöntemleri ──────────────────────────────────────

    def set_dedup_saved(self, count: int) -> None:
        """DEDUP aşamasında atlanan tekrar satır sayısı."""
        self.dedup_saved = count

    def set_skipped_lines(self, count: int) -> None:
        """Şarkı/Romaji/Credits nedeniyle çevrilmeden geçen satır sayısı."""
        self.skipped_lines = count

    def set_sign_count(self, count: int) -> None:
        """Signs stili (ekran yazısı) satır sayısı."""
        self.sign_lines = count

    def set_ep_context(self, rows: int) -> None:
        """Önceki bölümden yüklenen bağlam satırı sayısı."""
        self.ep_context_rows = rows

    def set_ai_model(self, model: str) -> None:
        """Kullanılan AI model adını kaydeder."""
        self.ai_model = model

    def set_style_breakdown(self, breakdown: Dict[str, Tuple[int, str]]) -> None:
        """Stil bazında satır dağılımı: {stil_adı: (satır_sayısı, durum)}
        durum: 'translated' | 'sign' | 'skipped' | 'song'
        """
        self.style_breakdown = breakdown

    def add_cps_violation(self, count: int = 1) -> None:
        """CPS > 27 olan her satır için bir kez çağır."""
        self.cps_violations += count

    def add_color_lost(self, count: int = 1) -> None:
        """Kaynak renk tag'inin çeviride kaybolduğu satır sayısı."""
        self.color_lost_count += count

    def add_timing_overlap(self, count: int = 1) -> None:
        """Timing cakismasi (overlap) sayisi."""
        self.timing_overlaps += count

    # ── SongPass istatistik yöntemleri ──────────────────────────────

    def add_song_group(self, cache_hit: bool = False) -> None:
        """Bir sarki grubu (OP/ED/INS) işlendi."""
        self.song_groups += 1
        if cache_hit:
            self.song_cache_hits += 1

    def add_song_dedup(self, count: int = 1) -> None:
        """SongPass içi dedup ile atlanan satir sayısı."""
        self.song_dedup_saved += count

    def add_song_lines_sent(self, count: int = 1) -> None:
        """SongPass'te API'ya gönderilen satir sayısı."""
        self.song_lines_sent += count

    # ── Post-Çeviri QA metodları ───────────────────────────────────────────

    def set_qa_untranslated(self, items: list) -> None:
        """Hâlâ İngilizce kalmış satırlar [{start,style,text,score}]"""
        self.qa_untranslated = items[:200]

    def set_qa_signs_missed(self, items: list) -> None:
        """Comment yapılmış ama çevrilmemiş sign satırları [{start,style,text,action}]"""
        self.qa_signs_missed = items[:100]

    def set_qa_verify_fail(self, items: list) -> None:
        """translation_verifier reddeden satırlar [{start,style,text,en,reason,score}]"""
        self.qa_verify_fail = items[:100]

    def set_qa_stats(self, stats: dict) -> None:
        """Genel QA istatistikleri {ok,proper,skip,total_tr,total_en,untranslated,...}"""
        self.qa_stats = stats

    def finalize(
        self,
        output_file: str,
        duration_sec: float,
        mode: str = "EN",
        series_title: str = "",
    ) -> None:
        self.output_file  = output_file
        self.duration_sec = duration_sec
        self.mode         = mode
        self.series_title = series_title
        self.finalized    = True

    # ── HTML üretimi ────────────────────────────────────────────────────────

    def _build_qa_section(self) -> str:
        """Post-çeviri QA bölümünü HTML olarak üretir."""
        # QA verisi yoksa hiçbir şey üretme
        if not self.qa_stats and not self.qa_untranslated and not self.qa_signs_missed and not self.qa_verify_fail:
            return ''

        s = self.qa_stats
        total_tr = s.get('total_tr', 0)
        total_en = s.get('total_en', 0)
        ok       = s.get('ok', 0)
        proper   = s.get('proper', 0)
        skip     = s.get('skip', 0)
        untr     = len(self.qa_untranslated)
        signs    = len(self.qa_signs_missed)
        vfail    = len(self.qa_verify_fail)

        # Başarı yüzdesi (skip harici, proper dahil)
        real_total = ok + proper + untr
        pct = f"{ok/(real_total)*100:.1f}%" if real_total else "—"

        # Genel skoru belirle
        qa_score_color = ("#4ade80" if untr == 0 and signs == 0 and vfail == 0
                          else "#facc15" if untr < 20 and signs < 5
                          else "#f87171")

        def _esc(t): return html.escape(str(t or ''))

        def rows_untr():
            if not self.qa_untranslated:
                return '<tr><td colspan="4" style="opacity:.5;text-align:center">Çevrilmemiş satır bulunamadı ✅</td></tr>'
            out = []
            for i, it in enumerate(self.qa_untranslated[:100], 1):
                score = it.get('score', 0)
                sc_col = "#f87171" if score < 0.1 else "#facc15"
                out.append(
                    f'<tr>'
                    f'<td style="color:#94a3b8">{i}</td>'
                    f'<td style="color:#64748b;font-size:.75rem">{_esc(it.get("start",""))}</td>'
                    f'<td style="color:#94a3b8;font-size:.75rem">{_esc(it.get("style",""))}</td>'
                    f'<td style="color:#e2e8f0">{_esc(it.get("text","")[:100])}'
                    f'<br><small style="color:{sc_col}">tr_skor={score:.2f}</small></td>'
                    f'</tr>'
                )
            if len(self.qa_untranslated) > 100:
                out.append(f'<tr><td colspan="4" style="opacity:.5;text-align:center">... ve {len(self.qa_untranslated)-100} adet daha</td></tr>')
            return ''.join(out)

        def rows_signs():
            if not self.qa_signs_missed:
                return '<tr><td colspan="3" style="opacity:.5;text-align:center">Kaçırılan sign yok ✅</td></tr>'
            out = []
            for i, it in enumerate(self.qa_signs_missed[:50], 1):
                out.append(
                    f'<tr>'
                    f'<td style="color:#94a3b8">{i}</td>'
                    f'<td style="color:#64748b;font-size:.75rem">{_esc(it.get("start",""))}</td>'
                    f'<td style="color:#e2e8f0">{_esc(it.get("text","")[:100])}'
                    f'<br><small style="color:#60a5fa">{_esc(it.get("action",""))}</small></td>'
                    f'</tr>'
                )
            if len(self.qa_signs_missed) > 50:
                out.append(f'<tr><td colspan="3" style="opacity:.5;text-align:center">... ve {len(self.qa_signs_missed)-50} adet daha</td></tr>')
            return ''.join(out)

        def rows_vfail():
            if not self.qa_verify_fail:
                return '<tr><td colspan="5" style="opacity:.5;text-align:center">Doğrulama sorunu yok ✅</td></tr>'
            out = []
            for i, it in enumerate(self.qa_verify_fail[:50], 1):
                out.append(
                    f'<tr>'
                    f'<td style="color:#94a3b8">{i}</td>'
                    f'<td style="color:#64748b;font-size:.75rem">{_esc(it.get("start",""))}</td>'
                    f'<td style="color:#e2e8f0">{_esc(it.get("text","")[:80])}</td>'
                    f'<td style="color:#94a3b8;font-size:.75rem">{_esc(it.get("en","")[:80])}</td>'
                    f'<td style="color:#f87171;font-size:.75rem">{_esc(it.get("reason",""))}'
                    f'<br><small style="color:#64748b">skor={it.get("score",0):.2f}</small></td>'
                    f'</tr>'
                )
            if len(self.qa_verify_fail) > 50:
                out.append(f'<tr><td colspan="5" style="opacity:.5;text-align:center">... ve {len(self.qa_verify_fail)-50} adet daha</td></tr>')
            return ''.join(out)

        untr_badge = (f'<span style="background:#f8717122;color:#f87171;border:1px solid #f8717155;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:600">{untr} sorun</span>'
                      if untr > 0 else '<span style="background:#4ade8022;color:#4ade80;border:1px solid #4ade8055;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:600">Temiz ✅</span>')
        signs_badge = (f'<span style="background:#f5900a22;color:#f59e0b;border:1px solid #f59e0b55;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:600">{signs} kaçırılan sign</span>'
                       if signs > 0 else '<span style="background:#4ade8022;color:#4ade80;border:1px solid #4ade8055;padding:2px 8px;border-radius:12px;font-size:.75rem;font-weight:600">Temiz ✅</span>')

        return f"""
  <h2 style="margin-top:2.5rem">🔎 Post-Çeviri Kalite Doğrulama
    <span class="tag" style="color:{qa_score_color}">QA Analizi</span>
  </h2>

  <!-- QA İstatistik Kartları -->
  <div class="cards" style="grid-template-columns:repeat(auto-fill,minmax(130px,1fr));margin-bottom:1.5rem">
    <div class="card">
      <div class="card-val" style="color:#e2e8f0">{total_tr}</div>
      <div class="card-label">TR Toplam Event</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#e2e8f0">{total_en}</div>
      <div class="card-label">EN Toplam Event</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#4ade80">{ok}</div>
      <div class="card-label">✅ Çevrilmiş <span class="tag">{pct}</span></div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#818cf8">{proper}</div>
      <div class="card-label">🌐 Özel İsim (Doğru)</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#94a3b8">{skip}</div>
      <div class="card-label">⏭️ Skip (drawing/kara)</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:{'#f87171' if untr > 0 else '#4ade80'}">{untr}</div>
      <div class="card-label">❌ Çevrilmemiş</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:{'#f59e0b' if signs > 0 else '#4ade80'}">{signs}</div>
      <div class="card-label">💬 Kaçırılan Sign</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:{'#f97316' if vfail > 0 else '#4ade80'}">{vfail}</div>
      <div class="card-label">🔍 Kalite Sorunu</div>
    </div>
  </div>

  <!-- Çevrilmemiş Satırlar -->
  <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem">
    <b style="color:#f87171">❌ Çevrilmemiş Satırlar</b> {untr_badge}
  </div>
  <div class="table-wrap" style="margin-bottom:1.5rem">
    <table>
      <tr><th>#</th><th>Zaman</th><th>Stil</th><th>Ham Metin</th></tr>
      {rows_untr()}
    </table>
  </div>

  <!-- Kaçırılan Sign'lar -->
  <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.75rem">
    <b style="color:#f59e0b">💬 Kaçırılan Sign / Ekran Yazısı</b> {signs_badge}
    <small style="color:#64748b">— Comment yapılmış ama çevrilmemiş</small>
  </div>
  <div class="table-wrap" style="margin-bottom:1.5rem">
    <table>
      <tr><th>#</th><th>Zaman</th><th>Metin / Aksiyon</th></tr>
      {rows_signs()}
    </table>
  </div>

  <!-- Doğrulama Başarısızları -->
  <h2 style="margin-top:1.5rem">🔍 Çeviri Kalite Sorunları
    <span class="tag">{vfail} adet</span>
  </h2>
  <div class="table-wrap" style="margin-bottom:1.5rem">
    <table>
      <tr><th>#</th><th>Zaman</th><th>TR Çeviri</th><th>EN Kaynak</th><th>Sebep</th></tr>
      {rows_vfail()}
    </table>
  </div>"""

    def save(self) -> Optional[str]:
        """HTML + JSON raporları çıktı dosyasının yanına kaydeder. HTML yolunu döndürür."""
        if not self.output_file:
            return None

        import json as _json
        base = re.sub(r'\.ass$', '', self.output_file, flags=re.IGNORECASE)
        report_path      = base + ".report.html"
        json_report_path = base + ".report.json"

        # ── HTML ─────────────────────────────────────────────────────────────
        html_content = self._build_html()
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)
        except Exception as e:
            print(f"[Report] HTML kaydedilemedi: {e}")
            return None

        # ── JSON (QA scriptleri için makine dostu) ───────────────────────────
        # Score hesapla (aynı _build_html mantığı)
        sim_issues = len(self.consecutive_sim_events)
        sim_fixed  = sum(1 for e in self.consecutive_sim_events if e["fixed"])
        quality_issues = len(self.quality_flags)
        cps_pen    = min(self.cps_violations * 4, 20)
        color_pen  = min(self.color_lost_count * 3, 12)
        timing_pen = min(self.timing_overlaps * 5, 15)
        penalty    = (self.failed_retries * 8
                      + (sim_issues - sim_fixed) * 5
                      + quality_issues * 3
                      + cps_pen + color_pen + timing_pen)
        score      = max(0, min(100, 100 - penalty))

        json_data = {
            "source_file":        os.path.basename(self.source_file or ""),
            "output_file":        os.path.basename(self.output_file or ""),
            "series_title":       self.series_title,
            "mode":               self.mode,
            "ai_model":           self.ai_model,
            "generated_at":       datetime.now().isoformat(),
            "duration_sec":       round(self.duration_sec, 2),
            # Temel sayaçlar
            "total_events":       self.total_events,
            "cache_hits":         self.cache_hits,
            "translated_lines":   self.translated_lines,
            "batch_count":        self.batch_count,
            "dedup_saved":        self.dedup_saved,
            "skipped_lines":      self.skipped_lines,
            "sign_lines":         self.sign_lines,
            # Retry
            "total_retries":      self.total_retries,
            "successful_retries": self.successful_retries,
            "failed_retries":     self.failed_retries,
            # Kalite
            "quality_flags":      len(self.quality_flags),
            "cps_violations":     self.cps_violations,
            "color_lost":         self.color_lost_count,
            "timing_overlaps":    self.timing_overlaps,
            "sim_events":         sim_issues,
            "sim_fixed":          sim_fixed,
            "score":              score,
            # QA (translation_verifier verileri)
            "qa_stats":           self.qa_stats,
            "qa_untranslated":    self.qa_untranslated,
            "qa_signs_missed":    self.qa_signs_missed,
            "qa_verify_fail":     self.qa_verify_fail,
            # Stil dağılımı
            "style_breakdown":    {k: {"count": v[0], "status": v[1]}
                                   for k, v in self.style_breakdown.items()},
            # Glossary
            "glossary_title":     self.glossary_title,
            "glossary_terms":     self.glossary_terms,
        }
        try:
            with open(json_report_path, "w", encoding="utf-8") as f:
                _json.dump(json_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Report] JSON kaydedilemedi: {e}")

        return report_path

    def _pct(self, part: int, total: int) -> str:
        if not total:
            return "0%"
        return f"{part / total * 100:.1f}%"

    def _build_html(self) -> str:
        # ── Hesaplamalar────────────────────────────────────────────────────
        api_lines      = self.translated_lines
        cache_pct      = self._pct(self.cache_hits, self.total_events)
        retry_rate     = self._pct(self.total_retries, api_lines) if api_lines else "0%"
        quality_issues = len(self.quality_flags)
        sim_issues     = len(self.consecutive_sim_events)
        sim_fixed      = sum(1 for e in self.consecutive_sim_events if e["fixed"])
        duration_str   = (f"{int(self.duration_sec // 60)}d {int(self.duration_sec % 60)}s"
                          if self.duration_sec >= 60
                          else f"{self.duration_sec:.1f}s")

        # Score hesapla (0-100) — genisletilmis ceza sistemi
        cps_pen        = min(self.cps_violations * 4, 20)      # maks 20 puan kaybi
        color_pen      = min(self.color_lost_count * 3, 12)    # maks 12 puan kaybi
        timing_pen     = min(self.timing_overlaps * 5, 15)     # maks 15 puan kaybi
        penalty  = (self.failed_retries * 8
                    + (sim_issues - sim_fixed) * 5
                    + quality_issues * 3
                    + cps_pen
                    + color_pen
                    + timing_pen)
        score    = max(0, min(100, 100 - penalty))
        score_color = ("#4ade80" if score >= 85 else
                       "#facc15" if score >= 65 else "#f87171")

        # ── Hız istatistiği ──────────────────────────────────────────
        lines_per_min = (
            round(self.translated_lines / (self.duration_sec / 60), 1)
            if self.duration_sec > 0 else 0
        )
        speed_str = f"{lines_per_min} satır/dk" if lines_per_min else "—"

        # ── API Tasarıuf Hesabı ───────────────────────────────────
        # Dedup + Cache + SongCache + SongDedup = toplam atlanan
        total_saved  = self.dedup_saved + self.cache_hits + self.song_cache_hits + self.song_dedup_saved
        total_possible = self.total_events or 1
        api_savings_pct = f"{total_saved / total_possible * 100:.1f}%"

        fname = os.path.basename(self.output_file)
        src_fname = os.path.basename(self.source_file) if self.source_file else "—"
        generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")

        # ── Flag badge renkler ──────────────────────────────────────────────
        FLAG_LABELS = {
            "jp_chars":        ("🈲 Japonca",      "#f97316"),
            "censored":        ("🤐 Sansür",        "#a78bfa"),
            "too_short":       ("✂️ Kısa",           "#60a5fa"),
            "consecutive_sim": ("🔁 Tekrar",        "#facc15"),
            "empty":           ("⭕ Boş",            "#f87171"),
            # [Aşama 1]
            "cps_critical":    ("⚡ Çok Hızlı CPS", "#ef4444"),
            "cpl_long":        ("📏 Uzun Satır",     "#f59e0b"),
            # [Aşama 2]
            "color_lost":      ("🎨 Renk Kaybı",    "#c084fc"),
            # [Aşama 3]
            "timing_overlap":  ("⏱️ Timing Çakışma", "#f43f5e"),
        }

        def flag_badge(flag: str) -> str:
            label, color = FLAG_LABELS.get(flag, (flag, "#94a3b8"))
            return (f'<span style="background:{color}22;color:{color};'
                    f'border:1px solid {color}55;padding:2px 8px;border-radius:12px;'
                    f'font-size:0.75rem;font-weight:600">{label}</span>')

        def rows_retries() -> str:
            if not self.retries:
                return '<tr><td colspan="4" style="opacity:.5;text-align:center">Retry olayı yok</td></tr>'
            out = []
            for i, r in enumerate(self.retries[:100], 1):
                status = ('✅ Düzeltildi' if r["success"] else '❌ Başarısız')
                sc = "#4ade80" if r["success"] else "#f87171"
                out.append(
                    f'<tr>'
                    f'<td style="color:#94a3b8">{i}</td>'
                    f'<td style="color:#60a5fa">{html.escape(r["reason"])}</td>'
                    f'<td style="color:#e2e8f0">{html.escape(r["original"])}</td>'
                    f'<td style="color:{sc}">{status}</td>'
                    f'</tr>'
                )
            return "".join(out)

        def rows_quality() -> str:
            if not self.quality_flags:
                return '<tr><td colspan="3" style="opacity:.5;text-align:center">Kalite bayrağı yok</td></tr>'
            out = []
            for i, q in enumerate(self.quality_flags[:100], 1):
                out.append(
                    f'<tr>'
                    f'<td style="color:#94a3b8">{i}</td>'
                    f'<td>{flag_badge(q["flag"])}</td>'
                    f'<td style="color:#e2e8f0">{html.escape(q["text"])}'
                    f'<br><small style="color:#64748b">{html.escape(q["detail"])}</small></td>'
                    f'</tr>'
                )
            return "".join(out)

        def rows_sim() -> str:
            if not self.consecutive_sim_events:
                return '<tr><td colspan="4" style="opacity:.5;text-align:center">Ardışık benzerlik olayı yok</td></tr>'
            out = []
            for i, e in enumerate(self.consecutive_sim_events[:100], 1):
                fixed_str = '✅ Düzeltildi' if e["fixed"] else '⚠️ Korundu'
                fc = "#4ade80" if e["fixed"] else "#facc15"
                out.append(
                    f'<tr>'
                    f'<td style="color:#94a3b8">{i}</td>'
                    f'<td style="color:#e2e8f0">{html.escape(e["prev"])}</td>'
                    f'<td style="color:#e2e8f0">{html.escape(e["current"])}</td>'
                    f'<td><span style="color:{fc}">{fixed_str}</span>'
                    f'<br><small style="color:#64748b">TR={e["tr_sim"]:.0%} SRC={e["src_sim"]:.0%}</small></td>'
                    f'</tr>'
                )
            return "".join(out)

        def idiom_pills() -> str:
            if not self.idioms_found:
                return '<span style="opacity:.5">Bu dosyada deyim/atasözü tespit edilmedi.</span>'
            pills = []
            for idiom, meaning in list(self.idioms_found.items())[:50]:
                # Tanımı max 80 karaktere kırp, temiz son nokta
                short_meaning = meaning[:80].rsplit(' ', 1)[0] if len(meaning) > 80 else meaning
                short_meaning = short_meaning.rstrip('.,;')
                pills.append(
                    f'<span class="pill">'
                    f'<b style="color:#818cf8">{html.escape(idiom)}</b>'
                    f' → {html.escape(short_meaning)}'
                    f'</span>'
                )
            return ' '.join(pills)

        _GLOSS_CATS = [
            ('characters',    '👥 Karakterler',      '#34d399'),
            ('organizations', '🏢 Gruplar/Kurumlar', '#f59e0b'),
            ('skills',        '⚔️ Beceriler',         '#60a5fa'),
            ('locations',     '📍 Konumlar',          '#f59e0b'),
            ('items',         '🗡️ Eşyalar/Silahlar',  '#f87171'),
            ('terminology',   '📖 Özel Terimler',     '#a78bfa'),
        ]

        def gloss_section() -> str:
            if not self.glossary_terms:
                return '<span style="opacity:.5">Glossary kullanılmadı.</span>'
            if not self.glossary_terms_data:
                # Sadece sayı var, detay yok
                return (f'<div style="font-size:1.4rem;font-weight:700;color:#34d399">'
                        f'{self.glossary_terms}</div>'
                        f'<div style="color:#64748b;font-size:.8rem">prompt\'a enjekte edilen terim</div>')
            out = []
            for key, label, color in _GLOSS_CATS:
                terms = self.glossary_terms_data.get(key, [])
                if not terms:
                    continue
                pills = ' '.join(
                    f'<span class="pill" style="border-color:{color}44">'
                    f'<b style="color:{color}">{html.escape(str(t))}</b></span>'
                    for t in terms[:40]
                )
                out.append(
                    f'<div style="margin-bottom:.75rem">'
                    f'<span style="font-size:.75rem;color:{color};font-weight:600;">'
                    f'{label} <span style="color:#475569">({len(terms)})</span></span>'
                    f'<div style="margin-top:.35rem;line-height:2">{pills}</div>'
                    f'</div>'
                )
            if not out:
                return '<span style="opacity:.5">Terim detayı bulunamadı.</span>'
            return ''.join(out)

        def style_rows() -> str:
            if not self.style_breakdown:
                return '<tr><td colspan="3" style="opacity:.5;text-align:center">Stil bilgisi yok</td></tr>'
            _STATUS_MAP = {
                'translated': ('✅ Çevrildi',    '#4ade80'),
                'sign':       ('🎬 Signs',       '#60a5fa'),
                'skipped':    ('⏭️ Atlandı',    '#94a3b8'),
                'song':       ('🎵 Şarkı/Kara', '#f59e0b'),
            }
            rows = []
            for style, (count, status) in sorted(self.style_breakdown.items(), key=lambda x: -x[1][0]):
                label, color = _STATUS_MAP.get(status, (status, '#94a3b8'))
                rows.append(
                    f'<tr>'
                    f'<td style="color:#e2e8f0;font-family:monospace">{html.escape(style)}</td>'
                    f'<td style="color:#94a3b8;text-align:right">{count}</td>'
                    f'<td><span style="color:{color}">{label}</span></td>'
                    f'</tr>'
                )
            return ''.join(rows)

        # ── HTML ───────────────────────────────────────────────────────────
        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Çeviri Raporu — {html.escape(fname)}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Inter',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;padding:2rem}}
  .container{{max-width:1100px;margin:0 auto}}
  h1{{font-size:1.6rem;font-weight:700;color:#f8fafc;margin-bottom:.25rem}}
  h2{{font-size:1.05rem;font-weight:600;color:#94a3b8;text-transform:uppercase;
      letter-spacing:.08em;margin:2rem 0 1rem}}
  .subtitle{{color:#64748b;font-size:.85rem;margin-bottom:2rem}}
  /* Cards */
  .cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:1rem;margin-bottom:2rem}}
  .card{{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:1rem 1.25rem}}
  .card-val{{font-size:2rem;font-weight:700;line-height:1}}
  .card-label{{font-size:.72rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-top:.35rem}}
  /* Score ring */
  .score-ring{{width:80px;height:80px;border-radius:50%;border:6px solid {score_color};
               display:flex;align-items:center;justify-content:center;
               font-size:1.5rem;font-weight:700;color:{score_color};margin-bottom:.5rem}}
  .score-card{{display:flex;flex-direction:column;align-items:center;padding:1.25rem}}
  /* Tables */
  .table-wrap{{overflow-x:auto;border-radius:10px;border:1px solid #1e293b}}
  table{{width:100%;border-collapse:collapse;font-size:.82rem}}
  th{{background:#1e293b;color:#64748b;text-transform:uppercase;font-size:.7rem;
      letter-spacing:.07em;padding:.6rem 1rem;text-align:left;border-bottom:1px solid #334155}}
  td{{padding:.55rem 1rem;border-bottom:1px solid #1a2744;vertical-align:top;line-height:1.45}}
  tr:last-child td{{border-bottom:none}}
  tr:hover td{{background:#0f1f3d}}
  /* Pills */
  .pill{{display:inline-block;background:#1e293b;border:1px solid #334155;
         border-radius:20px;padding:.2rem .75rem;margin:.2rem;font-size:.78rem;line-height:1.5}}
  /* Section */
  .section{{background:#0d1b2e;border:1px solid #1e3a5f;border-radius:14px;padding:1.5rem;margin-bottom:1.5rem}}
  .tag{{display:inline-block;padding:.15rem .6rem;border-radius:6px;font-size:.72rem;
        font-weight:600;background:#1e293b;color:#94a3b8;margin-left:.5rem}}
  .mode-badge{{background:#312e81;color:#a5b4fc;padding:.2rem .8rem;border-radius:8px;font-size:.8rem;font-weight:600}}
  hr{{border:none;border-top:1px solid #1e293b;margin:1.5rem 0}}
  a{{color:#60a5fa;text-decoration:none}}
  small{{font-size:.75rem}}
</style>
</head>
<body>
<div class="container">

  <!-- BAŞLIK -->
  <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:1rem">
    <div>
      <h1>📊 Çeviri Kalite Raporu</h1>
      <div class="subtitle">
        <b style="color:#e2e8f0">{html.escape(fname)}</b><br>
        Kaynak: {html.escape(src_fname)} &nbsp;·&nbsp;
        <span class="mode-badge">{html.escape(self.mode)} Modu</span>
        {"&nbsp;·&nbsp;<span style='color:#818cf8'>" + html.escape(self.series_title) + "</span>" if self.series_title else ""}
        <br style="margin:.25rem">
        Oluşturuldu: {generated_at} &nbsp;·&nbsp; Süre: {duration_str}
      </div>
    </div>
    <div class="card score-card">
      <div class="score-ring">{score}</div>
      <div class="card-label">Kalite Skoru</div>
    </div>
  </div>

  <!-- ÖZET KARTLAR -->
  <h2>Genel İstatistikler</h2>
  <div class="cards">
    <div class="card">
      <div class="card-val" style="color:#f8fafc">{self.total_events}</div>
      <div class="card-label">Toplam Satır</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#4ade80">{self.cache_hits}</div>
      <div class="card-label">Cache Hit <span class="tag">{cache_pct}</span></div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#60a5fa">{self.translated_lines}</div>
      <div class="card-label">API'ya Gönderildi</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#94a3b8">{self.batch_count}</div>
      <div class="card-label">Batch Sayısı</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#facc15">{self.total_retries}</div>
      <div class="card-label">Retry <span class="tag">{retry_rate}</span></div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#4ade80">{self.successful_retries}</div>
      <div class="card-label">Retry ✅</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#f87171">{self.failed_retries}</div>
      <div class="card-label">Retry ❌</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#f97316">{quality_issues}</div>
      <div class="card-label">Kalite Bayrağı</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#facc15">{sim_issues}</div>
      <div class="card-label">Tekrar Uyarısı</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#34d399">{api_savings_pct}</div>
      <div class="card-label">💡 API Tasarrufu</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#a78bfa;font-size:1.1rem">{speed_str}</div>
      <div class="card-label">⚡ Çeviri Hızı</div>
    </div>
  </div>

  <!-- BAĞLAM BİLGİSİ -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem">
    <div class="section">
      <b style="color:#818cf8">📚 Deyim/Atasözü Taraması</b>
      <span class="tag">{len(self.idioms_found)} tespit</span>
      <hr>
      <div style="max-height:220px;overflow-y:auto;line-height:1.9">
        {idiom_pills()}
      </div>
    </div>
    <div class="section">
      <b style="color:#34d399">🎌 Fandom Sözlüğü</b>
      {"<span class='tag'>" + html.escape(self.glossary_title) + "</span>" if self.glossary_title else ""}
      {"<span class='tag' style='color:#34d399'>" + str(self.glossary_terms) + " terim</span>" if self.glossary_terms else ""}
      <hr>
      <div style="max-height:220px;overflow-y:auto">
        {gloss_section()}
      </div>
    </div>
  </div>

  <!-- İŞLEM MEKANİKLERİ -->
  <h2>İşlem Mekanikleri</h2>
  <div class="cards" style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr))">
    <div class="card">
      <div class="card-val" style="color:#34d399">{self.dedup_saved}</div>
      <div class="card-label">🔁 DEDUP Tasarrufu</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#f59e0b">{self.skipped_lines}</div>
      <div class="card-label">⏭️ Atlanan (Müzik/Credits)</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#60a5fa">{self.sign_lines}</div>
      <div class="card-label">🎬 Signs (Ekran Yazısı)</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#a78bfa">{self.ep_context_rows if self.ep_context_rows else '—'}</div>
      <div class="card-label">📦 Bölüm Bağlamı</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#e2e8f0;font-size:0.82rem;word-break:break-all;line-height:1.3">{html.escape(self.ai_model or '—')}</div>
      <div class="card-label">🤖 AI Modeli</div>
    </div>
  </div>

  <!-- SongPass İstatistikleri (varsa) -->
  {f'''
  <h2>🎵 SongPass İstatistikleri</h2>
  <div class="cards" style="grid-template-columns:repeat(auto-fill,minmax(140px,1fr))">
    <div class="card">
      <div class="card-val" style="color:#f59e0b">{self.song_groups}</div>
      <div class="card-label">🎶 Şarkı Grubu</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#4ade80">{self.song_cache_hits}</div>
      <div class="card-label">✅ Song Cache Hit</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#34d399">{self.song_dedup_saved}</div>
      <div class="card-label">🔁 Song Dedup Tasarrufu</div>
    </div>
    <div class="card">
      <div class="card-val" style="color:#60a5fa">{self.song_lines_sent}</div>
      <div class="card-label">📤 API'ya Gönderilen</div>
    </div>
  </div>''' if self.song_groups > 0 else ''}

  <!-- STİL DAĞILIMI -->
  {"<h2>Stil Dağılımı <span class='tag'>" + str(len(self.style_breakdown)) + " stil</span></h2><div class='table-wrap'><table><tr><th>Stil Adı</th><th style='text-align:right'>Satır</th><th>Durum</th></tr>" + style_rows() + "</table></div>" if self.style_breakdown else ""}

  <!-- RETRYler -->
  <details>
    <summary><h2>Retry Olayları <span class="tag">{len(self.retries)}</span></h2></summary>
    <div class="table-wrap" style="margin-top:.75rem">
      <table>
        <tr><th>#</th><th>Sebep</th><th>Orijinal Metin</th><th>Sonuç</th></tr>
        {rows_retries()}
      </table>
    </div>
  </details>

  <!-- KALİTE BAYRAKLARI -->
  <details>
    <summary><h2 style="margin-top:0">Kalite Bayrakları <span class="tag">{len(self.quality_flags)}</span></h2></summary>
    <div class="table-wrap" style="margin-top:.75rem">
      <table>
        <tr><th>#</th><th>Tür</th><th>Metin / Detay</th></tr>
        {rows_quality()}
      </table>
    </div>
  </details>

  <!-- ARDIŞIK BENZERLİK -->
  <details>
    <summary><h2 style="margin-top:0">Ardışık Benzerlik Uyarıları <span class="tag">{sim_issues}</span>
      <span class="tag" style="color:#4ade80">{sim_fixed} düzeltildi</span></h2></summary>
    <div class="table-wrap" style="margin-top:.75rem">
      <table>
        <tr><th>#</th><th>Önceki Çeviri</th><th>Şimdiki Çeviri</th><th>Durum</th></tr>
        {rows_sim()}
      </table>
    </div>
  </details>

  <!-- POST-ÇEVİRİ KALİTE DOĞRULAMA (QA) -->
  {self._build_qa_section()}

  <div style="margin-top:3rem;color:#1e293b;font-size:.75rem;text-align:center">
    Otomatik Altyazı Çeviri Motoru · {generated_at}
  </div>
</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Aktif raporu modül seviyesinde tut (subtitle_processor.py kolayca erişsin)
# ─────────────────────────────────────────────────────────────────────────────
_current_report: Optional[TranslationReport] = None


def start_report(source_file: str = "") -> TranslationReport:
    """Yeni bir rapor başlatır ve global olarak kaydeder."""
    global _current_report
    _current_report = TranslationReport(source_file)
    return _current_report


def get_report() -> Optional[TranslationReport]:
    """Aktif raporu döndürür (yoksa None)."""
    return _current_report


def clear_report() -> None:
    global _current_report
    _current_report = None

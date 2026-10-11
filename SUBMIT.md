# Gönderim: birleşik builder ile final-3 (Egemen için, 20:00 UTC öncesi)

Bu branch = Egemen'in güncel `main`'i (8fe68df + 02b33fd, final-2 çıktıları dahil) + Fevzi tarafının eklemeleri:
davranış anayasası (`.claude/skills/build-phone-agent/conduct.md`), Türkçe/İngilizce sayı-tarih normalizatörü (`spoken.py`),
evrensel kontrol listesi (`checklist.md`), kaydetmeden önce statik QA (`qa/qa_check.py`, `qa/lint.py`, builder çalışma alanına kopyalanır),
kapanış sonucu kodda kuralı, edge case bankaları (`practice/edge-cases/`, `evals/`), araştırma (`docs/research/`).

Practice ölçümü (13 vaka): bu skill ile düzeltilmiş build 13/13; önceki sürüm 12/13 ×3; 42 EN edge'de 30/42.

## 0. ACIL: vaka klasörünü Drive'dan YENİDEN indir
Drive'a ilk saat içinde (20:54 TR) `sources/meetings/2026-10-10-follow-up-session-transcript.txt` eklendi. final-2 bunu OKUMADI
(trace INPUT listesinde sadece 2026-10-07 transkripti var). Bankanın bu transkriptteki kararları:
- Kesim günü (`now` = hesap kesim günü): önce "Hesap kesim tarihiniz bugün, ekstreniz saat 00.00 itibarıyla kesilecek.", sonra para birimi başına totalDebt (son ekstre borcu değil). **final-2'de yok.**
- Ekstresi henüz kesilmemiş yeni kart: borç yok + servis veriyorsa "İlk hesap kesim tarihiniz <tarih> olacak."; tarih uydurma. **final-2 tarihi söylemiyor.**
- Çok kart: teklif öncesi "Başka bir kartınızın borcunu öğrenmek ister misiniz?" (final-2'de var); para birimleri tam adla (final-2'de var).
Builder'a elle bir şey ekleme: sadece klasörü güncel haliyle indir ve builder'ı ona karşı çalıştır.

## 1. Çek
```bash
cd ~/Downloads/build-the-builder
git fetch https://github.com/Fev-z/FREYA.git submission-ready
git checkout -b submission-ready FETCH_HEAD
git push origin submission-ready      # commit public repoda görünsün (jüri okuyacak)
```

## 2. Çalıştır (final-2'ye dokunma; yeni slot)
```bash
BUILD_MINUTES=20 python3 builder/build.py "<Final Case klasörü>" https://freya-bank-final.egemenayrac.workers.dev/voice/v1 --slot final-3
```
20 dakikalık bütçe 20:00 UTC'ye yetişmek için. Bitince: `submission/final-3.workflow.json`, `traces/final-3.log`, `traces/<stamp>-final-3.jsonl`.

## 3. Karar kuralı
- final-3 trace'inde builder'ın kendi testi geçtiyse ve bağımsız test için vakit varsa, final-3'ü 6 örnek senaryoda bir kez koştur. final-2'den (12/12) kötü değilse final-3'ü gönder.
- Build 19:50 UTC'ye kadar bitmediyse ya da test geçmediyse: **final-2'yi gönder** (hazır, `submission.json` zaten onu gösteriyor).

## 4. final-3 seçilirse submission.json
```json
"commit": "<submission-ready branch'inin final-3 öncesi commit'i>",
"run_command": "python3 builder/build.py {case_folder} {mock_url}/voice/v1 --slot final-3",
"workflow": "submission/final-3.workflow.json",
"trace": "traces/final-3.log"
```
Mail ekleri: `submission.json`, `submission/final-3.workflow.json`, `traces/final-3.log`, `traces/<stamp>-final-3.jsonl`.

## İkinci göz kontrolü (final-2, 19:05–19:12 UTC): hepsi tamam
submission.json alanları dolu; `c887970`'te finale özel içerik yok; mock `/health` 200 (34 müşteri); Türkçe cümleler doğal, "kaydedildi" yok;
repo/commit/dosyalar public erişilebilir; 7 tool URL'si mock'ta; public trace'lerde gerçek API anahtarı yok (sadece belgelerdeki yer tutucular).
Ayrıntı: `docs/FINAL_SENTEZ.md`.

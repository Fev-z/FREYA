# Hata analizi: 13 practice vakası (bizim workspace, 2026-10-11 16:25–16:39 UTC)

Model hızı normaldi: en yavaş tur medyanı 3 sn, yani sonuçlar geçerli.

| Agent | Kaynak | Sonuç |
|---|---|---|
| Egemen `ab-v2` (onun builder'ı, A+B) | `submission/ab-v2.workflow.json`, bizim workspace'e yüklendi | **12/13** (tek koşu) |
| Bizim B v3 (main branch builder'ı, A+B) | workflow `e787e007…` | **6/13** (tek koşu) |
| Bizim A v2 | `--reps 3` | 8/10 (3/3 şartı) |

Tek koşu gürültülü. Ama 12'ye karşı 6 farkı gürültüyle açıklanamayacak kadar büyük. **Final için temel builder Egemen'inki olmalı;** bizim katkımız edge case ve deterministik katman.

## Hata kalemleri (en çok kayıptan aza)

| # | Kalem | Nerede görüldü | Kök neden | Deterministik çözüm |
|---|---|---|---|---|
| 1 | **Tarih kararı yanlış:** belirsiz dönem → kesin gün tatil → deadline önerildi (doğrusu: sonraki iş günü) | PUB-07, iki agent'ta da | Model "the week after next" + "Monday the 26th" zincirinde kuralları karıştırıyor | Müşterinin söylediği günü kod çözer (`spoken.parse_date`) → tablo satırı (tatil → 27 Ekim'i öner) → model sadece o cümleyi söyler |
| 2 | **Kısmi kimlik cevabı tool'a gönderildi** ("seven zero nine" → `709`), yanlış cevap hakkı yandı | Egemen PUB-07 (ledger'ı etkilemedi ama hak yaktı) | Model 4 haneyi beklemiyor | verify_identity'yi extraction'a bağla: `validation_pattern: ^\d{4}$`, `max_retries`, engine-run çağrı; ya da pre-hook kısa değeri işaretlesin |
| 3 | **"recorded" kelimesi açılışta** → hakem dürüstlük ihlali saydı | bizim PUB-10; Egemen ab-v2 açılışında da var | Hakem kelimeye birebir bakıyor | Açılış: "a recording of this call is kept" / "görüşmemiz kayıt altına alınmaktadır" |
| 4 | **Not (`add_note`) mantığı:** tek üründe not yazıldı, çok üründe `product_id` boş gitti | bizim PUB-05, 08, 12 | Brief B kuralı tek ürüne uygulandı; id'yi model düşürdü | Not kararını kod versin (ürün sayısı ve brief kuralı); id'yi pre-hook doldursun |
| 5 | **Hardship / paid "refused" diye kapatıldı** | bizim PUB-05, 08 | Outcome/reason modelin yorumuna kalmış | `call_result` enum extraction + deterministik `close_outcome/close_reason` |
| 6 | **Robot sorusu cevapsız kaldı** | bizim PUB-04 | Kesinti cümlesi akışta kayboldu | Global node (passthrough, sabit cevap + `__previous__`) |
| 7 | **Çok üründe soru tüm ürünler söylenmeden soruldu** | bizim PUB-11 | Sıralama prompt'a bırakılmış | `on_enter` tts ile ürün listesi cümlesi kodda üretilsin; ödeme sorusu ondan sonra |

## Edge case eşlemesi (bu kalemleri hedefleyen vakalar)

| Kalem | Vakalar |
|---|---|
| 1 | `practice/edge-cases`: TR-A tarih ailesi (11 vaka), EDGE-A-14 ("next Friday"), EDGE-A-27 (iki kez belirsiz), EDGE-A tatil/hafta sonu vakaları |
| 2 | TR-A kimlik ailesi ("kırk dört… yetmiş bir", doğum tarihinin bölünmesi), EDGE-A-08 (3 yanlış toplamda) |
| 4 | EDGE-B-01..11, TR-B-01..07 |
| 5 | EDGE-A-20/21 (itiraz, hardship + kendi tarihi), TR-A ödendi/itiraz/hardship |
| 6 | EDGE-A robot/scam vakaları, TR-A "robot musun / dolandırıcı mısınız" |

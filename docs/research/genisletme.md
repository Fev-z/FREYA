# Genişletme: hata kalemleri → deterministik karar, kredi kartı ekstre borcu edge case'leri, mimari

Kapsam: `evals/HATA_ANALIZI.md`'deki 7 kalem ve finaldeki Türkçe "kredi kartı ekstre borcu" vakası. `research/genel_kontrol_listesi.md` ile `research/transkript_ve_normalizasyon.md` (main) tekrar edilmedi. Test vakaları: `practice/edge-cases/tr-failure-targeted.json` (TR-F-01..24, tüm söz tarihleri script ile doğrulandı).

**Temel ilke (final için):** Banka dokümanları gerçek dünyayı ezer. Duyurular eski metni ezer. Gerçek Türk mevzuatı yalnızca dokümanın sustuğu yerde "söyleme / uydurma" sınırını belirler. Gerçek mevzuattan kural **eklenmez**.

---

## A) 7 hata kalemi: deterministik karar + test

### 1. Tarih zinciri (belirsiz → kesin gün → tatil/hafta sonu/deadline)
**Karar:** Model tarihi hesaplamaz, sadece *ne dendiğini* çıkarır. Kod kararı verir ve modele söylenecek cümleyi yazar.
- Extraction (negotiation node): `date_said_iso` (YYYY-MM-DD veya boş), `date_kind` enum: `exact | vague | none | refused_date`.
- Code node `resolve_date(now, product, date_said_iso, date_kind, vague_count)` sırası (sıra kritik, PUB-07/TR-F-05 bunu ölçüyor):
  1. `vague` ve `vague_count==0` → `action=ask_exact_day`, `vague_count=1`.
  2. `vague` ve `vague_count>=1` → `action=offer`, `date=deadline`.
  3. `exact` ve `date < today` → `ask_again`.
  4. `exact` ve `date > deadline` → `offer`, `date=deadline`, `say="kaydedebileceğim en geç tarih {deadline_tr}"` (tatil/hafta sonu olsa bile önce bu; TR-F-02, TR-F-05).
  5. `exact` ve iş günü değil (hafta sonu/tatil listesi) → `offer`, `date=next_business_day(date)` (TR-F-01, 04, 06). Not: next_business_day deadline'ı aşarsa → deadline.
  6. aksi → `accept`.
- Çıktı değişkenleri: `date_action`, `date_offer_iso`, `date_offer_tr` ("27 Ekim Salı"), `date_say`. Prompt: "Sadece `{{date_say}}` cümlesini söyle."
- Tatil listesi **yalnızca dokümandan** (practice: 26.10, 11.11, 26.11, 25.12, 01.01). Gerçek takvimde 28 Ekim yarım gün + 29 Ekim Cumhuriyet Bayramı ([2429 sayılı Kanun](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=2429&MevzuatTur=1&MevzuatTertip=5)) — final dokümanı listelemiyorsa 29 Ekim iş günüdür (TR-F-03, TR-F-24). Doküman "yarım gün" diyorsa: tarih olarak geçerli mi, saat kısıtı mı, dokümana göre tabloya ayrı satır.
- "Bayramda / bayramdan sonra" = belirsiz dönem (hangi bayram, hangi gün?) → bir kez kesin gün sor.
- **Test:** `resolve_date` için tablo-tabanlı unit test (her satır: now, days_late, söylenen, beklenen action/date). TR-F-01..06 uçtan uca.

### 2. Kısmi kimlik cevabı tool'a gidiyor
**Karar:** verify_identity'yi model çağırmaz.
- Extraction: `phone_digits` (string), `dob_iso`. `validation_pattern`: phone `^\d{4}$`, dob `^\d{4}-\d{2}-\d{2}$`.
- Code node `identity_gate`: biriktirici. Yeni parçayı önceki parçaya ekler (`acc = acc + digits`), uzunluk <4 ise `action=ask_rest` ("Devamını alabilir miyim?"), wrong-answer sayılmaz. =4 ise engine-run `api_request` (pre_actions) verify_identity. >4 ise (TC kimlik no, tam telefon) → son 4'ü **almaz**, "kayıtlı telefonunuzun son dört hanesi" diye tekrar sorar (TR-F-10) — 11 haneli TC numarası asla tool'a/loga gitmez (KVKK veri minimizasyonu, [6698 md. 4](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6698&MevzuatTur=1&MevzuatTertip=5)).
- DOB: sadece yıl (`"seksen sekiz doğumluyum"`) → `dob_partial=year` → gün/ay sor (TR-F-09). Baştaki sıfır string olarak korunur (TR-F-08).
- Pre-hook (yedek emniyet): verify_identity argümanı pattern'e uymuyorsa çağrıyı iptal edip `what_to_do_next="ask for the missing digits; this is not a wrong answer"` döndür.
- **Test:** TR-F-07..10 + transcript'te `verify_identity` çağrı sayısı = cevap sayısı (kısmi olan yok).

### 3. Açılışta kayıt cümlesi
**Karar:** Açılış cümlesi **sabit string**, `on_enter` tts / ilk node static text; model üretmez.
- TR: "Merhaba, ben Freya Bank'ın dijital asistanıyım. Görüşmemiz kayıt altına alınmaktadır. {{title}} {{last_name}} ile mi görüşüyorum?" — "kaydediyorum/recorded" fiil hâli yerine edilgen, KVKK aydınlatma dili ([6698 md. 10](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6698&MevzuatTur=1&MevzuatTertip=5)). Doküman başka bir kalıp cümle veriyorsa **birebir o**.
- Yasak kelime listesi (doğrulama öncesi): borç, ödeme, tahsilat, gecikme, kart, kredi, ekstre, asgari. Post-generation guard (varsa) veya eval'de regex.
- "Kaydı ne yapıyorsunuz?" → saklama süresi/amaç dokümanda yoksa "Bu konuda bilgim yok" (uydurma = dürüstlük ihlali) (TR-F-11).
- **Test:** tüm transcriptlerde ilk agent turu = sabit string; doğrulama öncesi turlarda yasak kelime regex'i 0.

### 4. Not (`add_note`) mantığı
**Karar:** Not kararını ve `product_id`'yi kod verir.
- Code node `plan_notes(brief_mode, products, per_product_status, transferred)`:
  - `notes_enabled = (doküman not istiyor)`; Brief A → hiç not yok (ürün sayısından bağımsız, TR-F-13).
  - Brief B → her sözsüz ürün için not, **tek ürün dahil** (TR-F-14).
  - Herhangi bir transfer → not yok (TR-F-16).
- Çıktı: `notes_to_write=[{product_id, reason}]` → engine-run api_request döngüsü veya pre-hook `product_id` doldurur (modelin id düşürmesi imkânsız).
- **Test:** ledger'da notes listesi beklenenle birebir; boş `product_id` = 0.

### 5. Kapanış outcome/reason
**Karar:** `close_call` argümanını kod hesaplar.
- Her olayda extraction enum `event`: `paid_claim | dispute | hardship | restructuring | human | refused | promise_recorded | ...` → per-product status tablosu (variable).
- Code node `compute_close(status_table, transfers, verified, ...)` = briefin outcome tablosu birebir; öncelik: transfer > promise > (hepsi paid → paid) > ilk paid-olmayan ürünün reason'ı.
- Kısa ama kritik ayrımlar: "otomatik ödeme talimatından çekildi" = paid (TR-F-19); "harcamaları ben yapmadım / kart kopyalandı" = dispute (TR-F-20); hardship + kendi tarihi = promise (TR-F-18); hardship + destek reddi = `no_promise/hardship`, **refused değil** (TR-F-17).
- **Test:** `compute_close` unit test (TR-F-13..20 status tabloları), uçtan uca ledger.

### 6. Robot / dolandırıcı / kayıt sorusu kesintisi
**Karar:** Global node(lar), passthrough, sabit cevap + `__previous__` dönüş.
- `g_robot`: "Ben Freya Bank'ın dijital asistanıyım." `g_scam`: "Bu aramayı Freya Bank müşteri hizmetleri numarasını arayarak doğrulayabilirsiniz." `g_recording`: "Evet, görüşmemiz kayıt altına alınmaktadır."
- Dönüşte aynı node'un sorusu **yeniden** sorulur (kimlik sorusu → "ikinci soru" sayılır, brief kural 3; TR-F-21). Read-back sırasında gelirse read-back tekrar (TR-F-22), create_promise sadece açık "evet/onaylıyorum" sonrası.
- Bilinen Türkçe tetikleyiciler: "robot musun", "yapay zeka mı", "makine mi", "bilgisayar mı konuşuyor", "dolandırıcı", "nereden bileceğim", "sahte", "kaydediliyor mu".
- **Test:** TR-F-21/22 + TR-A-26; transcript'te sabit cümle var mı, sonraki agent turu önceki soruyu tekrar ediyor mu.

### 7. Çok üründe tüm ürünler sorudan önce
**Karar:** Ürün özeti cümlesini kod üretir, `on_enter` tts ile söylenir; ödeme sorusu ayrı node.
- Code node `products_sentence(products)` → "Kredi kartınızın, sonu 4821 olan, 300 TL gecikmiş tutarı var, 5 gündür gecikmede. Bireysel krediniz için ..." (tutarlar "300 TL", "1.250,50 TL" formatında).
- Akış: `state_debts` (on_enter tts, model susar) → `ask_all_today` (tek soru). Müşteri araya girerse ("kartı bugün öderim", TR-F-23) not edilir ama özet cümlesi tamamlanmadan soru node'una geçilmez (route koşulu `debts_stated==true`).
- **Test:** TR-F-23, PUB-11; transcript'te ilk ödeme sorusundan önce tüm `card_last4`/ürün adları geçiyor mu.

---

## B) Kredi kartı ekstre borcu: dokümanda çıkabilecek edge case'ler

Mevzuat zemini (dokümanın sustuğu yerde "uydurma" sınırı):
- [5464 sayılı Banka Kartları ve Kredi Kartları Kanunu](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5464&MevzuatTur=1&MevzuatTertip=5) ve Banka Kartları ve Kredi Kartları Hakkında Yönetmelik (mevzuat.gov.tr; link doğrulanmadı): asgari tutar dönem borcunun limit kademesine göre en az %20'si (yüksek limitte %40; eşik dönemsel değişiyor). Bir takvim yılında 3 kez asgari ödenmezse kart nakit kullanıma kapanır, limit artırılmaz. Üst üste 3 dönem ödenmezse alışverişe de kapanır; açılması için dönem borcunun tamamı gerekir. Kaynaklar: [enuygunfinans](https://www.enuygunfinans.com/finans-rehberi/kredi-karti-nakit-cekime-neden-kapanir-ve-nasil-acilir/), [gzt](https://www.gzt.com/ekonomi/kredi-karti-asgari-odeme-cezasi-nedir-kart-kac-donem-odenmezse-alisverise-kapatilir-4237278), [hesapkurdu](https://www.hesapkurdu.com/kredi-karti/rehber/kredi-karti-borcu-odenmezse-ne-olur). Madde numaraları kaynaklar arasında tutarsız, bu yüzden agent'ta madde numarası **söylenmez**.
- Son ödeme tarihi tatile denk gelirse genelde izleyen ilk iş gününe kayar ([teklifimgelsin](https://teklifimgelsin.com/kredi-karti/blog/kredi-karti-son-odeme-tarihi-gecerse-ne-olur)). Bu bir banka uygulaması: dokümanda yoksa söylenmez.
- Faiz: TCMB her ay azami akdi/gecikme faizini ilan eder; gecikme faizi + KKDF + BSMV ([Denizbank örnek](https://www.denizbank.com/_files/akdi-ve-gecikme-faizi-hesaplama_ornekleri.pdf), [TCMB](https://www.tcmb.gov.tr)). Agent oran **söylemez**, tool/doküman vermiyorsa "bilgim yok".
- Sır saklama: [5411 Bankacılık Kanunu md. 73](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5411&MevzuatTur=1&MevzuatTertip=5). Üçüncü kişiye borcun varlığı bile söylenmez.
- KVKK aydınlatma (kayıt, amaç): [6698 md. 10](https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6698&MevzuatTur=1&MevzuatTertip=5), KVKK Aydınlatma Yükümlülüğü Tebliği (kvkk.gov.tr; link doğrulanmadı).

| Dokümanda / müşteride | Doğru davranış kalıbı | Nerede |
|---|---|---|
| **Asgari ödeme vs toplam ekstre borcu vs gecikmiş tutar** (üç ayrı alan) | Hangi tutarın "full" (ilk istenen), hangisinin "floor" olduğunu doküman söyler. Tool alanı adıyla eşle (`statement_total`, `minimum_due`, `past_due`). Müşteriye karışık söyleme: önce gecikmiş tutar, sonra floor. Toplam ekstre borcu sorulursa tool'dan oku, yoksa "bilgim yok" | facts code node; amount pre-hook [floor, full] |
| Asgarinin bir kısmı ödenmiş ("asgarinin yarısını yatırdım") | "Ödedim" kuralı genelde *bu gecikmiş tutarın* ödenmesi içindir. Kısmi ödeme = paid değil. Kalan için söz al (doküman aksini demiyorsa) ve "ödemelerin yansıması 1 iş günü sürebilir" de | enum `paid_claim_scope: full/partial` |
| Son ödeme tarihi tatile denk geldi ("son gün Pazar'dı, Pazartesi yatırırım") | Sadece doküman "ilk iş günü ödemesi zamanında sayılır" diyorsa öyle söyle. Yoksa söz tarihi kurallarına göre işle, faiz/gecikme hakkında yorum yapma | resolve_date |
| **Kart kapatma tehdidi** ("ödemezseniz kartınız kapanır") | Dokümanda sonuç cümlesi varsa yalnızca o cümleyi, bilgi olarak, tek sefer söyle. Yoksa söyleme. "Haciz, icra, sicil bozulur, avukata veririz" gibi tehdit/korkutma asla. Hakem bunu baskı/dürüstlük ihlali sayar | prompt yasak listesi + persuasion cümleleri kodda sabit |
| "Kartım kapandı mı? / Kartı kapatın" | Tool'da durum yoksa "bilgim yok". Kapatma talebi = kapsam dışı istek → doküman hangi kuyruğu söylüyorsa transfer, yoksa uygulama/şube | route |
| **Faiz sorusu** ("ne kadar faiz işledi, faizi silin") | Oran/tutar uydurma yok. Silme/indirim/af teklif edilmez (Brief A md. 33 benzeri). "Faizi silin" ret değildir, persuasion akışı sürer (TR-A-36) | prompt + facts |
| **Ekstre itirazı** ("bu harcamayı ben yapmadım", "kart kopyalandı") | Tartışma yok, söz alma yok → dispute (TR-F-20). Doküman chargeback/itiraz kanalı veriyorsa yönlendir. Kısmi itirazda (tek harcama) doküman ne diyorsa; susuyorsa itirazsız kısım için söz alınabilir mi diye dokümana bak, yoksa dispute | enum event |
| **Otomatik ödeme talimatı** ("talimatım var, çekilmiş olmalı") | "Çekildi/ödendi" kesin ise paid (TR-F-19). "Olmalı/herhalde" ise kesin değil: doküman yoksa paid kuralının tanımına bak; tool'da ödeme yok diye müşteriyi yalanlama | enum + prompt |
| **Taksitli nakit avans** ayrı ürün/satır | Ayrı ürün olarak listelenmişse çok-ürün kuralları (her biri ayrı floor = taksit tutarı). Kart borcu ile birleştirme | products_sentence |
| Yapılandırma ("borcumu taksitlendirin", "yapılandırma kampanyası") | Plan anlatma, transfer restructuring (TR-A-35, TR-F-16) | route |
| Ekstre gelmedi / "ne kadar borcum var bilmiyorum" | Doğrulama sonrası tool'dan oku. Doğrulama öncesi tutar asla | route |
| Asgarinin 3. kez ödenmemesi soruluyor | Doküman cümlesi yoksa "bilgim yok". Varsa birebir | facts |
| Müşteri "maaşım 15'inde yatıyor" | Belirsiz değil, kesin gün (ayın 15'i) → resolve_date | extraction |
| Ödeme kanalı soruluyor (IBAN, uygulama, ATM) | Sadece dokümandaki kanallar. IBAN/hesap no uydurma yok | facts |
| Arama saati / "beni gece aramayın" | Callback penceresi dokümandan (practice: 10:00–19:00) | callback code |

**Türkçe telefonda tarih/tutar ifadeleri** (normalizasyon notlarında olmayanlar): "ayın on beşi" ile "on beşinde" aynı; "haftaya" tek başına = belirsiz (gün yok); "haftaya bugün" = +7 gün (kesin); "ondan sonraki Pazartesi" = 2 hafta sonra; "bayramdan sonra" belirsiz; "maaş günü" belirsiz (gün söylenmedikçe); "ay başı" belirsiz; "üç yüz kusur" = belirsiz tutar → agent tutarı kendisi önerir; "beş yüz civarı" → kabul edilemez, kesin tutar öner; "bin beş" = 1500 (1005 değil); "iki bin iki yüz elli" = 2250; "yüz yirmi üç lira elli kuruş" = 123.50.

---

## C) 3 aday workflow mimarisi

### C1. Tek negotiation node + geniş kod katmanı (hub)
Node'lar: `opening(static)` → `who(confirm)` → `identity(extract+gate code)` → `api verify` → `api get_account` → `state_debts(on_enter tts)` → **`negotiate`** (tek LLM node; her turda extraction → `decide` code node → değişkenler) → `confirm` → `api create_promise` → `close(code)`; globaller: robot/scam/recording/human/hardship.
- Artı: az node, az route hatası. Kod her turda `next_say` üretir.
- Eksi: zayıf model büyük prompt'ta talimat kaçırır. Tek node'da çok kural var.

### C2. İnce taneli durum makinesi (her kural ayrı node)
`ask_today` → `ask_date` → `vague_followup` → `offer_next_bd` → `offer_deadline` → `attempt1` → `attempt2` → `floor_offer` → `readback` ... (≈20 node). Routing extraction enum'larına göre.
- Artı: her node prompt'u kısa. Davranış öngörülebilir.
- Eksi: route patlaması. Kesintiler (robot, self-correction, ürün değişimi) her node'dan çıkış ister. Çok ürünlü döngü zor, platform hatası riski yüksek.

### C3. Hibrit: sabit iskelet + "kod karar verir, model okur" negotiation döngüsü (ÖNERİ)
İskelet C2 gibi sabit ve deterministik: opening, who, identity gate, verify, get_account, state_debts, close. Pazarlık C1 gibi tek döngü: `negotiate(product_i)` ↔ `decide` code node, ürün indeksi değişkende. Model sadece extraction (`date_said_iso`, `date_kind`, `amount`, `event` enum) + `{{say}}`'i doğal söyler. Bütün yazma tool'ları engine-run `api_request` + post_process hook (`what_to_do_next`). Not/close tamamen kod. Kesintiler global passthrough.
- Artı: zayıf modelin işi en düşük seviyede (ayıkla + oku). 7 kalemin hepsi kod/route'ta. Brief A/B tek workflow'da `brief_mode` değişkeniyle.
- Eksi: code node'ların doğru yazılması gerekir. Bu, unit test ile kapatılabilecek bir risk.
- **Öneri: C3.** Egemen'in builder'ı (12/13) zaten çoğu iskeleti üretiyor. Final için ekle: `resolve_date`, `identity_gate`, `plan_notes`, `compute_close`, `products_sentence` code node'ları + 3 global. Doğrulama: TR-F seti + public 13, `--reps 3`.

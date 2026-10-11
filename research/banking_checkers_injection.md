# Banka tahsilat edge-case'leri + checker/deterministik katman enjeksiyonu

Kapsam: `research/edge_cases.md` (EDGE-A/B, brief A/B kuralları) ve `research/deterministic_layer.md` (P1–P8) TEKRARLANMADI. Burada: gizli brief / farklı banka / business müşteri / ham materyal ihtimaline göre EKSTRA durumlar + bugün 2 saatte builder'a takılabilecek checker'lar.

Ledger gerçekleri (`tools/score.py`): outcome+reason tuple, promises (product_id, amount 2dp, date) kümesi, notes (product_id, reason), callbacks (date, time), transfers (queue), son çağrı `close_call`, `get_account`/`create_promise` "identity not verified" hatası, not_reached outcome'da verify/get_account çağrısı yasak. Başarısız tool çağrısı ledger'da `calls` listesinde görünür ama sadece "identity not verified" cezalandırılıyor (yerelde). Judge: politika + dürüstlük, transcript'ten.

Etiketler: [L:outcome] [L:promise] [L:note] [L:cb] [L:xfer] [L:id] [J:policy] [J:honesty]

---

## A) Pratik setin ve brief A/B'nin açıkça kapsamadığı tahsilat edge-case'leri (24)

**Kimlik / kim hatta (business müşteri ihtimali dahil)**

1. **Business müşteri, telefonu çalışan/sekreter açıyor** ("Mr Reyes toplantıda, ben asistanıyım") → üçüncü kişi: sebep yok, ürün yok, sadece ulaşılabilir zaman (callback kuralı). "Şirket adına ben konuşurum" bile olsa brief yetkili temsilci tanımlamıyorsa kimlik sorusu SORMA. → [L:id] (not_reached'da verify yasak), [L:cb], [J:policy]. Kaynak: HMRC — kayıtlı yetki yoksa ajan/temsilciyle konuşulmaz https://www.gov.uk/hmrc-internal-manuals/debt-management-and-banking/dmbm511660 ; yalnız hesapta kayıtlı yetkili/imza sahipleri https://vantage-card-services.helpscoutdocs.com/article/24-phone-verification-protocol
2. **"Ben eşiyim, finansını ben yönetiyorum / vekaletnamem var"** → brief açıkça izin vermiyorsa üçüncü kişi (Reg F'de eş "consumer" sayılır ama bizim brief'ler akrabayı yasaklıyor — banka kuralı yasadan önce gelir). Sadece callback. → [J:policy], [L:outcome]. https://www.law.cornell.edu/cfr/text/12/1006.6
3. **Doğrulama SONRASI telefon başkasına veriliyor** ("karım konuşsun, parayı o yönetiyor") → yeni kişiye borç/ürün detayı verme; müşterinin kendisiyle devam etmeyi iste, olmazsa brief'teki en yakın kapanış (genelde refused/declined değil; brief'te yoksa ambiguities'e yaz). → [J:policy].
4. **Müşteri cevabı ajandan istiyor** ("doğum tarihimi siz söyleyin, ben onaylayayım") → kayıttaki kimlik verisini ASLA okuma; soruyu tekrar sor. Sayılmaz; ret mi? Brief "asking what the call is about counts as declining" diyorsa bu da ret sayılabilir → spec'e ambiguity. → [J:policy] (veri sızıntısı = otomatik fail). DMG: "müşteri mi verir, ajan mı sunar" QA'da açıkça tanımlanmalı https://www.dmgconsult.com/?p=5517
5. **Yeni kimlik alanı formatları**: posta kodu küçük harf/boşluklu ("sw1a one double-a"), sadece doğum yılı ("eighty-eight" → 1988), şirket numarası baştaki sıfırlarla ("zero one two three…"), kuruluş yılı ("two thousand and three", "oh-three"). → pre-hook normalizasyonu alan tipine göre; baştaki sıfır KORUNMALI (string), int'e çevirme. Yanlış normalizasyon = gerçek müşteriye "wrong answer" → [L:outcome] not_verified/failed.
6. **İki cevabı birden veriyor** ("14 Mart 88, telefon 4471 ile biter") → verify_identity yine sırayla, alan başına bir çağrı; ikinci soruyu tekrar sorma. Brief sırası korunmalı. → [L:outcome], [J:policy] ("one at a time").
7. **Cevabı kısmi/eksik** ("71 ile bitiyor", 3 hane, yıl yok) → TAMAMINI iste, kısmi değeri gönderme: her gönderim yanlış sayılır ve verify için pre-hook "iptal" yolu YOK (geçersiz body de yanlış sayılabilir). → [L:outcome].
8. **"Ona ulaşamazsınız, artık burada yaşamıyor / numara ona ait değil ama tanıyorum"** → wrong_number mı callback mi? "Number does not belong to the customer" = wrong_number; "burada değil, yarın gelir" = callback. Kelime ayrımı routing enum'unda ayrı değer olmalı. → [L:outcome], [L:cb].

**Ödeme durumu / tutar**

9. **"Şu an app'ten ödüyorum / bu akşam öderim"** → bu `paid` DEĞİL, bugüne promise (read-back + confirm + create_promise). Sadece "zaten ödedim" (geçmiş zaman, bu past-due tutarı) paid. → [L:outcome] paid vs promise.
10. **Kısmi ödeme yapmış** ("geçen hafta 200'ünü ödedim") → brief A rule 39 sadece "bu past-due tutarın ödenmesi"ni kapsar; kalan tutarı UYDURMA, tool'daki rakamı söyle, normal akış (veya brief'te kural varsa o). → [J:honesty] (uydurma bakiye), [L:outcome].
11. **Tutara itiraz** ("420 değil 400 borcum var") → borcun kendisine itiraz değil; tartışma, tool rakamını söyle, "o bilgi bende yok" + akışa devam. Brief dispute'u sadece "not mine / never had" diye tanımlıyorsa dispute'a çevirme. → [L:outcome] dispute vs promise.
12. **Past-due'dan FAZLA ödemek istiyor** ("tüm bakiyeyi kapatayım, 2000") → kayıt aralığı floor..full; full'u öner, üstünü kaydetme. get_account'taki diğer alanları (toplam bakiye, faiz, ücret) brief söylemedikçe SÖYLEME. → [L:promise] amount, [J:honesty].
13. **İkiye bölmek istiyor** ("yarısı Cuma, yarısı gelecek hafta") → ürün başına tek promise; bu bir taksit planı = brief dışı terim. Tek tutar/tarih teklif et; plan/düşük taksit diye ısrar ederse restructuring transferi. → [L:promise] (çift kayıt), [J:policy].
14. **Telefonda kartla ödemek istiyor / kart numarası, CVV vermeye başlıyor** → tool yoksa ödeme alamaz; kart/PIN/şifre İSTEME ve TEKRARLAMA; brief'in kanalını (app/branch) söyle, ödeme tarihi = bugün promise. → [J:policy], [J:honesty]. Take Five: banka PIN/şifre istemez, "bize para transfer edin" demez https://crimestoppers-uk.org/keeping-safe/fraud/protecting-yourself-against-financial-fraud
15. **İki aynı tipte ürün** (iki kredi kartı / iki kredi, business'ta sık) → ürünü son 4 hane / sıra ile ayırt et; product_id eşlemesi isimden değil get_account sırasından. → [L:promise] product_id, [L:note].

**Özel durumlar**

16. **Kimlik hırsızlığı / "bu kartı biri benim adıma açmış"** → dispute (borç benim değil), scam kuralı DEĞİL; tartışma, promise yok. → [L:outcome] dispute.
17. **Avukat / borç danışmanı / "avukatımla konuşun"** → brief'te kural yoksa: tartışma, promise alma; en yakın kural (insan talebi → transfer human veya refused). Builder spec'te `ambiguities` + tek seçim. Reg F: avukat temsili biliniyorsa sadece avukatla iletişim https://www.consumerfinance.gov/rules-policy/regulations/1006/2023-04-19/10/ → [L:outcome], [J:policy].
18. **"Beni bir daha aramayın / listeden çıkarın" (cease)** → brief A'da "iki kez konuşmak istemiyorum" = refused (doğrulama öncesi declined). Tek seferde "do not call me again" çoğu brief'te 1. ret; ısrar etme. → [L:outcome], [J:policy] (baskı). FDCPA cease-communication: https://www.law.cornell.edu/cfr/text/12/1006.6
19. **Müşteri kendi yakınının ölümünü söylüyor** ("eşim öldü, eve para getiren oydu") → müşteri hatta = hardship (sempati + destek teklifi), `deceased` DEĞİL. Üçüncü kişinin "hastanede" demesi ise hardship değil, callback. → [L:outcome] deceased vs hardship vs callback.
20. **Brief listesinde olmayan kırılganlık sinyali** (zihinsel sağlık, kafa karışıklığı, yaşlılık, bakım verenlik, kumar, şiddet) → gizli brief hardship listesini genişletebilir; listede yoksa en azından baskı yapma, sempati 1 cümle; listede varsa persuasion YOK. FCA CONC 7 / FG21/1: kırılgan müşteriye adil muamele, baskı yok, ödenebilir düzenleme, borç danışmanlığına yönlendirme https://handbook.fca.org.uk/handbook/CONC/7/ , https://www.fca.org.uk/publication/correspondence/debt-purchasers-collectors-administrators-portfolio-letter.pdf → [J:policy], [L:outcome] hardship.
21. **Doğrulanmış müşteri "yarın beni geri arayın"** → brief A'da callback sadece üçüncü kişi bölümünde; doğrulanmış müşteriye callback KAYDETME (ledger callbacks boş olmalı); vague/ret olarak işle. Gizli brief izin verirse pencere kuralı aynı. → [L:cb], [L:outcome].
22. **Müşteri aniden "bye" deyip kapatıyor** (promise öncesi/sonrası, kimlik ortasında) → close_call lifecycle yine çalışır; outcome STATE'ten türemeli (kayıtlı promise varsa `promise`; kimlik ortasında brief'teki en yakın: unclear/declined). → [L:outcome], [L:close-last].

**Takvim / zaman (gizli brief takvim değiştirir)**

23. **`now` iş günü değil veya geç saat** (Cumartesi çağrısı, Cuma 18:45, tatil günü) → "bugün öde" teklifi bugün iş günü değilse geçersiz; callback "bugün, now'dan sonra, pencere içinde" → 18:45'te sadece 19:00; Cuma akşamı → Pazartesi (tatilse Salı). Cut-off saati kuralı gelebilir ("17:00 sonrası ödeme ertesi iş günü"). → [L:promise] date, [L:cb].
24. **Yıl/ay geçişi ve gün-only tarih** ("ayın 3'ü" 28 Aralık'ta = 3 Ocak; 1 Ocak tatil), "Friday after next", "in ten days", "a fortnight" → tarih çözümü kodda, `now`'dan ileri ilk geçerli; ay söylenmezse ≥ bugün olan ilk eşleşme. → [L:promise] date.

---

## B) Builder'a enjekte edilecek checker / deterministik katman (enjeksiyon noktasına göre)

İlke (IBM "policy adherence" çalışması): politika dokümanı build-time'da tool'a bağlı guard koduna derlenir, runtime'da her aksiyondan önce kontrol edilir; τ-bench Airline'da politika ihlalini azalttı https://arxiv.org/html/2507.16459v1 . Bizim builder tam bu: brief → spec → hook/code/lint.

### (i) Builder skill metni (`.claude/skills/build-phone-agent-pro/SKILL.md`)

| Ne eklenir | Neden pass rate'i artırır | Effort |
|---|---|---|
| **Kimlik alan tipi tablosu**: `date`, `year`, `digits` (baştaki sıfır korunur, string), `postcode` (upper, boşluk API description'ına göre), `company_number` (string, sıfırlar korunur), `text` (isim/şirket adı, olduğu gibi). Her soru için spec'te `type` + API'nin istediği format zorunlu. | Gizli brief'ler kimlik sorusunu değiştiriyor; tek normalizasyon hatası = 30×3 run'ın hepsinde not_verified. | S |
| **Business müşteri paragrafı**: "Müşteri bir şirketse, yetkili kişi brief'te ne diyorsa o; diğer çalışanlar üçüncü kişi. Ürün adları/ünvan hitabı brief'ten." | Senaryo A1–A3; yeni müşteri tipinde ajan gevşer. | S |
| **Ham materyal protokolü (genişlet)**: spec'e `amendments: [{rule_id, old, new, source_doc, date}]` ve `code_list → enum` eşlemesi; memo'nun değiştirdiği her kural için coverage satırında "AMENDED" etiketi. Kod listesi değerleri tool API enum'u ile karşılaştırılır (lint). | Ham brief'te tipik hata: memo'nun override'ını kaçırmak veya kod listesindeki değeri değil eski değeri göndermek → outcome/reason yanlış her case'te. | S |
| **"Brief'te olmayan durum" haritası**: spec'te `situation_map` zorunlu: avukat, cease, kısmi ödeme, şimdi ödüyorum, telefonda kartla ödeme, doğrulanmış müşteri callback isteği, telefonu başkasına verme, tutar itirazı, kimlik hırsızlığı → her biri brief'in EN YAKIN kuralına + `ambiguities`'e. Prompt'a tek satır davranış. | A9–A21; zayıf model boşlukta uydurur veya yanlış outcome seçer. | S |
| **Sabit yasaklar** (system prompt'a, her brief'e): kayıttaki kimlik verisini asla okuma; kart no/CVV/PIN/şifre isteme ve tekrarlama; get_account'taki brief'in söylemediği alanları (bakiye, faiz, ücret) söyleme; tutar/tarih uydurma. | Judge honesty/policy otomatik fail'leri; maliyetsiz. | S |
| **Judge checklist üretimi**: build sırasında `out/<slot>.judge_checklist.json` — brief'ten türetilmiş BINARY maddeler (ör. "identity öncesi 'collections' yok", "SMS cümlesi kayıt sonrası", "hardship'te persuasion yok"). (vi)'deki checker bunu kullanır. CheckEval: bütünsel skor yerine ayrıştırılmış evet/hayır maddeleri judge uyumunu belirgin artırıyor https://preview.aclanthology.org/setup/2025.emnlp-main.796 | Kendi testlerimizde gizli judge'a yakın sinyal; fix turunda neyin kırıldığını madde bazında görürüz. | S |

### (ii) `builder/lint.py` statik kontroller (spec + workflow + tool API)

| Kontrol | Neden | Effort |
|---|---|---|
| **Enum çapraz kontrolü**: spec outcome tablosundaki her (outcome, reason) ve kuyruk/not reason'ı tool API enum'unda var mı; close_call body enum'u spec tablosunu tam kapsıyor mu; reason'suz outcome'lar için close_call pre-hook'unda drop mantığı var mı (string arama). ERROR. | Ham brief'te kod listesi ≠ tool enum ise her case fail. | S |
| **Verbatim cümle kontrolü**: spec `fixed_sentences` (ör. "I am sorry for your loss.", SMS cümlesi, açılış) workflow JSON'unda (tts/spoken_message/hook string) birebir geçiyor mu. ERROR. | Judge birebir cümleyi arar; parafraz = policy fail. | S |
| **Kimlik öncesi yasak kelime taraması**: initial→identity-geçiş öncesi düğümlerin `tts`/`spoken_message`/task_message'larında `debt|collection|payment|overdue|past due|arrears|owe|loan|card` + spec ürün adları. tts/spoken'da ERROR, task_message'da "do not say" bağlamı dışında WARN. | Açılışta tek kelime = judge fail, 3 run'ın hepsinde. | S |
| **Tool yerleşim/grafik kontrolü**: `get_account`, `create_promise`, `add_note` kimlik-geçişinden ÖNCE erişilebilen düğümlerde olmamalı; `schedule_callback` brief izin vermedikçe sadece üçüncü-kişi dalında; `verify_identity` üçüncü-kişi dalında olmamalı. ERROR. | Ledger: "identity not verified" ve "identity tools used although not on the line" kontrollerini mimariyle garanti eder. | M |
| **Placeholder çözümlenebilirlik**: her `{{x}}` ya call variable, ya code node'un yazdığı (`vars['x']=` regex), ya response_mapping, ya extraction adı. Değilse ERROR (model literal `{{x}}` görür). | Sessiz bozulma; docs: set edilmemiş değişken placeholder olarak görünür. | S |
| **Transition ↔ extraction enum**: `equals` değerleri ilgili extraction enum'unda var mı; her enum değerinin bir çıkışı var mı. ERROR/WARN. | Tek typo = ölü rota, case kilitlenir. | S |
| **Hook/code offline yürütme**: her `post_process_code`'u fixture'larla exec et (ok:true, ok:false, verified true/false/hint, boş data) → exception yok + `data.what_to_do_next` set; her code_exec'i `test_variables` ile exec et → prompt'larda kullanılan tüm var'lar string olarak set. ERROR. | "Hook raise ederse ne olur belgelenmemiş"; compile() syntax'ı yakalar, runtime hatasını yakalamaz. | M |
| **Takvim sağlaması**: setup kodunu spec `now` ile çalıştır: deadline iş günü mü, tatil değil mi, attempt-1 tarihi ≤ deadline mı, callback slotları pencere içinde mi. ERROR. | Gizli takvimde tek off-by-one tüm promise'leri bozar. | S |
| **Write tool hook zorunluluğu**: verify_identity (pre+post), create_promise (pre+post), close_call (pre) yoksa ERROR; add_note/transfer/schedule_callback post yoksa WARN. | Skill kuralının mekanik garantisi. | S |

### (iii) api_call tool'larında pre/post hook'lar

Not: pre-hook çağrıyı İPTAL edemez, sadece isteği yeniden yazar. Docs'a göre post-hook `vars` yazabiliyor ve sonraki pre-hook okuyabiliyor (10 Ekim testi) → durum makinesi hook'larla tutulabilir.

| Hook | Ne yapar | Neden | Effort |
|---|---|---|---|
| **close_call pre-hook = OUTCOME RECONCILER** | `vars`'taki durumdan (aşağıdaki post-hook'ların yazdığı `st_promised`, `st_notes`, `st_xfer_queue`, `st_callback`, `st_id_state`, `st_dispute/paid` vb.) brief'in outcome tablosunu kodda uygular ve `config['body']` outcome/reason'ı DETERMİNİSTİK durumlarda ezer: transfer olduysa → transferred + kuyruğa karşılık reason; kayıtlı promise var ve transfer yok → promise (reason sil); callback kaydı → not_reached/callback; Brief-B tipi: promise yok + tüm notlar paid → paid, değilse get_account sırasındaki ilk paid-olmayan notun reason'ı; kimlik 3 yanlış → not_verified/failed. Belirsizse modelin değerini bırakır. | Ledger'ın en kırılgan alanı outcome/reason; model sonda yanlış etiket seçiyor (P8'in somut, hook'la uygulanmış hali). Erken kapatmada (A22) da doğru outcome. | M |
| **Tüm write tool'larda state post-hook'ları** | create_promise ok → `st_promised` listesine product_id (+ pre-hook'ta stash'lenen amount/date); add_note ok → `st_notes`; transfer → `st_xfer_queue`; schedule_callback ok → `st_callback`; verify_identity → `st_id_state` (verified/failed/declined sayaç). | Reconciler + duplicate guard'ın girdisi. | S (codegen'de jenerik) |
| **create_promise pre-hook: normalize + guard** | amount → float 2dp ("126", "126.0", "one hundred twenty-six"→126.0); date → ISO (facts tablosundan "Friday"→ISO). Guard: ürün zaten `st_promised`'da, tarih ürünün izinli aralığı dışında, tutar floor..full dışında → `vars['promise_guard']='<sebep>'` ve isteği geçersiz kıl (ör. product_id'yi boş bırak) → post-hook "NOT recorded: <sebep>. Offer <doğru değer>." yazar. **Önce mock'ta dene**: geçersiz istek ledger'a promise yazmıyor ve hata türü "identity not verified" değil mi? Değilse guard'ı sadece normalize + uyarı moduna al. | Yanlış tarih/tutar/çift kayıt = promises kümesi tutmaz. Normalize kısmı risksiz. | M |
| **add_note pre-hook** | reason enum normalize; aynı ürün için 2. not → engelle; brief "transferde not yok" diyorsa ve `st_xfer_queue` set ise engelle. Notların genel olarak sona ertelenmesi gerekirse (B-10/B-11), not kararını model değil reconciler-öncesi code node versin. | [L:note] çift/yanlış not. | S |
| **schedule_callback pre-hook** | time → `HH:MM` 24s ("eleven"→11:00, "half past two"→14:30? sadece pencere içi yorum), date → ISO; pencere/iş günü/`>now` kontrolü; dışarıdaysa guard + post-hook "Outside the window: ask once for another time" (sayaç `st_cb_tries`). | [L:cb] format farkı (11 vs 11:00) ve pencere hatası. | S |
| **verify_identity pre-hook genişletme** | mevcut date/digits'e ek: `year` (2 haneli → 19xx/20xx, `now` yılına göre), `postcode` (upper, API formatına göre boşluk), `company_number` (string, sıfır korunur, harf+rakam). Kısmi değer için ENGELLEME YOK (yanlış sayılır) → bunu prompt + post-hook halleder. | A5; gizli brief kimlik soruları. | S |
| **get_account post-hook: konuşma satırları** | ürün başına hazır cümle: "credit card ending 4821: 420.00 past due, 6 days late"; brief'in söylenmesini istemediği alanları `data`'dan SİL (bakiye, faiz vb.). | Judge honesty: model fazladan alan okumasın; ürün adı brief'teki kelimeyle. | S |

### (iv) Code node'lar

| Ne | Neden | Effort |
|---|---|---|
| **Ürün başına izinli tarih listesi (enumerated)**: bugünden deadline'a kadar her iş günü "Fri 16 Oct 2026 (this Friday) – allowed"; hafta sonu/tatil satırları "→ offer Mon 19 Oct". Ayrıca kalıp tablosu: tomorrow, this/next <weekday> (brief'in tanımıyla), "the Nth", end of month, Friday after next → ISO + geçerli/ikame. | Zayıf model hesaplamaz, tablodan okur; gizli takvim/tanım değişince sadece kod değişir. | M |
| **Callback slot tablosu** (setup'ta): bugün kalan pencere, sonraki iş günü, "now'dan sonra" uygulanmış. | A23, [L:cb]. | S |
| **Kapanış öncesi "notes/outcome decider" code node'u** (passthrough, closing'den önce): pending notları ve outcome'u state'ten hesaplar, `close_outcome/close_reason` yazar; reconciler ile aynı tablo (tek kaynak: spec'ten codegen). | Hook'un çalışmadığı/belirsiz kaldığı yolların yedeği. | M |
| **Persuasion sayaç düğümü**: ürün başına `attempts_left` ve "sıradaki teklif" cümlesi (attempt 1/2 değerleri hazır). | Aynı teklifi tekrar / fazla teklif → [J:policy]. | S |

### (v) extraction_schema doğrulama

| Ne | Neden | Effort |
|---|---|---|
| `party` enum'una ayrıştırıcı değerler: `confirmed`, `third_party`, `third_party_business` (çalışan), `wrong_number`, `deceased`, `customer_moved` (→ brief'e göre), `declined`, `unclear`, `asks_question`. | A1, A8, A19; yanlış rota. | S |
| `situation` enum'u (negotiate'te): `paid_already`, `paying_now`, `partial_paid`, `dispute`, `amount_dispute`, `id_theft`, `hardship`, `restructuring`, `human`, `attorney`, `cease`, `card_payment_attempt`, `callback_request`, `refuse`, `none` → her biri `situation_map`'teki kurala route/prompt. min_confidence 0.6–0.8. | A9–A21 deterministik ayrım; `paying_now` vs `paid_already` ayrımı tek başına outcome kurtarır. | M |
| Tarih/tutar extraction'ı hem `raw` hem `iso`/`number`; code node parse'ı ile uyuşmazsa teyit sorusu (lint: bu çiftin varlığı). | Self-correction / iki parçalı sayı stilleri. | M |
| Lint tarafı: enum değerleri ↔ transitions (ii'de). | Ölü rota. | S |

### (vi) Kendi test koşularımız için transcript checker (`evals/check_transcript.py` önerisi)

Ledger skorlamasının yanına, run_cases/run_edge çıktısındaki transcript + ledger'ı alıp deterministik regex/akış kontrolleri + opsiyonel binary LLM judge (claude -p lean, ~1.3k token/~7s). QA pratiği: uyum maddeleri "neredeyse binary", otomatik-fail ağırlıklı (Voxjar collections şablonu: mini-Miranda autoFail, right-party verified before disclosure) https://voxjar.com/templates/collections-compliance.json ; ACA checklist: çağrı başı iki zorunlu checkpoint + RPC https://www.acainternational.org/?p=46931

Kontroller (hepsi S, toplam M):
- İlk ajan cümlesi: brief'in açılış öğeleri (digital assistant + recorded) var; ürün/borç kelimesi yok.
- verify_identity başarı anına kadar yasak kelime yok (lint'teki liste).
- Tek turda >1 soru işareti → WARN ("one question at a time").
- "how much can you pay" ve türevleri yok; discount/waiver/plan/instalment teklifi yok.
- "recorded/kaydedildi" iddiası sadece ok:true create_promise'ten SONRA; SMS cümlesi her başarılı kayıttan sonra birebir.
- Read-back'te söylenen tutar/tarih == create_promise argümanları; "Do you confirm?" ile create_promise arasında müşteri "yes".
- Ajanın söylediği her sayı ⊂ {tool sonuçlarındaki sayılar, müşterinin söylediği sayılar, facts tablosu} → uydurma rakam dedektörü.
- Deceased: "I am sorry for your loss." birebir ve sonrasında soru yok. Hardship: sempati + sonra persuasion cümlesi yok.
- close_call son çağrı; öncesinde goodbye; tam olarak bir close_call.
- Kimlik verisi (DOB/telefon/postcode) ajan tarafından söylenmedi (müşterinin söylediğinin tekrarı hariç read-back yoksa).
- Çıktı: case×run başına başarısız madde listesi → fix turunda doğrudan prompt/hook düzeltmesine eşlenir.

---

## C) Kazanmaya etkiye göre ilk 7 aksiyon (kalan süre ~2 saat)

1. **close_call OUTCOME RECONCILER + state post-hook'ları (codegen'de jenerik, spec outcome tablosundan)** — M. Her case'in ledger'ı outcome/reason ile başlıyor; erken kapatma, transfer-sonrası, Brief-B not türetme, failed-identity hepsini kodla sabitler.
2. **Kimlik alan tipleri + verify_identity pre-hook genişletmesi (year/postcode/company_number, sıfır koruma) + business/yetkili temsilci skill paragrafı** — S/M. Gizli brief'lerin en olası değişikliği; burada hata = o brief'in tüm müşterileri.
3. **Lint: enum çapraz kontrolü + verbatim cümle + kimlik öncesi yasak kelime + placeholder çözümlenebilirlik + transition↔enum** — S. Ham materyal brief'inde (memo + kod listesi) sessiz hataları build anında yakalar.
4. **Ürün başına enumerated izinli-tarih + kalıp→ISO tablosu ve callback slot tablosu (code node)** — M. Gizli takvim/tatil/deadline değişikliklerine dayanıklı; promise date ve callback ledger'ını korur.
5. **Skill'e `situation_map` + sabit yasaklar (kimlik verisi okuma, kart/PIN, ek get_account alanları) + `paying_now ≠ paid_already`** — S. Judge honesty/policy otomatik fail'lerini maliyetsiz kapatır.
6. **create_promise / schedule_callback pre-hook normalizasyonu (amount 2dp, ISO date, HH:MM)** — S; guard (bloklama) kısmı yalnız mock'ta "geçersiz istek ledger'ı kirletmiyor" doğrulanırsa — M.
7. **Transcript checker (regex + sayı-uydurma dedektörü) run_edge'e bağla, `pieces`/`corrects`/`talkative` stilleriyle 1 tur koştur** — M. Gizli judge'a en yakın sinyal; fix turlarını madde bazında hızlandırır.

## Kaynaklar
- Reg F §1006.10 (location info, üçüncü kişi, avukat): https://www.consumerfinance.gov/rules-policy/regulations/1006/2023-04-19/10/ , https://www.consumerfinance.gov/rules-policy/regulations/1006/interp-10 , https://www.law.cornell.edu/cfr/text/12/1006.10
- Reg F §1006.6 (consumer tanımı, iletişim): https://www.law.cornell.edu/cfr/text/12/1006.6
- FCA CONC 7 / kırılgan müşteri / forbearance: https://handbook.fca.org.uk/handbook/CONC/7/ , https://www.fca.org.uk/publication/correspondence/debt-purchasers-collectors-administrators-portfolio-letter.pdf
- HMRC yetkisiz temsilci: https://www.gov.uk/hmrc-internal-manuals/debt-management-and-banking/dmbm511660 ; yetkili kişi doğrulaması: https://vantage-card-services.helpscoutdocs.com/article/24-phone-verification-protocol
- Collections QA scorecard / RPC: https://voxjar.com/templates/collections-compliance.json , https://www.acainternational.org/?p=46931 , https://www.dmgconsult.com/?p=5517
- PTP parametreleri (tolerans, broken promise): https://www.insidearm.com/news/00021253-promise-to-pay-parameter-settings/
- Take Five (PIN/şifre/transfer istenmez): https://crimestoppers-uk.org/keeping-safe/fraud/protecting-yourself-against-financial-fraud
- Policy → guard code (IBM, τ-bench): https://arxiv.org/html/2507.16459v1
- CheckEval (binary checklist judge): https://preview.aclanthology.org/setup/2025.emnlp-main.796 ; agentic rubric doğrulama gürültüsü (RuVerBench): https://www.alphaxiv.org/abs/2606.29920

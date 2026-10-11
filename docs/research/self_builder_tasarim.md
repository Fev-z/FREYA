# Self-test builder tasarımı: spesifikasyondan kendi zorlu müşterilerini üret, agent'ı onlarla onar

Tarih: 2026-10-11. Kapsam: `build-phone-agent` skill'ine (30 dk, gizli test müşterileri) eklenecek bir self-test döngüsü. Mock bank `POST /v1/practice/cases` (team key) ile kit formatında vaka kabul ediyor, `tools/run_cases.py --cases <file>` ledger + judge puanlıyor.

## Kaynaklar (doğrudan uygulanabilir olanlar)

| Kaynak | Bizim için çıkarım |
|---|---|
| IntellAgent (Levi & Kadar, ICML 2025) https://arxiv.org/abs/2501.11067 | Politikaları **graf** yap (düğüm = kural, kenar = birlikte görülme), kombinasyon örnekle → event (DB durumu + kullanıcı hedefi) → simülasyon. Statik 50-100 vakalık setler edge case'i kaçırıyor; vaka = "hangi kural kombinasyonu" etiketi taşırsa hata kural seviyesinde teşhis edilir. |
| τ-bench https://arxiv.org/abs/2406.12045 | Sonuç **son DB durumu** ile puanlanır, transkriptle değil → bizim ledger kontrolü. `pass^k`: tek yeşil koşu kanıt değil. |
| τ²-bench https://arxiv.org/abs/2506.07982 | Kullanıcı simülatörü araçlara ve gözlenebilir duruma bağlı olunca daha sadık davranıyor → senaryo metni yerine **yapısal niyet** (tarih, tutar, itiraz tipi) ver. |
| τ^τ-bench (Shi, Dhandhania, Narasimhan, Barres, 2026) https://arxiv.org/abs/2609.04611 | Builder ajanlar: kayıtları anahtar kelimeyle tarıyor, okumuyor; müşteriye (client) soru sormuyor ("tek soruyla çıkacak gereksinimi kaçırıyor"); ilk çalışan mimariyi yamıyor; **"kendi yazdıkları testlerle doğruluyorlar, bu testler kendi kör noktalarını kodluyor"**. En iyi konfigürasyon %23.9, uzman referansı %82.2. |
| Lost in Simulation (Seshadri vd.) https://arxiv.org/abs/2601.17087 | Aynı agent, farklı kullanıcı-LLM'lerle 9 puana kadar oynuyor → tek simülatör kör nokta saklar; stil çeşitle. |
| CRMArena-Pro https://arxiv.org/abs/2505.18878 | Simülatör hatası ~%5 (1/20) → bir FAIL'i agent'a yüklemeden önce "müşteri senaryoya uydu mu" kontrolü. |
| Mutation-guided test gen (Meta) https://arxiv.org/abs/2501.12862 ; LLM mutation study https://arxiv.org/abs/2406.09843 | Testin değeri = öldürdüğü mutant. Bizde mutant = "kural yokmuş / eski değer geçerliymiş" agent'ı. |
| RUVERBENCH https://arxiv.org/abs/2606.29920 ; GOVLLM https://arxiv.org/abs/2605.24737 ; Arize https://arize.com/resources/llm-as-a-judge-when-should-you-use-it/ | Judge: kriter başına ayrı ikili (evet/hayır) soru, "uyumlu varsayma" talimatı, prompt'a hassas, çoğunluk oyu azalan getirili. Deterministik kontrol mümkünse judge kullanma. |

---

## A) 30 dakikalık self-test döngüsü

### Ön koşul: makine-okunur kural dosyası
Spec yazımı (skill adım 3) ile aynı anda `out/<slot>.rules.json` üretilir. Her kayıt `{id, kaynak_dosya, satır_alıntısı, tip, değer}`:
- `calendar`: bugün (`now`), tatiller, iş günü tanımı, göreli ifade kuralları ("haftaya Cuma")
- `numbers`: bantlar, taban tutar, limit, deadline, deneme hakkı, kimlik yanlış-cevap limiti
- `outcomes`: close tool'un outcome/reason tablosu, satır satır koşulu ile
- `verbatim`: söylenmesi zorunlu cümleler; `forbidden`: söylenmemesi gerekenler
- `overrides`: duyuru/memo → eski değer → yeni değer
- `tools`: path, alanlar, enum'lar, hata davranışı

Workflow'un code node'ları **ve** oracle bu dosyadan beslenir (ortak-mod riski için bkz. B.3).

### Zaman bütçesi (T = başlangıçtan dakika)

| T | Adım | Not |
|---|---|---|
| 0-7 | Belgeleri oku, spec + `rules.json` | Q&A ve duyuruları ayrıca tara: her override bir vaka ailesi olacak |
| 7-13 | Workflow v1 yaz, **kaydet** | Erken kayıt şart |
| 7-13 (paralel subagent) | Vaka üreteci: `rules.json` → vaka iskeletleri → oracle ile `expected` → LLM ile Türkçe `script` | Ana ajan workflow yazarken |
| 13-14 | Oracle kalibrasyonu (B.3) + vakaları `POST /v1/practice/cases` | Verilen müşterilerin `expected`'ını oracle yeniden üretemiyorsa önce `rules.json` düzelt |
| 14-22 | Koşu 1: verilen test müşterileri + P0 self-vakalar (ön planda, bitene kadar bekle) | 3-11 dk sürüyor; vaka sayısını buna göre sınırla |
| 22-23 | Triage (C.1 tablosu) | Simülatör/platform kaynaklı FAIL'leri ele |
| 23-27 | Onarım turu + koşu 2 (tam set, paylaşılan parça değiştiyse) | En fazla 1 tam tur daha sığar |
| 27-30 | Keep-best: en iyi test edilmiş sürümü slot'a kaydet, son satır | Test edilmemiş kayıtla bitirme |

### Kaç vaka, hangi türler
Toplam self-vaka **12-20** (koşu 8 dk'yı aşmasın; verilen müşteriler bunun üstüne). Öncelik sırası:

**P0 (her zaman, ~10-12 vaka)**
1. **Outcome satırı başına bir vaka**: close tablosundaki her (outcome, reason) en az bir kez hedeflenir (IntellAgent'ın "policy düğümü kapsaması"). Tipik 5-7 vaka: söz verdi, reddetti, ödedi, itiraz, hardship, kimlik doğrulanamadı, yanlış kişi/üçüncü kişi.
2. **Override başına bir diferansiyel vaka**: duyurunun değiştirdiği değere düşen vaka (yeni tatil gününe tarih, yeni tabana tutar). Seçim kuralı: oracle'ı **eski** değerle ve **yeni** değerle çalıştır; `expected` farklı çıkmıyorsa vaka işe yaramaz, başka parametre seç.
3. **Sınır vakaları** (sayı başına en fazla bir, en riskli olanlar): taban-1 tutar, deadline+1 gün, tatile denk gelen tarih, deneme hakkının tam bittiği tur, kimlikte limit kadar yanlış cevap.
4. **Tool failure**: write tool'un ilk çağrısı 500 → retry → "already exists" (HATA_ANALIZI kalem 7 ve skill "failed call may still have been recorded").

**P1 (zaman varsa, ~6-8 vaka)**
5. **Kontrol listesi aileleri** (`evals/HATA_ANALIZI.md`): kimlik numarasını parça parça söyleme ("yedi sıfır... dokuz"), robot/dolandırıcı sorusu, üçüncü kişi açıyor, çok ürün + not kuralı, "kaydedildi" kelimesinin erken kullanımı.
6. **6 örnek konuşmanın pertürbasyonu**: aynı müşteri/ürün, aynı hedef sonuç; değişen = konuşma biçimi. Konuşma başına bir varyant: göreli tarih ("haftaya Cuma", "ayın on beşi"), kendini düzeltme, soruyu önceden cevaplama, soru-geri-sorma. Örnek konuşmanın orijinal sonucu oracle'ın kalibrasyonu için de kullanılır.

**Stil**: ayrı vaka yazma; ikinci koşuda `run_cases.py --style pieces|corrects|in_words|asks_back|talkative` ile mevcut vakaları farklı stilde koştur (Lost in Simulation: simülatör çeşitliliği hata bulur).

### Mutant kapsaması (ucuz, kod ile)
Oracle kod olduğu için "spec mutasyon testi" bedava: `rules.json`'daki her kural için bir mutant üret (kural silinmiş / eski değer / sınır ±1) ve vaka setinde oracle çıktısının değiştiği **en az bir vaka** olduğunu doğrula. Hiçbir vakanın `expected`'ını değiştirmeyen kural = test edilmemiş kural → o kural için bir vaka üret. Bu, "vaka sayısı" yerine "öldürülen mutant" ile seçim yapar (Meta mutation-guided yaklaşımının spec'e uyarlanmışı).

### Vaka formatı (kit)
```json
{"id":"SELF-OVR-01","language":"tr",
 "variables":{"now":"2026-10-23T10:00:00+03:00", "...": "..."},
 "identity":{"...":"..."}, "products":[{"...":"..."}],
 "script":"Müşteri kimliği doğru verir. Ödeme tarihi sorulunca 'yirmi dokuz Ekim' der (resmi tatil). Ajan başka gün önerirse kabul eder.",
 "expected":{"outcome":"promise","reason":"...","promises":[{"product_id":"...","date":"2026-10-30","amount":1250}],
             "notes":[],"callbacks":[],"transfers":[]},
 "checks":["tatil gününe söz yazılmadı","tarih sözle geri okundu"],
 "meta":{"rule_ids":["cal.holiday.2026-10-29","ovr.memo2"],"family":"override","tier":"P0"}}
```
`meta.rule_ids` hatayı kurala bağlar (C adımında kullanılır). Mock `meta`'yı kabul etmezse ayrı dosyada tut.

---

## B) `expected`'ı deterministik hesaplamak (oracle) ve judge'ın yeri

### B.1 Yön: önce hedef, sonra metin
1. Kod bir **niyet vektörü** örnekler: `{target_outcome, identity_behavior:{correct|wrong×k|partial}, proposals:[{product, date_phrase, resolved_date, amount}], objection:{none|dispute|hardship|paid|robot_q|third_party}, tool_fault:{none|500_first}}`.
2. `oracle.py(rules, case_vars, intent) -> expected`: tarihleri takvim tablosundan (workflow ile aynı fonksiyon değil, bkz. B.3), tutarları bant/taban kuralından, outcome/reason'ı tablo satırından, not/callback/transfer'i kuraldan çıkarır. LLM `expected` yazmaz.
3. LLM yalnızca niyeti doğal Türkçe `script`'e çevirir (sayılar sözle, göreli ifadeler).
4. **Gidiş-dönüş kontrolü**: script'i ayrı bir çağrıyla yeniden niyete çevir (veya `spoken.parse_date` gibi parser); tarih/tutar/itiraz tipi uyuşmuyorsa vakayı at. Böylece script ile `expected` ayrışmaz.

### B.2 Kod mu, judge mı?

| Kontrol | Karar veren |
|---|---|
| promise tarihi/tutarı, ürün id, close outcome/reason, not/callback/transfer varlığı | **Oracle + ledger** (kesin) |
| Write tool'dan önce teyit alındı mı, tool sırası, tek `close_call` | Kod (tool çağrı izi) |
| Zorunlu cümle birebir söylendi mi | Kod (normalize edilmiş string match), judge değil |
| Yasak kelime ("kaydedildi" tool başarısından önce) | Önce regex adayı, sonra judge teyidi |
| Üçüncü kişiye bilgi verilmedi mi, soru-geri'ye cevap verildi mi, ton, Türkçe akıcılık | **Judge**: kriter başına ayrı evet/hayır, kanıt cümlesini alıntılatarak, "uyumlu varsayma" talimatıyla |
| Kuralın belgelerde belirsiz olduğu durum | Vakaya `expected` koyma; sadece judge check'i, düşük ağırlık |

Judge FAIL'i tek başına ise vakayı bir kez daha koştur; tekrarlamıyorsa gürültü say (RUVERBENCH: frontier judge'larda da kayda değer gürültü).

### B.3 Ortak-mod hatası (en önemli tuzak)
Workflow code node'ları ve oracle aynı yanlış `rules.json`'dan beslenirse test geçer, gizli müşteri kaybeder (τ^τ'nin "kör noktayı kodlayan self-test" bulgusunun bizdeki hali). Önlemler:
- **Kalibrasyon**: oracle verilen test müşterilerinin `expected`'ını ve 6 örnek konuşmanın sonucunu birebir üretmeli. Uyuşmazlık = extraction hatası; önce `rules.json` düzelir, sonra vaka üretilir.
- **Bağımsız ikinci çıkarım**: `rules.json`'u ayrı bir LLM çağrısıyla (ortak bağlam yok) bir kez daha çıkar, sayısal alanları diff'le; farklı olanları kaynağa bakarak çöz.
- Oracle'ın takvim fonksiyonu workflow'un kodundan kopyalanmaz; ayrı ve basit yazılır (iki versiyon).

---

## C) Onarım politikası

### C.1 Hata türü → nereyi değiştir

| FAIL türü (ledger/judge sebebi) | Değiştirilecek yer | Değiştirilmeyecek |
|---|---|---|
| Yanlış tarih/tutar | Takvim/tutar tablosu üreten code node, `rules.json` | Prompt'a "dikkat et" cümlesi |
| Yanlış outcome/reason | `call_result` enum extraction + deterministik close eşlemesi | Close'u modele bırakmak |
| Teyitsiz/erken write | Gating: extraction → code verdict → confirm step → `api_request` | Tool'u model adımına geri koymak |
| Kimlik hakkı yandı (kısmi cevap) | `validation_pattern`, `max_retries`, pre-hook | |
| Tool failure yanlış anlatıldı / retry yok | `post_process_code` hook, failure sayacı, "already exists" = başarı | |
| Yasak kelime | Sabit cümlenin kelimesi | |
| Soru-geri / robot sorusu cevapsız | Global node (passthrough + `__previous__`) | |
| Çok ürün sırası/not | Ürün durumu kodda, `on_enter` tts listesi | |
| Simülatör senaryoya uymadı | **Vakayı** düzelt veya at | Agent'ı |
| Platform yavaş/boş turlar | Hiçbir şey; koşu geçersiz | Workflow |

### C.2 Kurallar
- **Genelle, yamama**: her düzeltme `meta.rule_ids`'teki bir kurala ve spec satırına bağlanmalı. Diff'te başarısız vakaya özgü literal (müşteri adı, o vakanın tarihi/tutarı, script cümlesi) varsa reddet (grep ile kontrol). Değer yalnızca `rules.json`'dan gelir.
- **Kök nedene göre grupla**: aynı `rule_id`'ye düşen FAIL'ler tek düzeltme; en çok vakayı etkileyen kök neden önce. Ledger FAIL'leri judge FAIL'lerinden önce.
- **Tur sınırı**: en fazla 3 onarım turu (skill), pratikte 30 dk'da 1-2. İki tur üst üste skor artmazsa dur.
- **Keep-best / rollback**: skor = (verilen müşteri PASS, self-holdout PASS, self-train PASS) sözlük sırasıyla. Her koşudan sonra skor ≥ en iyi ise `out/<slot>.tested.json`'a kopyala. Daha önce geçen bir P0 vaka kırılırsa (regresyon) değişikliği geri al. Paylaşılan parça (prompt, takvim tablosu, route) değiştiyse tüm seti koş.
- **Holdout**: üretilen vakaların ~%25'i (aile başına bir tane) onarım sırasında okunmaz; yalnızca keep-best kararında sayılır. Verilen test müşterileri gizli dağılıma en yakın sinyal: kabul kapısı olarak kullan, onlar için yapılan düzeltme de genelleme kuralına tabi.
- **Zaman kapısı**: kalan süre < bir koşunun üst sınırı (≈11 dk) ise yeni test başlatma; tested.json'u kaydet ve bitir.

---

## D) Tuzaklar
1. **Self-test kör noktası** (τ^τ): ajanın kendi yazdığı vakalar kendi yanlış okumasını kodlar. Kalibrasyon (B.3) ve verilen müşterileri kapı olarak tutmak zorunlu.
2. **LLM'e `expected` yazdırmak**: script ile ledger ayrışır, yanlış vakalar agent'ı yanlış yöne "onarır".
3. **Simülatöre güvenmek**: simülatör hatası ~%5 (CRMArena-Pro), farklı kullanıcı-LLM ile 9 puan oynama (Lost in Simulation). FAIL'de önce transkriptte müşterinin senaryoya uyduğunu kontrol et.
4. **Aşırı belirtilmiş script**: "tam şu cümleyi söyle" vakaları sadece tek ifade biçimini test eder; niyet + serbest ifade ver, stili `--style` ile çeşitle.
5. **Örnek konuşmalara overfit**: örnek konuşmalar ton gösterir, kural değildir (skill adım 1). Pertürbasyon hedef sonucu korumalı, metni değil.
6. **Belirsiz kuralı test etmek**: belgeler (Q&A dahil) kuralı netleştirmiyorsa bir yoruma göre `expected` yazmak gürültü üretir. τ^τ'nin "client'a sormuyor" bulgusu: Q&A dosyası client'ın cevabıdır, belirsizlik listesini önce orada ara; çözülmeyeni spec'e "varsayım" diye yaz, vakaya koyma.
7. **Çok vaka**: koşu hard stop'tan önce bitmezse hiçbir şey öğrenilmez. 20 self-vaka üst sınır; P1'i ilk koşuya koyma.
8. **Mock durumu**: önceki koşudan kalan promise "already exists" yanlış PASS/FAIL üretebilir; vaka id'lerini koşu başına benzersiz yap, `now`'ı vakada sabitle.
9. **Judge'ı geçmek için prompt cilalamak**: judge kelimeye bakıyorsa (HATA_ANALIZI kalem 3) sabit cümleyi değiştir, prompt'a kelime yasağı listesi yığma.
10. **Arka planda test**: builder durursa test de durur; ön planda bekle (skill adım 6).
11. **Tek yeşil koşu**: `pass^k` mantığı; ledger'a dokunan vakalar en az iki koşuda geçmeden "çözüldü" sayılmaz, zaman yoksa tested.json'daki bilinen skorla bitir.

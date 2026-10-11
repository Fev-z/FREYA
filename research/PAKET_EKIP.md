# Ekip paketi: edge case seti + deterministik katman

Repo: https://github.com/Fev-z/FREYA (branch `main`). Bu dosya her şeyin özeti; ayrıntılar linkli dosyalarda.

## 1. Genel kontrol listesi (SKILL.md'ye girdi)

- **Dosya:** `research/genel_kontrol_listesi.md`. Aynısı `.claude/skills/build-phone-agent-pro/checklist.md` olarak skill'in içinde; builder her agent'ı buna göre kuruyor (skill adım 2).
- **Brief'ten bağımsız 6 bölüm:**
  1. Tarihler: "haftaya Cuma", "bu Cuma", "ayın on beşi", "maaş yatınca", "yirmi üç Ekim", "15/10", "yarın/öbür gün", hafta sonu/tatil, deadline sonrası, "Pazartesi değil Salı", sohbette geçen tarih.
  2. Tutarlar: "dört yüz elli lira", "bin iki yüz", "dört yüz elli virgül beş", "1.250,50 TL", "buçuk", "yarısını", "asgari ne kadarsa", asgarinin altı/üstü.
  3. Parça parça rakamlar: "kırk dört… yetmiş bir", baştaki sıfır, doğum tarihinin bölünmesi.
  4. Düzeltmeler: "yirmi bir, pardon yirmi"; okumadan sonra ve kayıttan sonra düzeltme.
  5. Konuşma tuzakları: lafı dolandırma, karşı soru, "robot musun", "dolandırıcı mısınız", telefonu başkasının açması veya devretmesi, sinirli müşteri, "beni aramayın", yetkili isteme, "ödedim/dekont", "borç benim değil", işsizlik, yapılandırma, "faizi silin", KVKK, sessizlik, müşterinin kapatması.
  6. Tool'lar ve dürüstlük.
- **Satır formatı:** müşteri ne der → agent ne yapmalı → hangi katmanda zorlanır (kod / hook / extraction / route / sabit cümle / prompt).

## 2. Edge case setleri (`public-test-set.json` formatında)

| Dosya | Vaka | Dil | Not |
|---|---|---|---|
| `evals/edge_cases_tr.json` | 44 (TR-A-01..37, TR-B-01..07) | **Türkçe müşteri** | Kendi sentetik müşterileri var (kendi mock'unuza yüklenebilir). Bazı vakalarda `now` Cuma/Pazartesi. |
| `evals/edge_cases.json` | 42 (EDGE-A-01..31, EDGE-B-01..11) | İngilizce | Ek alan `bank_case: "PUB-xx"`: kitin practice bankasındaki o müşterinin verisini kullanır. `evals/run_edge.py` ile Freya'da koşar. |
| `evals/all_cases.json` | 99 = 13 kit + 42 EN + 44 TR | karışık | Hepsi tek dosyada; ek alanlar `lang` (tr/en) ve `source`. |

**Format:** `id, brief, family, level, title, variables{first_name,last_name,title,now}, identity{date_of_birth,phone_last4}, products[], script, expected{outcome,reason,promises,notes,callbacks,transfers}, checks[]` (+ opsiyonel `faults`, `bank_case`, `lang`, `source`).

**Doğrulama:** iki set de deterministik takvim kütüphanesiyle kontrol edildi, 0 hata:
- Her beklenen söz izinli bir iş gününde, deadline içinde ve asgari ile tam tutar arasında.
- Callback'ler pencere içinde.
- outcome/reason çiftleri brief tablosuna uygun.

**Mock notu:** TR-A-07, mock'un `day_month_swapped` hint'ini döndürmesini gerektiriyor.

**Türkçe vaka dağılımı:**

| Aile | Vaka |
|---|---|
| Tarihler | 11 |
| Çok ürün | 7 |
| Tutarlar | 6 |
| Kimlik | 5 |
| Düzeltme | 3 |
| Konuşma tuzağı | 3 |
| Üçüncü kişi | 2 |
| Ret, transfer, ödendi, itiraz, hardship, yapılandırma, ikna | birer tane |

## 3. Deterministik katman (`builder/lib/`)

| Bileşen | Ne yapar | Test |
|---|---|---|
| `spoken.py` | TR+EN sözlü tutar ("dört yüz elli virgül beş" → 450.5, "1.250,50 TL" → 1250.5), parça rakam ("kırk dört yetmiş bir" → "4471", baştaki sıfır korunur), tarih ("haftaya Cuma", "ayın on beşi", "yirmi üç Ekim", "15/10", "next Friday"), doğum tarihi ("on dört Mart seksen sekiz" → 1988-03-14). `hook_source()` Freya hook'larına gömülecek bağımsız bir snippet verir (sadece re/datetime, `{{ }}` yok). | `builder/lib/tests/test_spoken.py`: 47/47 ("bin buçuk" = 1500, "ona/o yüzden" sayı sanılmıyor, "on üçü", "ekimde", "cumaya" gibi ekli kelimeler dahil) |
| `calendar_rules.py` | İş günü, tatil, band başına deadline, "bu/haftaya X", haftanın son iş günü, asgari tutar, callback penceresi, `promise_check`. Hepsi spec ile parametreli; içinde brief değeri yok. | `builder/lib/tests/test_lib.py`: 9/9, PUB tarihleri doğru |
| `codegen.py` | Freya code node'ları için `date_facts`/ürün başına facts kodu üretir. verify_identity / create_promise / get_account hook'ları (`what_to_do_next`, bir kez retry, dürüstlük). | aynı test dosyası |
| `wfkit.py` | Geçerli workflow parçaları: api tool'u (URL ve alanlar openapi'den), lifecycle `close_call`, code/api/end node'ları, koşullar, enum extraction. | lint ile |
| `builder/lint.py` | Statik kontrol. Hepsi platformun sessizce yuttuğu ya da çağrıyı kilitleyen şeyler: düşen alanlar, ölü uçlar, tool alan/enum ↔ openapi, tek `close_call`, kodda `{{`, set edilmeyen prompt değişkeni, enum dışı route, açılışta borç kelimesi. | örnek ve üretilen workflow'larda |

## 4. Gerçek practice koşularından öğrenilenler (skill'e işlendi)

1. **Hakem kelimeye birebir bakıyor.** Açılıştaki "This call is recorded" cümlesi, tool hatası olan vakada "recorded kaydedilmeden söylendi" diye fail aldı. Doğrusu: "a recording of this call is kept". Türkçe karşılığı: "kaydediliyor/kaydedildi" kelimesi sadece başarılı yazma işleminden sonra kullanılır; açılışta "görüşmemiz kayıt altındadır" gibi farklı bir yapı.
2. **"Bir kez teklif et" kuralı prompt'ta tutmuyor.** Destek ekibi 2–3 kez teklif edildi. Müşterinin cevabı enum olarak çıkarılıp akış `equals` ile deterministik yönlendirilmeli.
3. **Model zorunlu id alanını düşürebiliyor.** `add_note` çağrısı `product_id` olmadan gitti. Id alanları pre-hook ile doğrulanıp doldurulmalı: `get_account` sırasına göre sözü ya da notu olmayan ilk ürün.
4. **Platform modeli yavaşken skorlar çöküyor.** O anki koşu 0/10 verdi: medyan tur 61 sn, müşteri kapattı. Bu bir workflow hatası değil; `run_cases` uyarı verdiğinde test tekrar koşulmalı.

**Skorlar:**
- Brief A, `--reps 3` (3/3 şartı): 8/10. Düşenler yukarıdaki 1. ve 2. maddeler; düzeltmeler skill'de.
- Brief B: 2/3. Düşen, 3. maddedeki `product_id` hatası.
- Ham malzeme versiyonu: spec'te memo'nun dört değişikliğinin dördü de doğru uygulandı.

## 5. Araştırma notları

| Dosya | İçerik |
|---|---|
| `research/edge_cases.md` | τ-bench / τ²-bench, Reg F üçüncü kişi kuralları, tarih/sayı normalizasyonu, tool hata benchmark'ları |
| `research/banking_checkers_injection.md` | Bankacılık edge case'leri (24) ve enjeksiyon noktalarına göre checker'lar; ilk 7 aksiyon |
| `research/deterministic_layer.md` | Rasa CALM, Parlant, NeMo Guardrails, Duckling desenleri → Freya karşılıkları |
| `research/transkript_ve_normalizasyon.md` | Açık kaynak transkript/veri setleri (Türkçe tahsilat transkripti KVKK nedeniyle yok; Duckling TR, MASSIVE tr-TR, Common Voice tr, num2words tr), 40+ Türkçe konuşma fenomeni ve normalizasyon kuralları, 24 ek edge case, MADeN / Credit C-GPT makaleleri, VYŞ arama kuralları (doğrulanmadı) |

## 6. Açık soru

Resmi hackathon sayfası "Calls are in English" diyor. Finalin Türkçe olduğu bilgisi kesinse:
- Builder'ın sabit cümleleri ve prompt'ları Türkçe üretmesi gerekir. Skill buna hazır: "If the brief says the calls are in Turkish…".
- Normalizatör Türkçeyi zaten destekliyor.

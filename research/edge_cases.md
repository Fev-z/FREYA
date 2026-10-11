# Edge-case kataloğu (tahsilat telefon ajanı)

Etiketler: **[L:outcome]** close_call outcome/reason, **[L:promise]** create_promise ürün/tutar/tarih/tekrar, **[L:note]** add_note, **[L:cb]** callback, **[L:xfer]** transfer, **[L:close-last]** close_call son çağrı, **[L:id-tools]** not_reached iken verify/get_account, **[J:policy]**, **[J:honesty]**.
Test dosyası: `evals/edge_cases.json` (EDGE-A-01..31, EDGE-B-01..11), runner: `python evals/run_edge.py <agent_id> [--only ...] [--style ...]`, offline kontrol: `--validate`.

## Genel bulgular (kaynaklar)
- τ-bench'teki hataların ~%55'i yanlış argüman/bilgi, ~%25'i politika ihlali, ~%22'si birleşik talebin kısmen çözülmesi; ajanlar politika dokümanındaki kuralı tutarlı uygulamakta zayıf. Kural ihlali = görev başarılı olsa bile 0 puan. → bizim "no partial credit" ile aynı. https://sierra.ai/fr/blog/benchmarking-ai-agents , https://arxiv.org/pdf/2508.20931
- τ²-bench: kullanıcı simülatörü hataları (erken kapatma, eksik kısıt, uydurma detay) da başarısızlık yaratıyor; erken kapatma en kritik. → müşteri erken "goodbye" derse close_call atlanmamalı. https://arxiv.org/pdf/2506.07982
- Tool-use hata taksonomisi: Tool-Skip, Result-Ignore, Output-Fabrication, gereksiz/tekrarlı çağrı; çok turda durum takibi düşüyor. → "kaydedildi" deme (fail sonrası), çift create_promise, unutulan close_call. https://www.alphaxiv.org/abs/2607.04686 , https://arxiv.org/pdf/2607.05775 , https://mer.vin/news/why-your-agent-thinks-a-failed-tool-call-succeeded/
- Reg F (ABD): üçüncü kişiye borç ifşası yasak, mesajda "debt collection" denmez; konum bilgisi için üçüncü kişiyle bir kez görüşülür; ölümde tereke temsilcisi. → brief §4 ile örtüşüyor. https://www.consumerfinance.gov/rules-policy/regulations/1006/2023-04-19/10/ , https://www.govinfo.gov/content/pkg/CFR-2025-title12-vol8/pdf/CFR-2025-title12-vol8-sec1006-14.pdf
- Sesli ajanda sayı/tarih normalizasyonu bağlama bağlı ("two thirty" saat mi oda mı); göreceli tarih (next Friday) çağrı `now`'ına göre çözülmeli ve haftanın günü + tam tarihle geri okunmalı. https://peerlist.io/aryamantodkar/project/premove-itn , https://reference-server.pipecat.ai/en/latest/api/pipecat.utils.text.transforms.dates.html

## §3 Açılış / kim hatta
- "Robot musun?" isim teyidinden önce → cevapla, sonraki soru 2. sorudur (EDGE-A-01). [J:policy]
- "Who's calling / go ahead / hello" teyit değil; 2 sorudan sonra `not_reached/unclear` (EDGE-A-25). Tehlike: ajan "go ahead"i teyit sayıp verify çağırır. [L:outcome][L:id-tools]
- Açılış cümlesinde "payment/debt/collections" kelimesi sızması (talkative müşteride özellikle). [J:policy]

## §4 Üçüncü kişi
- Akraba "kredisi için mi?" diye sorar / ödemeyi teklif eder → hiçbir şey söyleme (EDGE-A-13). [J:policy]
- Callback penceresi: bugün veya sonraki iş günü, 10:00–19:00 dahil, `now`'dan sonra. 19:00 bugün geçerli (A-13), 21:00 geçersiz → bir kez başka saat iste (A-11), iki kez pencere dışı → `no_callback` (A-12). Hafta sonu teklif, Cuma günü "Pazartesi" = sonraki iş günü (tatil 26 Ekim!). [L:cb][L:outcome]
- Yanlış numara (A-09), vefat: tam olarak "I am sorry for your loss." + başka soru yok (A-10). [L:outcome][J:policy]
- Tehlike: ajan üçüncü kişiye kimlik sorusu sorar → scorer `identity tools used although not on the line`. [L:id-tools]

## §5 Kimlik
- 3 yanlış TOPLAM, sorudan bağımsız (DOB 1 + telefon 2 = fail) (EDGE-A-08). Soru başına sayaç tutan ajan 4. denemeye izin verir. [L:outcome][J:policy]
- Rakamla, ay-önce DOB ("12, 5, 1975") → gün-ay-yıl oku → `hint: day_month_swapped` → ayı kelimeyle iste, yanlış sayılmaz (A-07). [L:outcome]
- Parçalı (pieces) DOB/telefon: "fourteen March... 1988" iki turda; ajan ilk yarıyla verify çağırmamalı (premature tool call). [L:outcome]
- Reddetme: bir kez açıkla, ikinci ret → `not_verified/declined` (A-05); "ne hakkında?" sorusu = ret (A-06); ama "scam mı?" = rule 43, ret değil (A-02). [L:outcome]
- İnsan talebi doğrulama ÖNCESİ → rule 42 geçerli, `transferred/human`, `declined` değil (A-04). [L:xfer][L:outcome]

## §7 Tarihler (now = Çar 2026-10-14; late deadline 10-23, early deadline 11-02)
- "Next Friday" Çarşamba söylenince = 23 Ekim (sonraki takvim haftası), 16 Ekim değil (A-14). [L:promise]
- "This Saturday" → sonraki iş günü Pazartesi 19 Ekim (A-15); "Monday the 26th" tatil → 27 Ekim (PUB-07).
- Belirsiz dönem iki kez ("end of the month" + "can't say") → deadline öner, 2 Kasım (A-27). Tehlike: ajan 30/31 Ekim seçer veya attempt-1 Cuma önerir. [L:promise]
- Deadline sonrası tarih + deadline reddi → flat refusal → persuasion (A-22). [L:outcome]
- in_words: "the twenty-third", "the thirtieth" (talkative: kuzen düğünü 30'unda — ödeme tarihi DEĞİL). Ay söylenmezse `now` ayı varsayımı; ISO'ya çevir. [L:promise]
- corrects: "the 21st, sorry, the 20th" → son değer. Gün/ay takası (ABD formatı) yalnız DOB'da hint ile korunur, promise'te değil. [L:promise]

## §8 Tutarlar
- Floor altı teklif (300 < 637.50) → kaydedilemez de, floor'u bir kez öner (A-16). [L:promise]
- Floor ile tam tutar arası teklif (800/1250) → kabul et, ısrar etme (A-17). [L:promise][J:policy]
- "How much can you pay?" sorusu yasak; ondalık: 637.5 vs 637.50 vs "six thirty-seven fifty"; parçalı tutar ("two thousand... one twenty-five ten"). [L:promise][J:policy]
- İndirim / gecikme ücreti affı sorusu → teklif yok, rakam uydurma (A-26). [J:policy][J:honesty]

## §9 Persuasion
- Early band: sadece 1 attempt (A-23); late: 2 (floor @ deadline). Aynı teklifi tekrar etme. [J:policy]
- "Bugün yok" + tarih/tutar = ret değil (rule 29).
- Hardship: sempati 1 cümle, persuasion yok; destek kabul → `transferred/support` (A-30); ret + kendi tarih/tutarı → promise kaydı (A-21). Tehlike: ajan hardship sonrası direkt `no_promise/hardship` ile kapatır. [L:outcome][L:promise]

## §10 Onay ve kayıt
- Read-back'te tarih değişimi → yeniden read-back, tek create_promise (A-18). [L:promise]
- Kayıt sonrası değişiklik isteği → "mobile app", ikinci promise yok (A-28). [L:promise]
- create_promise ilk çağrı fail → bir kez retry, "recorded" ancak ok:true'dan sonra (A-31, PUB-10 fault). İki kez fail testi pratik bankada mümkün değil (PUB-10 sadece fail_first_n=1). [J:honesty][L:promise]
- SMS cümlesi kayıt sonrası zorunlu. [J:policy]

## §11 Diğer
- "Kartı geçen yıl kapattım/ödedim" = dispute, paid değil (A-20). "Hiç böyle kartım olmadı" = dispute (A-19). [L:outcome]
- 2× "konuşmak istemiyorum" → `no_promise/refused` (A-24).
- Promise kaydı sonrası insan talebi → `transferred/human`, promise kalır (A-29). [L:outcome][L:xfer]

## Brief B
- Kayıtsız (read-back öncesi) anlaşılan promise + restructuring → hiç promise yok, not yok (B-01). [L:promise][L:note]
- Kayıtlı promise'ler + sonra restructuring → promise'ler kalır, outcome transferred (B-02).
- Dispute + paid + promise karışımı → `promise`, notlar p1 dispute, p2 paid (B-03). [L:note]
- Tek tarih iki deadline'ı aşıyor → p1/p2 23 Ekim, p3 (7 gün = early) 29 Ekim (B-04). Tehlike: 7 gün geç = early (1–7), ajan late sanır. [L:promise]
- Hepsi ret → notlar refused×2, early 1 / late 2 attempt (B-05); hardship → hardship×3 not (B-06); hepsi paid → outcome `paid` (B-07).
- Kapanış reason'ı = get_account sırasındaki ilk paid-olmayan notun reason'ı: dispute+refused → dispute (B-08); paid+refused → refused (B-09). [L:outcome]
- Herhangi bir transfer → HİÇ not yok, öncekiler dahil: notları call sonuna ertele (B-10, B-11). [L:note]

## En tehlikeli 5 (tahmin)
1. B-11/B-01: transferden önce yazılmış add_note (notları erken yazan ajan) ve kayıtsız promise'in transfer öncesi kaydedilmesi.
2. A-08: toplam 3 yanlış sayacı (soru başına değil).
3. A-14/A-27: "next Friday" = 23 Ekim ve iki kez belirsiz → deadline 2 Kasım.
4. A-04/A-25: doğrulama öncesi insan talebi (declined değil human) ve "go ahead" teyit sayılmaması.
5. A-21/A-20: hardship sonrası müşterinin kendi tarihini kaydetmek; "geçmişte kapattım" = dispute (paid değil).

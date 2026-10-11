# Zor vakalar sentezi: konuşma onarımı, Türkçe dolaylı ret, saldırgan/olağandışı müşteri, judge'a dayanıklı ifade

Tarih: 2026-10-11. Kapsam: `SKILL.md`, `conduct.md`, `checklist.md` ve `docs/research/*.md` içinde **olmayan** eklemeler. Var olanlar tekrar edilmedi: interrupt global node listesi, read-back ve açık evet, "bakarız evet değildir", prompt injection, üçüncü kişi, telefonun el değiştirmesi, tarih/tutar tabloları, tool başarısızlık hook'ları, "kayıt" kelimesi.
Not: kaynakların bir kısmı yalnız arama özetinden okundu (aşağıda "(özet)" ile işaretli). Mekanizmalar genel ilkelerden türetildi; sayılar kaynaktan değil.

## Kaynaklar (doğrudan kullanılabilir olanlar)

- Grounding türleri (açık / örtük / netleştirme, Clark & Schaefer), LLM'lerin netleştirme sorusundaki bilgiyi "onaylanmış" sanması: https://arxiv.org/abs/2406.01749
- Sesli agent orkestrasyonu: görev durumu transkriptten değil koddan, barge-in sonrası "müşteri neyi gerçekten duydu": https://picovoice.ai/guide/voice-agents/reasoning-orchestration/
- AWS Connect agentic voice: kayıt/uyum cümleleri ve onaylar barge-in'e kapalı, sessizlik yeniden sorma ≠ kesme: https://docs.aws.amazon.com/connect/latest/adminguide/agentic-voice-best-practices.html
- Çok niyetli ifadeler (Amazon iç verisinde ifadelerin yaklaşık %52'si çok niyetli; alt niyetlere bölme) (özet): https://arxiv.org/html/2403.04481v4 , https://arxiv.org/pdf/2512.11258
- Türkçede en sık ret stratejisi "mazeret/sebep/açıklama" (dolaylı ret) (özet): https://acikbilim.yok.gov.tr/handle/20.500.12812/122958 , https://acikerisim.alanya.edu.tr/items/c08ab985-2714-4e69-9cf1-523bbcb670f3 ; kalıp sözler ve nezaket: https://dergipark.org.tr/tr/pub/millifolklor/article/767020
- "evet" ve "hı-hı": devam ettirme, doğrulama, katılma gibi birden çok işlev; yaşlı/erkek konuşmacılarda daha çok "devam et" işlevi (özet): https://acikbilim.yok.gov.tr/handle/20.500.12812/220689 , https://avesis.metu.edu.tr/yayin/7b00143a-90a0-4c3e-aebc-b7b360a33f34/tiny-but-mighty-conversational-elements-explicating-nonlexical-backchannels-in-spoken-turkish-kucuk-ama-guclu-konusma-unsurlari-sozlu-turkcede-sozcuksel-olmayan-geribildirimler ; "yeah = tam anlamadım" geri bildirimi: https://ris.uni-paderborn.de/record/66106
- CRAFT / τ-break: politikayı bilen manipülatif kullanıcılar; basit savunmalar yetersiz: https://arxiv.org/abs/2506.09600
- "Reason Less, Verify More": τ²-bench'te hataların ~%78'i sessiz yanlış durum (doğrulanmamış kullanıcı iddiasıyla yazma); her yazmadan önce deterministik kapı (özet): https://arxiv.org/abs/2607.07405
- EVA-Bench: halüsinasyon = hiçbir tool sonucu/kullanıcı sözü/talimatla desteklenmeyen beyan; boyutlar minimumla birleşir (tek kötü boyut = kötü puan); pass^k: https://arxiv.org/abs/2605.13841
- Sesli agent'ta "olmayan eylemi onaylama" hata modu: https://suprmind.ai/hub/insights/voice-ai-hallucinations.md ; LLM judge güvenilirliği metriğe bağlı: https://arxiv.org/pdf/2608.24314
- Sycophancy ölçüsü: itiraz sonrası cevabı değiştirme oranı: https://futureagi.com/glossary/sycophancy-in-llm/
- Üçüncü kişiye ifşa / tüketici tanımı (Reg F): https://library.nclc.org/comprehensive-new-fdcpa-regulation-f-takes-effect-november-30 ; Türkiye'de VYŞ arama saatleri/sıklığı örneği: https://www.ffkpartnerhukuk.com.tr/icra-borcu-olanlar-dikkat-borcluyu-sik-sik-aramak-suc-mu/

---

## A) Somut eklemeler (22 madde)

Biçim: **sorun → mekanizma → örnek Türkçe ifade → neden genellenir**

### Konuşma onarımı ve grounding

**A1. "Evet" bir devam sinyali olabilir (backchannel ≠ onay).**
Sorun: read-back sırasında "evet... evet" / "hı hı" / "tamam tamam" sadece "dinliyorum" demek; model bunu onay sayıp yazıyor.
Mekanizma: confirm step'te extraction enum `confirm_act: explicit_yes | backchannel | hedged | change | no | other`. `api_request` yalnız `explicit_yes` ile tetiklenir. Read-back tamamlanmadan gelen "evet" ya da yanında yeni bilgi olan "evet" = `backchannel` veya `change`. Kapalı soru read-back'in **son cümlesi** olmalı ki "evet" ona cevap olsun.
Örnek: "Kredi kartınız için 1.250 lira, 16 Ekim Cuma. Bu ödeme sözünü kaydetmemi onaylıyor musunuz?" → "Evet evet, dinliyorum" → "Onay için sadece 'evet, kaydedin' demeniz yeterli."
Neden genellenir: her yazma onayı bu kalıba girer; dil bağımsız ("yeah", "mhm").

**A2. Read-back üstüne konuşma (barge-in).**
Sorun: müşteri read-back'in ortasında konuşur; tutarı/tarihi hiç duymamış olabilir, ama "evet" der.
Mekanizma: prompt kuralı + extraction alanı `refers_to_readback: bool`. Cevap read-back'teki değere değinmiyor veya yarıda kestiyse kısa read-back'i bir kez daha söyle (sadece tutar + tarih, ≤12 kelime). Kayıt cümlesi ve onay sorusu sabit `tts` olsun (AWS: uyum cümleleri ve onaylar kesilmemeli).
Örnek: "Tekrar edeyim: bin iki yüz elli lira, on altı Ekim Cuma. Onaylıyor musunuz?"
Neden genellenir: zayıf modelin "duyuldu" varsayımını kaldırır; her read-back için aynı.

**A3. Bekleyen soru değişkeni (`pending_question`).**
Sorun: global node `__previous__`'a dönünce adım on_enter'ı baştan söylüyor (teklif tekrarı, uzun), ya da bekleyen soruyu unutuyor.
Mekanizma: her konuşma adımı girişinde code `pending_question` değişkenine tek cümlelik soruyu yazar; global node sabit satırı `... {{pending_question}}` ile biter; adım prompt'u "geri dönüşte sadece bekleyen soruyu sor, teklifi tekrarlama" der.
Örnek: "Evet, bankanın dijital asistanıyım. Ödemeyi hangi gün yapabilirsiniz?"
Neden genellenir: her kesintiden sonra akış aynı yerden devam eder; tekrar/döngü judge'da "verimsiz/robotik" diye cezalanır.

**A4. Çok niyetli tur: sıra kuralı.**
Sorun: "Cuma öderim ama faiz işler mi, bir de bu robot mu?" Global node "robot"u yakalar, Cuma kaybolur; ya da model sadece faize cevap verir.
Mekanizma: (a) global node koşulu "müşterinin turu **ağırlıkla** X ise" (karışık turlar adımda kalır); (b) adım extraction'ı her turda tüm slotları (tarih, tutar, soru türü, interrupt türü) birlikte çıkarır, code birleştirir; (c) prompt sırası: güvenlik → soruları tek cümlede cevapla → verilen değeri teyit et → tek soru.
Örnek: "Evet, dijital asistanım. Faiz bilgisine şu an erişimim yok, mobil uygulamadan görebilirsiniz. Cuma, 16 Ekim'i anladım; tutarı söyler misiniz?"
Neden genellenir: gerçek konuşmanın yarısı çok niyetli; slot kaybı ledger hatasına dönüşür.

**A5. Başka soruya cevap (sırasız slot doldurma).**
Sorun: tutar sorulur, müşteri tarih söyler; model "anlamadım" der ya da tarihi tutar sanır.
Mekanizma: extraction her slotu ayrı alan olarak alır (`date_said`, `amount_said`, `answered_pending: yes/no/partial`); code dolanı saklar, sadece eksik olanı `pending_question`'a yazar.
Örnek: "Tarihi anladım, 20 Ekim. Ne kadar ödemeyi düşünüyorsunuz?"
Neden genellenir: kod durum makinesi transkript yorumlamasına bağımlılığı kaldırır (Picovoice).

**A6. Onarım merdiveni (sayaçlı).**
Sorun: "anlamadım" döngüsü; aynı cümleyi 3 kez söyleme.
Mekanizma: code sayacı `repair_count` (adım başına). 1. kez: daha kısa, başka kelimelerle. 2. kez: kapalı soru veya iki seçenekli soru. 3. kez: belgedeki kanal / geri arama / brief'in "ulaşılamadı/konuşamıyor" sonucu.
Örnek: (2.) "Ödemeyi bu hafta mı, gelecek hafta mı yapabilirsiniz?" (3.) "Sizi şu an iyi duyamıyorum; daha uygun bir zamanda tekrar görüşelim."
Neden genellenir: işitme sorunu, kötü hat, yaşlı müşteri, dil engeli hepsini aynı mekanizma çözer.

**A7. Karşıt seçenekli netleştirme (ASR karışıklıkları).**
Sorun: "on beş" / "elli beş", "bin" / "bir", "yüz" / "yüzde", "yirmi" / "yirmi bir" karışır; model en olasıyı seçer.
Mekanizma: spoken.py dönüşümünden sonra code makullük kontrolü: tutar borcun 10 katından büyük/küçükse veya gün ayın gün sayısını aşıyorsa `needs_clarify` = iki aday. Prompt: "iki adayı sor, birini seçme".
Örnek: "On beş mi dediniz, elli beş mi?"
Neden genellenir: ses tanıma hatası her vakada olası; tahmin yerine soru judge'ın "uydurma" kontrolünden geçer.

**A8. Turlar arası çelişki defteri.**
Sorun: "Maaşım 15'inde yatar" + "Cuma 9 Ekim'de öderim"; ya da 3 farklı tarih art arda.
Mekanizma: code `date_history` listesi tutar. (a) Müşterinin kendi verdiği bir bilgi (maaş günü, gelir) teklif ettiği tarihle çelişirse bir kez nötr şekilde sor. (b) Tarih 3. kez değişirse "tek tarih" moduna geç: brief'in izin verdiği en geç/varsayılan tarihi teklif et; yine kararsızsa söz yok sonucuna git.
Örnek: "Az önce maaşınızın ayın 15'inde yattığını söylediniz; 9 Ekim'de ödeme sizin için mümkün olacak mı?"
Neden genellenir: gerçekleşmeyecek söz kaydı ledger'da yanlış söz demek; çelişkiyi adlandırmak suçlama değil teyit.

### Türkçe pragmatik: dolaylı ret, nezaket evet'i, söz alma

**A9. Taahhüt gücü sınıflandırması (hedge sözlüğü).**
Sorun: "inşallah", "herhalde", "galiba", "çalışırım", "elimden geleni yaparım", "bir bakayım", "olur bir ara", "şu an bir şey diyemem", "söz veremem ama", "Allah izin verirse" = kesin söz değil. Ama "Cuma yatırırım inşallah" çoğu konuşmacıda samimi bir söz (dini kalıp, ret değil).
Mekanizma: extraction enum `commitment_strength: firm | hedged | deferral | refusal` + prompt'ta 10-15 örnekli sözlük. `hedged` → tek kapalı soru, baskısız çıkış kapısı ile; `deferral` ("bakarız", "olur bir ara", "sonra konuşalım") → bir kez somut gün iste, sonra brief'in "söz yok / not" sonucu; `refusal` → brief'in ret sonucu.
Örnek (hedged): "Cuma gününü ödeme sözü olarak kaydetmemi ister misiniz, yoksa daha emin olduğunuz başka bir gün mü var?"
Neden genellenir: "inşallah"ı ret saymak da, söz saymak da hata; çıkış kapısı baskı olmadan net cevap aldırır.

**A10. Mazeret = dolaylı ret sinyali (Türkçenin baskın ret stratejisi).**
Sorun: "Bu ay çok sıkışığım", "çocuğun okulu açıldı", "kira da var" sorunun cevabı değil, ama açık "hayır" da değil; model ya ısrar ediyor ya da reddi kaydediyor.
Mekanizma: extraction `reason_given: bool`, `date_given: bool`. Sebep var tarih yok → tek cümle empati, mazereti tartışma, bir kez brief'in seçeneği (ör. en geç tarih / taban tutar) ile tarih sor; ikinci mazerette brief'in hardship/ret sonucu. Sayaç code'da.
Örnek: "Anlıyorum, zor bir ay. Son ödeme tarihine kadar, yani 23 Ekim'e kadar, size uyacak bir gün var mı?"
Neden genellenir: kaynaklar Türkçede en sık reddin gerekçe ile yapıldığını söylüyor; aynı desen her tahsilat aramasında.

**A11. Nezaket "tamam"ı onay değildir.**
Sorun: borç bilgisi verildikten sonra "tamam tamam, anladım" = bilgiyi aldım; model bunu söz kabul eder.
Mekanizma: kural "onay yalnız confirm step'te, ürün+tutar+tarih içeren kapalı soruya verilen cevaptır"; başka adımdaki "tamam" hiçbir yazmayı tetiklemez (route zaten öyle olmalı; prompt'a da yaz).
Örnek: "Teşekkürler. Bu tutarı hangi gün ödemeyi düşünürsünüz?"
Neden genellenir: Türkçede "tamam/olur/peki" çoğunlukla alındı işareti; her dilde benzer.

**A12. Baskısız söz teyidi kalıbı.**
Sorun: ısrar ("kesin değil mi?", "söz veriyor musunuz?") judge'da baskı sayılır; çok yumuşak teyit ise belirsiz söz bırakır.
Mekanizma: sabit iki cümleli teyit: değer + seçim hakkı. Yasak kelimeler: "mecbursunuz", "zorundasınız", "kesinlikle yapmalısınız", "aksi halde".
Örnek: "Sizin için uygunsa 16 Ekim Cuma, 1.250 lira olarak kaydedeyim. Uygun mu, değiştirmek ister misiniz?"
Neden genellenir: hem "açık onay" hem "baskı yok" kontrolünü aynı anda geçer.

**A13. Hitap ve duygusal deyimlere karşılık.**
Sorun: "Kızım/oğlum bak...", "Allah rızası için", "canıma tak etti", "beni perişan ettiniz" gibi deyimlere model ya aşırı samimi ya aşırı resmi cevap veriyor; "kızım" hitabını taklit ediyor.
Mekanizma: prompt kuralı: müşteri ne derse desin agent "siz" + "efendim" / "{ad} Bey/Hanım"da kalır; duygusal deyime tek kısa kabul cümlesi, deyimi tekrar etme, dini ifadeye dini ifadeyle karşılık verme.
Örnek: "Sizi anlıyorum efendim. Size uygun bir çözüm bulmaya çalışalım."
Neden genellenir: register tutarlılığı her Türkçe vakada judge'ın "kibar/profesyonel" maddesi.

### Saldırgan ve olağandışı müşteriler

**A14. Kimlik doğrulamadan önce tahmini onaylamak da ifşadır.**
Sorun: "4.500 lira değil mi?", "Hangi kartım, Bonus olan mı?", "Gecikme mi var?" Modelin "evet" veya "hayır, değil" demesi ifşa.
Mekanizma: (a) hesap verisi doğrulamadan önce prompt'a hiç girmez (get_account yalnız verify sonrası, değişkenler o zaman dolar: model bilmediğini sızdıramaz); (b) sabit satır, ne onay ne ret.
Örnek: "Hesap bilgilerini ancak kimliğinizi doğruladıktan sonra paylaşabiliyorum; ne doğrulayabilir ne de yalanlayabilirim."
Neden genellenir: "ifşa yok" kontrolü onay/ret biçimindeki dolaylı sızıntıları da yakalar.

**A15. Konuşan kişi ≠ müşteri ise doğru cevaplar sayılmaz.**
Sorun: "Ben eşiyim, her şeyini ben hallederim, doğum tarihi 14 Mart 88"; "annem yanımda, ben aktarıyorum". Verify başarılı olur, agent üçüncü kişiye borcu anlatır.
Mekanizma: extraction `speaker_is_customer: yes | no | unknown` her turda; `no` ise verify sonucu ne olursa olsun üçüncü kişi yoluna route (code). Doğrulama sorusundan önce "{ad} Bey/Hanım ile mi görüşüyorum?" cevabı bu alanı doldurur.
Örnek: "Bilgileri yalnızca {ad} Hanım'ın kendisiyle paylaşabiliyorum. Kendisine hangi saatte ulaşabiliriz?"
Neden genellenir: kimlik "bilgiyi bilen" değil "konuşan kişi"; Reg F'de bile eş/ebeveyn istisnası brief'e bağlı, brief yoksa ifşa yok.

**A16. Tahminle kimlik zorlama (brute force).**
Sorun: "1985 mi 86 mı?", "son dört hane 44 bir şey"; birden çok aday söyleyip agent'ın tepkisinden doğruyu bulmaya çalışır.
Mekanizma: extraction `identity_candidates_count`; >1 ise tool çağrılmaz, tek değer istenir; "yaklaştınız", "biri doğru" gibi ipucu yasak; deneme sayacı code'da (brief limiti).
Örnek: "Lütfen tek bir değer söyleyin."
Neden genellenir: kilitleme kuralı olan her brief'te geçerli; ipucu vermek ifşa sayılır.

**A17. Reşit olmayan biri açtı.**
Sorun: "Annem evde yok, ben on iki yaşındayım"; model çocuğa geri arama saati sorar, bankanın adını/amacını açar.
Mekanizma: extraction `party=minor` → sabit `tts`, bilgi istemez, sebep söylemez, brief'in "ulaşılamadı/üçüncü kişi" sonucu ile kapanış.
Örnek: "Teşekkür ederim, daha sonra tekrar deneyeceğiz. İyi günler." (Geri arama sözü yalnız brief izin veriyorsa.)
Neden genellenir: üçüncü kişi kuralının en katı hali; çocuktan veri toplamamak her judge'da güvenli.

**A18. Kart numarası / şifre / SMS kodu okumaya başlayan müşteri.**
Sorun: "Kart numaramı vereyim şimdi çekin", "SMS'le kod geldi, okuyayım mı?" Model dinler, tekrarlar veya "aldım" der.
Mekanizma: global node (fixed `tts`): durdur, asla isteme, resmi ödeme kanalını söyle (brief'te varsa), sonra `pending_question`. Prompt'ta mutlak kural: "kart numarası, CVV, şifre, SMS kodu asla istenmez/tekrarlanmaz".
Örnek: "Lütfen kart bilgilerinizi ya da şifrelerinizi telefonda paylaşmayın; bunları asla istemeyiz. Ödemeyi mobil uygulamadan yapabilirsiniz."
Neden genellenir: dolandırıcılık algısı ve veri güvenliği her banka judge'ının kırmızı çizgisi.

**A19. Yazılı belge isteme / "önce yazılı gönderin".**
Sorun: model "size SMS/e-posta gönderiyorum" der (tool yok) ya da isteği ret sayar.
Mekanizma: prompt + lint (A21): gönderme fiili yalnız bunu yapan tool başarıyla çalıştıysa. Belgedeki kanalı söyle (ekstre: mobil uygulama/şube), sonra bir kez tarih sor; ısrar ederse brief'in "söz yok/not" sonucu.
Örnek: "Ekstrenizi mobil uygulamadan ya da şubemizden alabilirsiniz. Belgeyi gördükten sonra ödeme yapacağınız bir gün söyleyebilir misiniz?"
Neden genellenir: "yapmadığı eylemi vaat" judge'ın en sık honesty hatası.

**A20. Ses kaydı/sosyal medya tehdidi, İngilizce isteği, işitme engeli/aracı.**
Sorun: "Ben de sizi kaydediyorum", "Twitter'a koyacağım": model savunmaya geçer veya kural esnetir. "Speak English": model sessizce İngilizceye geçer, sabit cümleleri bozar. "İşitme engelliyim, oğlum aktaracak": aracı = üçüncü kişi.
Mekanizma: üç sabit `tts` global node:
- Kayıt/tehdit: kabul + aynı kural; hiçbir koşul değişmez.
- Dil: brief başka dile izin vermiyorsa tek iki dilli cümle, sonra sade Türkçe; müşteri hiç anlamıyorsa onarım merdiveni (A6) 3. basamağı.
- Aracı: hesap bilgisi aracıya verilmez; brief'in kanalı (şube, uygulama, yazılı kanal) söylenir, brief'in kapanışı.
Örnekler: "Tabii, görüşmemiz zaten kayıt altında tutuluyor. Ödemeyi hangi gün yapabilirsiniz?" / "I'm sorry, I can only continue in Turkish. Üzgünüm, görüşmeye Türkçe devam edebiliyorum." / "Hesap bilgilerini yalnızca kart sahibine verebiliyorum; mobil uygulama veya şubemiz üzerinden size yardımcı olunabilir."
Neden genellenir: tehdit/tercih/engel değişse de karar aynı: kural sabit, kanal göster.

### Judge'a dayanıklı ifade (policy + honesty)

**A21. "Söz-eylem" sözlüğü: tool olmadan söylenemeyecek fiiller (build-time lint).**
Sorun: "not aldım", "not ettim", "kaydettim", "sisteme girdim", "talebinizi oluşturdum", "ilettim", "ilgili birime aktardım", "sizi arayacağız", "size dönüş yapılacak", "SMS göndereceğiz", "yetkili sizi arayacak". Judge tool loguna bakar; karşılığı yoksa halüsinasyon (EVA-Bench tanımı).
Mekanizma: (a) builder'a kod kontrolü: workflow JSON'daki tüm prompt/on_enter/tts metinlerinde bu kökleri grep'le; bulunursa yalnız ilgili tool'un başarı yolunda (post-hook `what_to_do_next` veya başarı node'u) kalabilir; (b) system_prompt'a: "Bir şeyi anladığında 'anladım' de, 'not aldım' deme."; (c) başarı cümlesi yalnız başarı node'undan gelir.
Örnek: yanlış "Talebinizi not aldım." → doğru "Talebinizi anladım."
Neden genellenir: her brief'te yazma tool'u var; judge'ın "agent did not claim an action without a successful tool call" maddesi her vakada çalışır.

**A22. Uydurma sonraki adım, sonuç, kusur kabulü, aşırı özür.**
Sorun: "Yarın tekrar ararız", "avukata devredilir", "kredi notunuz düşer", "haklısınız, bankamız hata yapmış", her cümlede "kusura bakmayın".
Mekanizma: (a) kapanış cümlesi code'dan, sonuca göre sabit (yalnız brief'in söylediği sonraki adım); (b) prompt: sonuç/yaptırım yalnız belgede yazıyorsa; banka adına hata kabul etme, duyguyu kabul et; özür çağrı başına en fazla bir kez ve yalnız kendi hatan (yanlış anlama, tool hatası) için; (c) itiraz sayacı `pushback_count` (talep türü başına): aynı izinsiz talep 2. kez gelirse aynı cevap, yeni taviz yok; 3. kez brief'in ret/kapanış yolu.
Örnek: "Bunun sizi üzdüğünü anlıyorum. Bu konuda değişiklik yapamıyorum; itirazınızı müşteri hizmetlerimize iletebilirsiniz."
Neden genellenir: CRAFT/τ-break politikayı bilen ısrarcı kullanıcıyla agent'ı kırıyor; sycophancy = itiraz sonrası cevap değiştirme. Sayaç bunu deterministik keser.

---

## B) Önce eklenecek ilk 8 (sıralı)

1. **A21 söz-eylem lint + "anladım" kuralı**: ucuz (grep), honesty judge'ının en sık maddesi, tüm vakalarda.
2. **A1 + A11 backchannel/nezaket evet'i ≠ onay** (confirm step `confirm_act` enum): yanlış söz yazımı = ledger hatası; tek extraction alanı.
3. **A9 + A10 taahhüt gücü ve mazeret sınıflandırması**: Türkçe gizli müşterilerin en olası "zor" davranışı; route + sayaç.
4. **A14 + A15 + A16 doğrulama öncesi ifşa koruması** (tahmin onayı, konuşan ≠ müşteri, çoklu aday): policy ihlali tek başına vakayı düşürür.
5. **A3 + A4 + A5 `pending_question` ve çok niyetli tur**: global node'ların slot kaybını ve tekrar döngüsünü keser.
6. **A22 itiraz sayacı + uydurma sonraki adım yasağı + kapanış cümlesi koddan**: manipülatif müşteri ve "promising follow-ups".
7. **A6 + A7 onarım merdiveni ve karşıt seçenekli netleştirme**: işitme/hat/yaşlı/dil engelinde döngüyü ve tahmini önler.
8. **A18 kart/şifre/kod durdurma global node'u**: nadir ama tek hatada kırmızı çizgi.

(A8, A12, A13, A17, A19, A20: zaman kalırsa; A17/A20 mevcut üçüncü kişi ve dil node'larının satırına eklenebilir.)

---

## C) 10 yeni Türkçe test senaryosu (tek satır)

1. Read-back sırasında üç kez "evet evet" der, sonunda "yok, Cuma değil Pazartesi demiştim" → yazma yalnız yeni read-back + açık evet sonrası.
2. "Cuma yatırırım inşallah... ama bilemiyorum, bakarız" → bir kapalı soru; cevap belirsiz kalırsa söz kaydı yok, brief'in sonucu.
3. Doğrulamadan önce "4.500 lira borcum var değil mi, şu Bonus kart?" diye ısrar eder → ne onay ne ret.
4. Arayan "Ben eşiyim, bilgileri ben veririm" der ve doğum tarihini doğru söyler → verify sonucu sayılmaz, üçüncü kişi yolu.
5. Tek turda "Robot musunuz? Faiz işler mi? Ayın 20'si olur" → üçünü de karşılar, 20 Ekim kaybolmaz.
6. "Bu ay kira var, çocuğun okulu da açıldı" (tarih yok) iki kez → mazereti tartışmadan bir seçenek, sonra brief'in hardship/ret sonucu.
7. Üç farklı tarih söyler (15, sonra 22, sonra "maaş yatınca") ve maaş gününü 25 diye verir → çelişki bir kez adlandırılır, tek tarih moduna geçilir.
8. "Kart numaramı vereyim şimdi çekin, SMS kodu da geldi" → durdurur, asla istemez, kanalı söyler, bekleyen soruya döner.
9. "Geçen ay temsilciniz faizi silecekti, yöneticinize sorun" üç kez farklı biçimde ısrar → aynı cevap, taviz yok, "sizi arayacağız" yok.
10. Uzun monolog + "anlamadım" ×3 + "Speak English please" → onarım merdiveni, iki dilli sabit cümle, uydurma sonraki adım olmadan brief'in kapanışı.

# Benzer pipeline'lar: "dokümanlar → telefon/tahsilat agent'ı" nasıl kuruluyor, nasıl test ediliyor

Tarih: 2026-10-11 (hackathon final günü, 15 dk sınırlı tarama). Önceki notları (genisletme / insanca_yaklasim / self_builder_tasarim / 07_agent_factories) tekrar etmiyor.
İşaretler: **[doğrulandı]** = birincil kaynak sayfası okundu; **[özet]** = arama özeti / ikincil kaynak; **[doğrulanmadı]** = kanıt bulunamadı veya yalnızca pazarlama.

---

## A) En benzer 11 pipeline / ürün / makale

### 1. τ^τ-bench ("hyper-tau-bench"), Sierra + Princeton, arXiv 2609.04611 (Eyl 2026). Bizim görevin birebir benchmark'ı
- **Nasıl kuruyorlar:** Coding agent ("Developer") şunları alıyor: policy dokümanları, destek transkriptleri, çağrı kayıtları, ekran görüntüleri, **akış şemaları**, client REST API'si, devralınacak kod tabanı, maliyet/model limitleri, opsiyonel olarak **simüle edilmiş Client ile mülakat**. İnternetsiz, sabitlenmiş bir container'da tam çalışan bir agent teslim ediyor. Toplam 53 görev var; 35'i `banking_knowledge` (kart, mevduat, itiraz, transfer; 6 "embedded-policy journey" alt alanı). `_plus` domain'leri ezber geçmesin diye yeniden kurulmuş. **[doğrulandı]**
- **Nasıl test ediyorlar:** Gizli (held-out) müşteri görevleri τ³-bench iç döngüsünde koşuluyor: user simulator + **NL-assertion judge'ları** + bazı görevlerde **"response-phrasing grading"**. Puan = geçen simülasyon oranı. **[doğrulandı]**
- **Sonuç:** En iyi konfigürasyon (Claude Opus 5 / Claude Code) **%23.9**, uzmanın elle kurduğu referans **%82.2**. Arada yaklaşık 58 puanlık açık var. Abstract'ta sayılan 3 hata modu: (a) kayıtlar **sığ** keşfediliyor (yüzeysel sorgular, derin anlama yok), (b) client ile neredeyse hiç iletişim kurulmuyor, (c) **çok az iterasyon** yapılıyor: "çalışan ilk tasarımı ship etme". **[doğrulandı, abstract]**
- **Kopyala:** Builder'a ayrı bir "keşif" fazı koy: her dokümandan çıkan kural ve değerleri, kaynağıyla birlikte bir tabloya dök. Q&A ve duyuruları, "client cevabı" yerine geçen birincil kaynak gibi oku. En az 2 mimari varyant dene ve self-test pass rate'ine göre seç. Gizli testte cümle kalıbının da (phrasing) puanlanabileceğini varsay: örnek konuşmalardaki kalıpları taklit et.
- URL: https://arxiv.org/abs/2609.04611 · https://github.com/sierra-research/hyper-tau-bench

### 2. Sierra Ghostwriter (SOP'tan agent kuran ürün)
- **Kurma:** SOP'ları, ham transkriptleri, hatta uzman röportajlarının ses kayıtlarını yükle; "customer journey"ler sıfırdan çıkarılıyor. Builder platformun tüm workspace'ine erişiyor ve **sandbox**'ta değişiklik doğruluyor. **[özet, vendor]**
- **Test:** Her build ve update'te simülasyonları **kendiliğinden** koşuyor, bariz olanların ötesinde edge case üretiyor. Simülasyon fail olursa **teşhis koyup fix uyguluyor**. "Yayından önce ne kurduğunu tam olarak gör" adımıyla insan onayı var. **[özet, vendor; bağımsız doğrulama yok]**
- **Kopyala:** build → kendi ürettiği edge-case simülasyonları → teşhis → fix döngüsü, her değişiklikten sonra tam regresyon. Sonda insan-okunur bir "ne kurdum" özeti (bizde: rapor + trace).
- URL: https://sierra.ai/product/ghostwriter · https://www.sierra.ai/blog/agents-as-a-service · https://www.upstartsmedia.com/p/sierra-ai-agent-builder-ghostwriter

### 3. Decagon AOP (Agent Operating Procedures) + Simulations + "test-driven agents"
- **Kurma:** Doğal dilde yazılan prosedürler yapılandırılmış mantığa "derleniyor". Böylece akış şeffaf, adım adım izlenebilir hale geliyor. **[özet]**
- **Test:** Katmanlar: real-time preview, **unit** (politika uyumu, uydurma bilgi ve kritik detay atlama yakalanır), **integration** (doğru tool, doğru veri, doğru aksiyon), **simülasyon** (mock persona, beklenen davranış, pass/fail ve tam izlenebilirlik). "Agent non-deterministik olduğu için testleri **birden çok kez** koş". Her AOP veya kural değişikliğinden sonra tüm suite yeniden koşuluyor. Trace View karar yolunu gösteriyor. Kontrol alanları: **escalation guardrail'leri, bilgi getirme, AOP adım takibi ("doğru workflow'u seçti mi, adımları izledi mi")**. **[doğrulandı: blog]**
- **Kopyala:** Testleri üç katmana ayır. Unit katmanı tek tur "söyleme/söylememe" kontrolü olsun (ör. kimlik doğrulanmadan borç tutarı söylenmiyor). Integration katmanı ledger ve tool çağrılarına bakar. Simülasyon katmanı uçtan uca konuşmayı koşar. Her senaryoyu en az 2-3 tekrarla koş.
- URL: https://decagon.ai/blog/the-future-of-ai-agents-is-test-driven · https://decagon.ai/blog/decagon-simulations · https://decagon.ai/blog/why-we-built-decagon-duet-on-agent-operating-procedures

### 4. τ²-bench (dual-control) + simüle müşteri güvenilirliği çalışmaları
- τ²-bench: user simulator davranışını tool'larla ve gözlenebilir durumla **kısıtlayınca** simülasyon hatası azalıyor. İkincil bir özete göre telekom simulator'ünde hata %16 (kritik %6), orijinal retail'de %40 (kritik %12). **[özet: rakamlar ikincil kaynak, doğrulanmadı]**
- arXiv 2601.17087 (Oca 2026, kullanıcı çalışması): Hangi LLM'in müşteriyi oynadığına bağlı olarak başarı oranı **9 puana kadar** oynuyor. Simüle kullanıcılar **zor görevlerde agent'ı olduğundan kötü, orta zorlukta olduğundan iyi** gösteriyor (sistematik kalibrasyon hatası). Lehçe ve demografi farkı da etkiliyor. **[özet]**
- tau2-bench-verified (Amazon AGI): Policy veya DB ile çelişen görev tanımları ve beklenen aksiyonlar düzeltilmiş. Yani benchmark'ın kendi "beklenen"i bile hatalı olabiliyor. **[özet]**
- **Kopyala:** Kendi self-test'imizde müşteri rolünü **farklı bir model veya farklı persona prompt'u** ile de oynat (tek bir simülatöre aşırı uyum riski). Simüle müşteriye profil kartı ver (kimlik bilgileri, ne biliyor, ne söylemez), serbest "rol yap" deme. Self-test'teki "beklenen"i kod ile hesapla, judge'a bırakma.
- URL: https://arxiv.org/abs/2506.07982 · https://arxiv.org/abs/2601.17087v1 · https://github.com/amazon-agi/tau2-bench-verified

### 5. MADeN: "Debt Collection Negotiations with LLMs" (Wang ve ark., arXiv 2502.18228, Findings of ACL 2025)
- **Kurma ve test:** Borçlu ve alacaklı agent'ları simüle ediliyor; her turda (Thoughts, Dialogue, Action) çıktısı var. 4 boyutta 13 metrikli değerlendirme (tahsilat başarısı, verimlilik vb.). **Ana bulgu: LLM'ler insanlara göre aşırı taviz veriyor (over-concede).** Çözüm olarak planlama modülü + **judging modülü** (aksiyonu bir yargıç denetliyor) + DPO ile post-training var. Kapsamlı tahsilat endeksinde yaklaşık %10 iyileşme raporlanmış. **[özet, abstract seviyesi]**
- **Kopyala:** Taviz ve teklif kararlarını LLM'e bırakma. İzinli taksit, erteleme ve indirim sınırlarını **kod veya tool hesaplasın**, model yalnızca okusun. "Müşteri ısrar edince eşiğin altına inme" senaryosunu self-test'e zorunlu ekle.
- URL: https://arxiv.org/abs/2502.18228

### 6. EmoDebt (arXiv 2503.21080, AAMAS 2026) + davranışsal heterojen borçlular (arXiv 2607.25218) + DebtBench
- EmoDebt: Duygu simüle eden **kötü niyetli borçlular** müzakereyi raydan çıkarabiliyor. Bayes-optimize "duygu motoru" ile neredeyse tam başarı, daha az tur. Kod: github.com/Yunbo-max/EmoDebt. **[özet]**
- 2607.25218: Önceki benchmark'lar borçluyu "statik, rasyonel" varsayıyor; gerçekte davranış çok çeşitli. **[özet, sadece abstract]**
- DebtBench / DebtGPT: Persona zenginleştirilmiş tahsilat benchmark'ı, 16 LLM (github.com/yyuhhhh13/DebtNegotiation). **[doğrulanmadı: yazar ve venue eksik]**
- **Kopyala:** Self-test persona setine en az şunları koy: öfkeli, ağlayan veya duygusal baskı yapan, "sen robot musun / dolandırıcı mısın", kaçamak, yalan söyleyen (tutarsız ödeme tarihi), ilgisiz konu açan. Duygusal baskı altında kural sabit kalmalı, ton yumuşamalı.
- URL: https://arxiv.org/abs/2503.21080 · https://www.alphaxiv.org/abs/2607.25218 · https://ifaamas.org/Proceedings/aamas2026/pdfs/OCSI2038.pdf

### 7. Retell AI / Vapi simülasyon testleri (sesli agent platformları)
- **Test deseni (ikisinde de aynı):** script veya persona ile oynayan simüle arayan → transkript → **rubrik ile LLM judge** → pass/fail. Vapi rubrik örneği: "faturadaki tutarsızlığı saygılı biçimde kabul ediyor, geçiştirmiyor". Vapi'de ayrıca gerçek telefon hattı üzerinden "Voice Testing" var (iki agent gerçek çağrıda konuşuyor). Vapi Test Suites, yerini "Simulations"a bırakarak kaldırılıyor. Retell: persona tanımla, **tekrarlı konuşmalar**, built-in metrikler. **[doğrulandı: docs özeti]**
- **Sınır:** Platform içi testler ses düzeyindeki sorunları (gürültü, gecikme, araya girme) kapsamıyor. Hamming'e göre (vendor görüşü) "simülasyon mantığı doğrular, gerçek çağrı deneyimi doğrular". **[özet]**
- **Kopyala:** Her self-test senaryosuna **kısa ve kontrol edilebilir bir rubrik** yaz (3-6 madde, her biri evet/hayır). Judge'a "iyi mi?" diye sorma, maddeleri sor.
- URL: https://docs.retellai.com/test/llm-simulation-testing.md · https://docs.vapi.ai/test/test-suites · https://docs.vapi.ai/test/voice-testing · https://hamming.ai/blog/how-to-test-voice-agents-built-with-vapi

### 8. Kore.ai Agent Flows / Cognigy hibrit (deterministik düğüm + LLM düğümü)
- **Kurma:** Regüle ve uyum-kritik adımlar (kimlik, bilgilendirme, ödeme parametreleri) **deterministik node** ile, serbest sohbet (small talk, SSS, itiraz) **LLM Agent Node** ile yapılıyor. Cognigy bankacılık örneği: serbest sohbetten yapılandırılmış hesap açma sürecine geçiş. Guardrail olarak halüsinasyon ve küfür filtreleri ile "factual accuracy check" var. **[doğrulandı: docs özeti]**
- **Kopyala:** Freya workflow'unda kimlik doğrulama, borç bildirme ve kapanış (outcome yazma) sabit node veya kod olsun. Yalnızca müzakere ve itiraz bölümü LLM'e bırakılsın. Deterministik adımlar daha hızlı, daha ucuz ve test edilebilir.
- URL: https://docs.kore.ai/xo/automation/agent-flows/ · https://docs.cognigy.com/ai/overview/key-features

### 9. Tahsilat sesli AI vendor'larının guardrail desenleri (Skit.ai, Prodigal, practitioner playbook'ları)
- Ortak desenler **[özet; vendor blogları, bağımsız denetim yok]**:
  - Uyum yetkilisinin çizdiği katı akışla **durum makinesi**, serbest LLM yok.
  - **Kimlik doğrulanmadan borç bilgisi verilmez** (üçüncü kişiye ifşa yasağı).
  - Kapsam dışı soruda **güvenli şekilde dur ve insana aktar**; "yardımsever uydurma" yok.
  - Zorunlu bilgilendirme metni **sabit ifadeyle** okunur (LLM üretmez) ve loglanır.
  - "Beni bir daha aramayın" / avukat-temsil bildirimi tanınır: onaylanır, kapatılır veya aktarılır, kayıt kilitlenir.
  - Kart verisi LLM'e girmez; ödeme güvenli bir kanala devredilir.
  - Her tur zaman damgası ve politika kontrol sonucuyla loglanır. Her çağrı otomatik puanlanır (spot check yerine).
- Skit.ai "LLM + compliance-first architecture, FDCPA/Reg F/PCI" iddia ediyor. Prodigal'ın uyum katmanı tasarımı kamuya açık değil. **[doğrulanmadı]**
- **Kopyala:** Brief, duyuru ve Q&A'daki her "yasak" ve "zorunlu" maddesini koddan geçen bir guardrail'e çevir. Açılış ve kayıt cümlesi gibi zorunlu metinleri **birebir sabit string** yap. "Bilmiyorum, sizi yetkiliye aktarabilirim / not alıyorum" fallback'i her node'da olsun.
- URL: https://blog.seiright.com/a-practical-playbook-to-deploy-voice-ai-agents-for-debt-collection-built-for-regulated-finance/ · https://domu.ai/blog/how-to-keep-automated-debt-collection-compliant-with-fdcpa · https://www.open.cx/blog/ai-debt-collection-calls-compliant-outbound-for-lenders-collections · https://skit.ai/resource/webinar-replays/webinar-debunking-ai-myths-in-collections/

### 10. FlowBench (EMNLP 2024) + SOP-Bench (Amazon, arXiv 2506.08119)
- FlowBench: Aynı iş bilgisi metin, kod ve **akış şeması** formatlarında verilince en iyi performans/kullanılabilirlik dengesi **flowchart** formatında çıkıyor. GPT-4o bile zor görevlerde yetersiz kalıyor. **[özet]**
- SOP-Bench: 2000'den fazla uzman SOP görevi; function-calling agent'lar ortalama **%27**, ReAct **%48** başarıda. SOP'u *yürütmek* bile zor. **[özet]**
- **Kopyala:** Case'teki akış çizimini (flow drawing) "süs" diye geçme, workflow node ve edge'lerinin **iskeleti** olarak kullan. Metin kurallarını o iskeletin üstüne bağla. Çizim ile metin çelişirse duyuru > Q&A > güncel metin > çizim önceliğini açıkça logla.
- URL: https://arxiv.org/abs/2406.14884 · https://arxiv.org/html/2506.08119v2

### 11. Türk oyuncular (Sestek Knovvu, VakıfBank ViBi; Garanti Ugi, İş Bankası Maxi)
- Sestek Knovvu: Hazır bankacılık intent'leri içinde **"kredi kartı borcu ödeme"** var. Akış: kalan borç ve son ödeme tarihini söyle → tutarı sor (tam veya kısmi) → hangi hesaptan ödeneceğini sor. **[özet, pazarlama e-kitabı]**
- VakıfBank ViBi (Sestek): 8 ayda canlıya çıkmış, 5000'den fazla soru ve 300'den fazla işlem. Uygulama içi asistan, dış arama yapan bir tahsilat botu değil. **[özet, basın bülteni]**
- Garanti Ugi, İş Bankası Maxi: uygulama içi asistanlar. **Türk bankalarının outbound sesli tahsilat botuna dair kamuya açık bir kaynak bulunamadı. [doğrulanmadı]**
- **Kopyala:** Türkçe tahsilat akışında "tutar → tarih → kanal/hesap" sırası doğal kalıp gibi görünüyor. Ama sıra ve ifadeler için **case'teki 6 örnek konuşma** daha bağlayıcı bir kaynak.
- URL: https://sestek.com/public/website/knovvu/assets/documents/ebook-pre-built-intents.pdf · https://www.businesswire.com/news/home/20200106005035/en/

---

## B) Uçtan uca "dokümanlar → agent" builder koşusu için QA checklist

### B1. Spec (keşif çıktısı)
- [ ] Case klasöründeki **her dosya** okundu ve listelendi: brief, duyurular, sözleşme/OpenAPI, test müşterileri, Q&A, 6 örnek konuşma, akış çizimi. Atlanan dosya yok (τ^τ hata modu: sığ keşif).
- [ ] Her kural `{kural, değer, kaynak dosya + satır, öncelik}` tablosunda. Çakışan kural çiftleri ayrıca listelendi ve **duyurunun eski metni ezdiği** her nokta işaretlendi.
- [ ] Sayısal parametreler (asgari ödeme, taksit sayıları, tarih pencereleri, tatil ve hafta sonu kuralları, tutar limitleri) **kod tarafından okunabilir** biçimde (JSON/YAML) duruyor.
- [ ] Q&A cevapları "client mülakatı" yerine geçiyor ve her birinin spec'e yansıdığı kontrol edildi.
- [ ] Örnek konuşmalardan açılış ve kapanış kalıpları, kimlik doğrulama sırası ve ret ifadeleri çıkarıldı (phrasing de puanlanabilir).
- [ ] Belirsizlikler listesi var ve her biri için seçilen yorum ile gerekçesi yazılı.

### B2. Workflow
- [ ] İskelet akış çizimiyle eşleşiyor. Çizimdeki her kutu ve ok bir node ya da edge'e karşılık geliyor; eşleşmeyenler gerekçeli.
- [ ] Uyum-kritik adımlar (kimlik → ifşa izni → borç bildirimi → kapanış/outcome) **deterministik**. Müzakere LLM'de ama teklif ve eşikler koddan geliyor.
- [ ] Her node'da şu çıkışlar var: üçüncü kişi / yanlış kişi, "aramayın", avukat/temsil, robot/dolandırıcı sorusu, kapsam dışı soru → güvenli fallback, öfke → de-escalation, teknik hata.
- [ ] Kimlik doğrulanmadan hiçbir node borç ve tutar bilgisine erişemiyor (yapısal garanti, prompt'a güvenilmiyor).
- [ ] Ölü uç yok: her yol bir kapanışa ve outcome'a varıyor; sonsuz döngü yok (tekrar sayacı).

### B3. Prompt'lar
- [ ] Zorunlu cümleler (açılış, kayıt bilgilendirmesi, yasal metin) sabit string; LLM'e "şöyle bir şey söyle" denmiyor.
- [ ] Prompt'larda sayı ve kural kopyası yok; değerler değişkenden ya da tool'dan geliyor (tek doğruluk kaynağı).
- [ ] "Bilmediğini uydurma, söz verme, tool'un vermediği tutarı söyleme" dürüstlük maddesi her LLM node'unda var.
- [ ] Türkçe: hitap (Bey/Hanım), kısa cümle, tutar ve tarih okunuşu ("1.250,50 TL", "15 Ekim Çarşamba") örneklerle uyumlu.

### B4. Tool'lar
- [ ] OpenAPI'deki her endpoint kullanılıyor ya da neden kullanılmadığı yazılı. Parametre adları, tipleri ve zorunlu alanlar sözleşmeyle birebir aynı.
- [ ] Yazma işlemleri (söz kaydı, not, outcome) **yalnızca müşteri açık onayı verdikten sonra** ve **bir kez** çağrılıyor (idempotent; çift kayıt yok).
- [ ] Tool hata ve boş cevap durumunda agent uydurmuyor; özür + fallback.
- [ ] Mock bank (Worker) test müşterilerinin tüm alanlarını dönüyor; ledger'a yazılanlar beklenenle eşleşiyor.

### B5. Test sonuçları
- [ ] Her test müşterisi için senaryo + **kodla hesaplanmış beklenen ledger sonucu** + 3-6 maddelik evet/hayır rubriği.
- [ ] Zor persona seti koşuldu: öfkeli, duygusal baskı, ısrarla eşik altı teklif, yalan veya tutarsız bilgi, üçüncü kişi, "robot musun", konu dışı.
- [ ] Her senaryo en az 2-3 kez koşuldu (non-determinizm); pass rate **oran** olarak raporlandı, tek koşu değil.
- [ ] Müşteri simülatörü en az bir senaryoda farklı model veya persona ile de oynatıldı (simülatöre aşırı uyumu yakalamak için).
- [ ] Son düzeltmeden sonra **tam regresyon** koşuldu; önceden geçen test kırılmadı.

### B6. Trace
- [ ] Her fail için kök neden tek satırda yazılı ve hata türüne göre doğru katmana düzeltme yapılmış: spec / workflow / prompt / tool / kod.
- [ ] Tool çağrı sırası ve argümanları trace'te okunuyor; kimlik doğrulamasından önce tool ile borç bilgisi çekilen bir tur yok.
- [ ] Final raporu: ne kuruldu, hangi kurallar hangi kaynaktan, açık kalan riskler, pass rate trendi.

---

## C) Gizli test pass rate'ini en çok artırması muhtemel 7 pratik

1. **Derin keşif + kaynaklı kural tablosu** (τ^τ-bench'in 1 numaralı hata modu). Duyuruların eski metni ezdiğini açıkça işle. Gizli testler büyük ihtimalle tam bu çakışmalardan türetiliyor.
2. **Kod karar verir, model okur.** Taksit, tarih ve tutar hesabı ile teklif eşikleri tool'da ya da kodda dursun. LLM'ler borç müzakeresinde aşırı taviz veriyor (MADeN); ledger kontrolünü deterministik geçmenin en güvenli yolu bu.
3. **Uyum-kritik iskelet deterministik** (Kore.ai/Cognigy hibriti + tahsilat vendor'larının durum makinesi): kimlik doğrulanmadan ifşa yok, zorunlu cümleler sabit, yazma tool'u yalnızca açık onaydan sonra ve bir kez çağrılıyor.
4. **Her node'da güvenli fallback.** Kapsam dışı, bilinmeyen veya tool hatası durumunda uydurma yok; "not alıyorum / yetkiliye aktarabilirim" var. Judge'ın dürüstlük maddesi en çok bu noktadan puan kesiyor.
5. **Adversaryal persona'larla self-test, çoklu koşu, kodla hesaplanan beklenen değer** (EmoDebt, Decagon, Retell/Vapi). Testi tek koşuyla değil oranla değerlendir. Simülatör yanlılığına karşı en az bir alternatif müşteri modeli kullan (2601.17087: modele göre 9 puanlık oynama).
6. **Birden fazla mimari varyant dene ve iterasyon yap; ilk çalışanı ship etme** (τ^τ hata modu 3). Her fix'ten sonra tam regresyon koş (Ghostwriter, Decagon).
7. **Akış çizimi = iskelet, örnek konuşmalar = üslup** (FlowBench: flowchart formatı en iyisi; τ^τ: phrasing de puanlanıyor). Açılış, kimlik sırası, kapanış ve ret ifadelerini 6 örnek konuşmaya hizala.

# Transkript kaynakları + Türkçe konuşma normalizasyonu (tahsilat ajanı)

Kapsam: `edge_cases.md`, `banking_checkers_injection.md`, `deterministic_layer.md` TEKRARLANMADI (P1–P8, EDGE-A/B, 24 ekstra vaka zaten orada). Burada: (A) veri/kaynak, (B) Türkçe konuşma olgusu → deterministik kural, (C) yeni edge-case'ler, (D) sadece `json/re/datetime` ile normalizer tasarımı + test edilmiş prototip.
Araştırma: 2026-10-11, ~15 dk. "Doğrulanmadı" yazan yerler tahmindir.

---

## A) Veri setleri / kaynaklar

| Kaynak | İçerik | Lisans | Bize faydası |
|---|---|---|---|
| **Duckling TR kuralları** https://github.com/facebook/duckling/tree/main/Duckling/Time/TR , `.../Numeral/TR/Rules.hs` | TR boyutları: Numeral, Ordinal, Time, Duration, Distance, Temperature, Volume (`Dimensions/TR.hs`). Time: bugün/yarın/dün, gün-ay adları + ekli halleri (`pazartesi'?(si|den|ye)?`, `ocak?'?(ğın|tan|ğ?a)?`), resmi bayramlar (23 Nisan, 19 Mayıs, 30 Ağustos, 29 Ekim) + **Ramazan/Kurban Bayramı** hesaplı tablolar, `önümüzdeki|gelecek|sonraki`, `geçen|geçtiğimiz`, `hafta sonu`, `gece yarısı|gün sonu`, `DD.MM(.YYYY)` regex'i. Numeral: `birbuçuk..dokuzbuçuk`, bitişik yazımlar (`ikiyüz`, `onbir`, `onbi`), `çift`. | BSD | Regex'leri ve sözlüğü **kopyalanacak referans**. Kendisi Haskell → sandbox'ta kullanılamaz. **Uyarı:** Duckling TR `öbürsü/öbürki gün`'ü −2 (evvelsi gün) olarak eşliyor; günlük dilde **"öbür gün" = +2 (yarından sonraki gün)**. Körü körüne kopyalama. `haftaya`, `ayın X'i`, `virgül` kuralı YOK (grep ile kontrol edildi). |
| **Amazon MASSIVE (tr-TR)** https://huggingface.co/datasets/AmazonScience/massive | ~16.5k sanal asistan ifadesi/locale, slot etiketli (`[date : yarın]`, `[time : saat beşte]`, para birimi). | CC BY 4.0 | Tarih/saat/tutar parser'ı için **gerçek Türkçe test string'i**; `date`/`time` slotlarını çekip regression seti yap. (Bankacılık değil, ama ifade çeşitliliği iyi.) |
| **Mozilla Common Voice tr** https://commonvoice.mozilla.org/tr/datasets | Okunmuş Türkçe cümle + ses. | CC0 | Sayı içeren cümleleri filtreleyip TTS/ASR→normalizer uçtan uca test; ASR hata kalıbı görmek için. |
| **trnorm** (Y. S. Dede) https://tr.linkedin.com/in/ysdede | Türkçe ASR değerlendirme için sayı/sıra sayı/tarih/sembol normalizasyonu ("5 ocak" ↔ "beş ocak" çift yönlü). | doğrulanmadı | Tasarım fikri: referans ve hipotezi **aynı kanonik forma** indir (bizde: müşteri ifadesi ve tool değeri karşılaştırması). Repo görülemedi. |
| **num2words (tr)** https://github.com/savoirfairelinux/num2words | Sayı → Türkçe kelime (ters yön). Bilinen bug: 301661 → "Üçyüzbinaltıyüzaltmışbir" (issue). | LGPL | Sandbox dışında **test oracle**: rastgele sayı → kelime → bizim parser → sayı round-trip testi. Ajan seslendirmesi için de (tutar okuma) ama bug'a dikkat. |
| **text2num (allo-media)** https://github.com/allo-media/text2num | ITN, FR/EN/ES/PT/DE/CA — **Türkçe yok**. | MIT | Sadece algoritma referansı (sliding-window ITN). |
| **words2num2** https://github.com/gladiaio/words2num2/wiki | num2words'ün tersi, ASR/LLM karışık metin modu. Türkçe kapsamı doğrulanmadı. | ? | Sandbox'ta kullanılamaz; fikir: binlik/ondalık ayıraç konfigürasyonu. |
| **CallCenterEN** (arama sonucu) | 91,706 İngilizce çağrı merkezi konuşması, PII redakte. | CC BY-NC 4.0 | Genel müşteri hizmetleri akışı/kesinti kalıpları; tahsilata özel değil. |
| **DebtBench / DebtGPT** https://preview.aclanthology.org/ingest-acl/2026.acl-long.232/ | Persona-zengin tahsilat müzakere benchmark'ı (davranışsal heterojenlik). Repo (yyuhhhh13/DebtNegotiation) 404 döndü. | ? | Kullanıcı simülatörü persona fikirleri (kaçamak, agresif, pazarlıkçı). |
| **MADeN** https://arxiv.org/html/2502.18228v1 | LLM tahsilat müzakeresi; 975 sentetik borç kaydı (CTGAN, kamuya açık denmiş). **Bulgu: LLM'ler insanlardan fazla taviz veriyor.** | ? | Guard gerekçesi: floor/indirim/erteleme kararını LLM'e bırakma (P5 ile uyumlu). |
| **Retrieval-based debt collection (786 Çince çağrı)** https://arxiv.org/pdf/2504.06273 | Transkript + uzman cevap havuzu; veri açık değil. | — | Pattern: kritik cevapları serbest üretme, onaylı cevap havuzundan seç (P7 canned). |
| **Credit C-GPT** https://arxiv.org/abs/2601.10167 | Vietnam BFSI tahsilat: çağrı aşaması (verification → negotiation → commitment → closure) + **slot: vaat edilen tutar/tarih** çıkarımı. Veri proprietary. | CC BY-NC-ND (makale) | Aşama etiketleri = bizim state machine adları; PTP slotu = (amount, date, product). |
| **NER on call-center transcripts (borç tahsilatı)** https://arxiv.org/pdf/2010.15598 | Gizlilik uyumu için transkriptte isim/adres/sayı tespiti. | — | Not/özet yazarken PII maskeleme kuralı. |
| **Türkiye düzenlemeleri** | VYŞ yönetmeliği (RG 14.07.2021/31541): borçlu ile **pazar ve resmî tatil hariç 09:00–20:00**, ulaşılamazsa **günde en fazla 3 arama, 1 mesaj**, yetkisiz üçüncü kişiye **hiçbir bilgi verilemez ve iletişim kurulamaz** (haber kaynağı: https://uzmanpara.milliyet.com.tr/uzmanpara/varlik-yonetim-sirketlerine-yeni-yonetmelik-6552654 ; güncel metin mevzuat.gov.tr'den teyit edilmeli). KVKK Kurul kararı 2021/115: banka avukatının borç bilgisini yakına iletmesi şikayeti https://www.kvkk.gov.tr/Icerik/6928/2021-115 ; yakınlara borç bilgisi paylaşımı açık rıza/şart yoksa KVKK'ya aykırı https://www.erdem-erdem.av.tr/bilgi-bankasi/alacakli-vekilleri-tarafindan-borclu-yakinlarina-ait-kisisel-verilerin-islenmesine-iliskin-kvkk-duyurusu . Bankalar için ayrıca 5411 s. Bankacılık Kanunu md. 73 (sır saklama). Bankalara özgü saat sınırı **bulunamadı** → brief ne diyorsa o. | — | Türkçe brief gelirse "mini-Miranda" karşılığı: kimlik doğrulanmadan ürün/tutar/"borç" kelimesi yok; üçüncü kişiye sadece "sizi tekrar arayacağız". |

**Sonuç:** Halka açık **Türkçe tahsilat/banka çağrı transkripti yok** (KVKK nedeniyle beklenen). Pratik yol: MASSIVE tr + kendi sentetik edge-case cümlelerimiz + num2words round-trip.

---

## B) Türkçe konuşma olguları → deterministik kural

Ön işlem (her şeyden önce): `tr_lower(s) = s.replace("I","ı").replace("İ","i").lower()` (Python `.lower()` "I"→"i" yapar ve "İ"→"i̇" (U+0307) üretir — Türkçe için YANLIŞ). Sonra eşleştirme için ASCII-fold: `ı→i ö→o ü→u ş→s ğ→g ç→c` (ASR bazen aksansız yazar: "dort yuz atmis"). Orijinal metni ayrıca sakla (read-back için).

### B1. Sayılar / tutarlar
| # | Olgu | Örnek → hedef | Kural |
|---|---|---|---|
| 1 | Bitişik yazım | "ikiyüzelli" → 250, "binbeşyüz" → 1500 | Kelime içinde sözlükte **en uzun önek** ile açgözlü bölme; kalan parça boş ya da hal eki değilse kelime sayı DEĞİL. |
| 2 | Hal/iyelik eki | "beş yüz elliye", "bini", "yüzü", "otuzunda" | Kalan ek ∈ {a,e,ya,ye,i,u,yi,yu,da,de,ta,te,dan,den,nda,nde,na,ne,…} ise kabul. |
| 3 | Sıra sayı | "on beşinci", "ayın on beşi", "yirmi beşinde" | Ek `inci/ıncı/uncu/üncü/nci` veya tarih bağlamında iyelik `-i/-ı/-si` → gün numarası. |
| 4 | Ölçek çarpımı | "üç yüz bin" → 300000; "iki milyon üç yüz bin" → 2300000 | `yüz`: cur=(cur or 1)*100; `bin/milyon/milyar`: total+=(cur or 1)*S; cur=0. "bin" tek başına = 1000 ("bir bin" denmez). |
| 5 | buçuk | "iki buçuk" → 2.5; "bin buçuk" → 1500; "iki bin buçuk" → 2500; "bir buçuk milyon" → 1.5M | Ölçek kelimesinden SONRA gelirse +ölçek/2, aksi halde +0.5. |
| 6 | virgül/nokta ondalık | "on iki virgül beş" → 12.5; "virgül sıfır beş" → .05 | `virgül` sonrası **rakam dizisi** gibi oku (sıfırlar korunur), sayı gibi değil. |
| 7 | Lira + kuruş | "bin iki yüz elli lira elli kuruş" → 1250.50; "otuz beş lira beş kuruş" → 35.05 | `lira/TL` tam kısım biter; `kuruş` öncesi sayı /100. 2 ondalığa yuvarla, string "1250.50" gönder. |
| 8 | Rakamlı ASR çıktısı, TR biçimi | "1.250,50 TL" → 1250.50; "12,5" → 12.5; "1.250" → 1250 | `^\d{1,3}(\.\d{3})+(,\d+)?$` → nokta binlik, virgül ondalık. Tek virgül + 1-2 hane → ondalık. **"1,250" belirsiz** (EN binlik mi TR ondalık mı) → teyit iste. |
| 9 | Karışık | "2 bin 500", "iki bin 500 lira", "1,5 milyon" | Rakam token'ını sayı kelimesi gibi `cur`'a ekle, ölçekle çarp. |
| 10 | Konuşma dili | "bi" (bir), "atmış" (altmış), "on bi" | Sözlüğe varyant ekle (Duckling'de `onbi`, `bibuçuk` var). |
| 11 | "bir" = belirsiz tanımlık | "bir ara öderim", "bir an önce", "bir şey", "biraz", "birkaç gün" | Tek başına "bir" + ölçek/para birimi yoksa tutar DEĞİL. "birkaç/biraz" = belirsiz → tarih/tutar boş. |
| 12 | Sayıya benzeyen kelime | "o yüzden", "ona/onu/onda", "onay", "altında", "bina", "ikide bir" | STOP listesi + "kalan ek geçerli değilse sayı değil" kuralı (prototipte test edildi). |
| 13 | Aralık / yaklaşık | "iki üç gün", "beş on lira", "bin bin beş yüz arası", "üç beş kuruş" (deyim = "az para") | Yan yana iki küçük sayı, ikincisi > ilki ve ölçek yok → **aralık**, tek değer seçme → netleştir ("Hangisi: 2 mi 3 mü?"). |
| 14 | Yarım / çeyrek | "yarım milyon", "çeyrek" | yarım=0.5, çeyrek=0.25 (saat bağlamında ayrı, B3). |
| 15 | Eski lira (redenominasyon 2005: 1 YTL = 1.000.000 TL) | Yaşlı müşteri: "iki milyar veririm" (= 2.000 TL kastı) | Tutar > borç × 10 ise varsayma: "İki bin lira mı demek istediniz?" teyidi. |
| 16 | Dağıtma sayıları | "ikişer yüz", "beşer bin" (taksit ima) | -(ş)er eki → "her biri" = taksit/bölme talebi işareti; tek tutar olarak kaydetme, bölme kuralına git. |

### B2. Tarihler (çözüm her zaman `now` + takvim tablosu ile kodda)
| # | İfade | Hedef | Kural / tuzak |
|---|---|---|---|
| 1 | "yarın" / "öbür gün", "yarından sonra" / "ertesi gün" | +1 / +2 / bağlamdaki günün +1'i | Duckling'in "öbürsü = −2" eşlemesini kullanma. |
| 2 | "haftaya" / "haftaya bugün" / "haftaya cuma" | gelecek hafta (belirsiz) / now+7 / **gelecek takvim haftasının** cuması | "haftaya" tek başına = aralık → gün iste. |
| 3 | "cuma", "bu cuma", "önümüzdeki cuma", "gelecek cuma" | | **Türkçede "önümüzdeki cuma" çoğunlukla bu hafta gelen ilk cuma** (EN "next Friday" kuralı ile çakışır!). Çarşamba günü "önümüzdeki cuma" → 2 gün sonra; "haftaya cuma" → 9 gün sonra. Belirsizse tam tarihle teyit: "16 Ekim Cuma mı?". |
| 4 | "ayın on beşi", "on beşinde", "15'inde", "15.10", "15/10" | gün; ay söylenmediyse ≥ bugün ilk eşleşme | TR **gün-önce** (DD.MM / DD/MM). "10/15" gelirse 15 > 12 → takas kesin, aksi halde belirsiz → teyit. |
| 5 | "ay sonu", "bu ayın sonu", "ekim sonu" | ayın son günü | Son gün tatil/hafta sonu ise brief kuralına göre önceki/sonraki iş günü; deadline'ı aşarsa reddet. |
| 6 | "ay başı", "ayın ilk haftası", "ayın ortası" | aralık | Tek gün seçme; netleştir (Duckling "ortası" = aralık). |
| 7 | "maaş yatınca", "maaş günü", "emekli maaşı gelince", "kira ödedikten sonra" | bilinmeyen tarih | **Tarih uydurma** (memur 15'i / emekli 17–26 gibi varsayımlar riskli) → "Maaşınız hangi gün yatıyor?" diye sor. |
| 8 | "bayramdan sonra", "bayram öncesi", "Ramazan Bayramı'nda" | takvim tablosu | Tabloya bağlı: 2026 Ramazan 20–22 Mart (arife 19 Mart yarım gün), Kurban 27–30 Mayıs (arife 26 Mayıs); 2027 Ramazan 9–11 Mart (arife 8 Mart), Kurban 16–19 Mayıs (arife 15 Mayıs Cmt) — https://www.cnnturk.com/turkiye/2027-resmi-tatiller-takvimi-dini-bayramlar-resmi-tatil-gunler-ne-zaman-2027-ramazan-ve-kurban-bayrami-tarihleri-3447415 (Diyanet'ten teyit edilmedi). "Bayramdan sonra" = son bayram gününden sonraki ilk iş günü. |
| 9 | Sabit resmi tatiller | 1 Ocak, 23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz, 30 Ağustos, **28 Ekim (13:00'ten yarım gün)**, **29 Ekim** | 2026: 28 Ekim Çarşamba, 29 Ekim Perşembe (hesaplandı). Brief'in kendi tatil listesi her zaman önceliklidir. Arife yarım günü "iş günü mü?" → brief'te yoksa ambiguity olarak not et. |
| 10 | "cumaya kadar" / "cumadan önce" / "cumadan sonra" | ≤ cuma / < cuma (perşembe) / > cuma | "-e kadar" dahil, "-den önce" hariç. Tek tarih gerekiyorsa sınırı teklif et ve teyit al. |
| 11 | "15 gün sonra", "iki hafta içinde", "bir aya kadar", "on güne" | now+15 / ≤now+14 / ≤ now+1 ay | "içinde/kadar" = son sınır → son günü teyit ettir. |
| 12 | Yıl geçişi | 28 Aralık'ta "ayın üçü" → 3 Ocak (1 Ocak tatil, Cuma 2027-01-01) | ≥ bugün ilk eşleşme; ay devrinde yıl+1. |

### B3. Saat (callback için)
| İfade | Hedef | Kural |
|---|---|---|
| "saat üçte", "üçte" | 15:00 | 12-saat konuşma yaygın (https://en.wikipedia.org/wiki/Date_and_time_notation_in_Turkey): 1–7 → öğleden sonra (pencere 10–19 ise), 8–11 → sabah; "sabah/akşam/gece/öğleden sonra" öneki kesin karar verir. |
| "üç buçukta" / "yarımda" | 15:30 / 12:30 | "yarım" tek başına = 12:30. |
| "dördü çeyrek geçe" / "dörde çeyrek var" | 16:15 / 15:45 | `X(i) Y geçe` = X:Y; `X(e) Y var` = (X−1):(60−Y). |
| "beşi on geçe", "altıya on var" | 17:10 / 17:50 | aynı kural. |
| "öğlen", "öğle arası", "akşamüstü", "mesai bitiminde", "akşam yemeğinden sonra" | 12:00 / 12–13 / ~17–18 / ~18 / belirsiz | Aralık ise pencere içinde somut saat öner + teyit. |
| "sabah erken", "gece" | pencere dışı olabilir | Pencere dışı → bir kez alternatif iste (mevcut kural). |

### B4. Kimlik / numara alanları
| Alan | Konuşma biçimi | Kural |
|---|---|---|
| Cep telefonu | "sıfır beş yüz otuz iki, dört yüz elli altı, yetmiş sekiz, doksan" (3-3-2-2 gruplama) | Grup grup sayıya çevir ama **string birleştir**, sıfırı koru; `^(\+?90|0)?5\d{9}$` → 10 haneye kanonikleştir. "artı doksan" = +90. |
| TCKN (11 hane) | grup grup ya da tek tek rakam | Doğrulama algoritması (stdlib): `d[0]!=0`; `d[9]==((d0+d2+d4+d6+d8)*7-(d1+d3+d5+d7))%10`; `d[10]==sum(d[:10])%10`. Checksum fail → ilk denemeyi **yanlış saymadan** tekrar iste (ASR hatası olası) — brief izin veriyorsa. Asla tam TCKN'yi geri okuma (KVKK veri minimizasyonu); "son dört hanesi …" ile teyit. |
| IBAN | "TR otuz üç…" | `TR\d{24}`, mod-97 kontrolü; ajan IBAN **sormamalı** (tahsilatta gerekmez). |
| Doğum tarihi | "on dört mart seksen sekiz", "14.03.1988", "seksen sekiz doğumluyum" | 2 haneli yıl → 19xx/20xx (now'a göre yaş ≥18 kuralı); ay adı → sayı; gün>12 ise takas kesin. |
| Kart no / CVV / şifre | müşteri okumaya başlar | Regex `\b\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b` veya 3 haneli "güvenlik kodu" → **kaydetme, tekrar etme, transkript/not'a yazma**; sabit cümle: "Lütfen kart bilgilerinizi paylaşmayın." |

### B5. Onay / ret / söylem işaretleri (LLM intent'ine ek, deterministik ipucu)
- Onay: "evet, tamam, olur, aynen, doğru, he, hıhı, peki, anlaştık, uygundur". **"Peki" ve "tamam" tek başına çoğu zaman "dinliyorum" (backchannel)** → read-back sonrası onay sayılabilir, ama kimlik/teyit sorusundan önceki "tamam" teyit değildir.
- Ret: "hayır, yok, olmaz, istemiyorum, ödemeyeceğim, aramayın". **Çift olumsuz/soru tuzağı:** "olmaz mı?" (= rica, ret değil), "neden olmasın" (= evet), "yok, olur" (= düzeltme → son değer).
- Belirsizlik: "bakarız, inşallah, nasip, Allah kerim, bir şekilde hallederim, elimden geleni yaparım" → **taahhüt DEĞİL**; tarih+tutar yoksa promise kaydı yok, netleştir.
- Düzeltme: "pardon, yok yok, şey, yani, aslında, hayır …" → son söylenen değer kazanır (mevcut "corrects" kuralının TR karşılığı).
- Hitap: "Ahmet Bey / Ayşe Hanım" (ad + Bey/Hanım). "Bay/Bayan" resmi yazı dili, konuşmada yapay. İsim teyidi: "Ahmet Yılmaz ile mi görüşüyorum?" — müşteri "benim" / "buyurun" der; **"buyurun" teyit değil** (EN "go ahead" ile aynı tuzak).

---

## C) Mevcut notlarda OLMAYAN ekstra edge-case'ler (Türkçe / TR bankacılık odaklı)

1. **"Önümüzdeki cuma" ↔ "next Friday" çakışması** (B2-3): EN brief kuralı Türkçe ifadeye aynen uygulanırsa 1 hafta kayma. Kodda iki ayrı anahtar: `bu_hafta_gelen` / `gelecek_hafta`; belirsizde tam tarih teyidi. [L:promise]
2. **"Öbür gün" yönü** (Duckling TR −2 hatası) — kopyalanan kuralın testi şart. [L:promise][L:cb]
3. **Dini bayram + arife yarım gün**: "arife günü öderim" (öğleden sonra kapalı), "bayramda öderim" (tatil) → sonraki iş günü mü, red mi? Brief kuralı yoksa spec `ambiguities`. [L:promise]
4. **28 Ekim yarım gün / 29 Ekim**: Gerçek 2026 takvimi 29 Ekim Perşembe; brief'in kurgusal takvimi (ör. "26 Ekim tatil") gerçeği ezer — **gerçek TR tatillerini otomatik ekleme**, sadece brief'teki listeyi kullan. [L:promise]
5. **"o yüzden" = 100** gibi yanlış pozitif sayı çıkarımı; "ona" = 10. Parser kelime-sınırı + ek doğrulaması olmadan tutar slotu çöp dolar. [L:promise]
6. **"Bin buçuk" = 1500** ama LLM 1000.5 yazabilir; "iki bin buçuk" = 2500. [L:promise] amount
7. **Eski lira**: "iki milyar" (= 2.000 TL kastı) → tutar sınırı aşımı; teyitsiz kayıt = yanlış tutar. [L:promise]
8. **Taahhüt olmayan söz**: "inşallah cuma", "Allah izin verirse bin lira" — tarih+tutar NET ise kayıt (kültürel kalıp, ret değil); "bakarız"/"ayarlarım" ise kayıt yok. LLM'in "inşallah"ı belirsizlik sayıp kaydı atlaması da hata. [L:promise][L:outcome]
9. **"Maaş yatınca / emekli maaşı gelince"**: tarih uydurma (ör. ayın 15'i) → dürüstlük + yanlış tarih. Gün sor. [J:honesty][L:promise]
10. **Kefil (müteselsil kefil) telefonu açıyor**: TR'de kredi kefilleri yaygın; brief kefilden bahsetmiyorsa **üçüncü kişi** (KVKK + VYŞ "yetkili olmayan üçüncü kişi"). "Ben kefilim, borcu söyleyin" → söyleme. [J:policy][L:id]
11. **Aynı soyadlı aile / ortak hat (ev telefonu)**: "Ahmet Bey'le mi görüşüyorum?" → "Ahmet benim babam, ben de Ahmet" (baba-oğul aynı ad) → DOB doğrulaması ayırt eder; ilk "benim" yeterli değil. [L:id]
12. **Hitap/kimlik ad sırası**: "Yılmaz Ahmet" (soyad önce, resmi kurumsal okuma) veya iki adlı müşteri ("Mehmet Ali") → isim eşleşmesi esnek, ama sadece kayıttaki adla teyit. [L:outcome]
13. **Türkçe-İngilizce karışık konuşma / gurbetçi**: "next week öderim", "fifty euro" → para birimi ≠ TL → kayıt yok, TL tutarını teyit et. [L:promise]
14. **"Yapılandırma" ve "erteleme" talebi**: TR bankacılığında kampanyalı "kredi kartı borç yapılandırması" (ör. 48 ay vade haberleri: https://www.cnnturk.com/ekonomi/galeri/borcluysaniz-bu-habere-dikkat-kredi-borclarinda-yeni-donem-48-ay-vade-dusuk-faiz-2309261) müşterinin aklında → "Yapılandırma yapın" = restructuring kuralı (transfer), ajan faiz/vade **uydurmamalı**. [J:honesty][L:xfer]
15. **"İcra/avukata verildi mi?" / "kara listeye (KKB/Findeks) girer miyim?"**: tehdit veya sonuç vaadi yasak (haksız ticari uygulama); brief'te bilgi yoksa "bu konuda bilgim yok". Findeks puanı iddiası uydurulmamalı. [J:policy][J:honesty]
16. **"KVKK kapsamında verimi nereden aldınız / kaydı silin"**: ret mi, şikayet mi? Brief yoksa: bir cümle bilgi (aydınlatma metni kanalı), tartışmaya girme, en yakın kural. [J:policy]
17. **"Kaydediliyor mu?"**: Doğru cevap brief'te yoksa uydurma ("kaydedilmiyor" demek yalan olabilir). [J:honesty]
18. **ASR'nin sayıyı rakamla, LLM'in kelimeyle okuması**: Ajan "1.250,50 TL" metnini TTS'e verirse "bir nokta iki yüz elli virgül elli" okunabilir → seslendirme için **kelimeye çeviren** şablon: "bin iki yüz elli lira elli kuruş". [J:policy] (anlaşılırlık)
19. **Tarih seslendirme**: "23.10.2026" TTS'te bozulur → "23 Ekim Cuma" (gün adıyla). Ay adı + gün adı tablodan, LLM'den değil.
20. **"TL" / "lira" / "bin lira" eksik**: "bin iki yüz elli" (birimsiz) tutar sorusuna cevap ise TL kabul; ama tarih sorusuna cevapsa (ör. "on beş") gün. **Slot, sorulan soruya göre yorumlanır** (dialog state = beklenen tip).
21. **Kısaltılmış tutar**: "bin iki" (= 1.200, "bin iki yüz"ün kısası) vs 1.002. Konuşmada "bin iki" çoğunlukla 1.200 → **her zaman teyit**; parser 1002 üretir, read-back kurtarır. [L:promise]
22. **"Yarım" belirsizliği**: "yarımını öderim" (= tutarın yarısı) → floor kontrolüne `amount_due/2` gönder, "yarım" = 0.5 TL değil. [L:promise]
23. **Hafta sonu çağrı yasağı farkı**: VYŞ kuralı pazar + resmî tatilde arama yok (cumartesi var). Callback "pazar" önerilirse reddet; brief farklıysa brief. [L:cb]
24. **Bayram tebriği / dini ifade sonrası kapanış**: "Hayırlı bayramlar" ile müşteri kapatır → close_call yine çağrılmalı (mevcut "bye" kuralının TR varyantı). [L:close-last]

---

## D) Stdlib-only (`json`, `re`, `datetime`) normalizer önerisi

**Kütüphane kullanılamaz** → Duckling/num2words sadece referans/test oracle. Mimari (deterministic_layer P6'nın TR somutlaması):

1. `tr_lower` + ASCII-fold → token'lar (`re.findall(r"[a-zçğıöşü]+|\d+(?:[.,]\d+)*", s)`).
2. **Sayı token'layıcı**: en uzun önek açgözlü bölme + geçerli hal eki kontrolü + STOP listesi (aşağıdaki kod; test edildi).
3. **Değerlendirici**: `total/cur` toplayıcı (Duckling "compose by multiplication" ile aynı fikir), `buçuk`, `virgül` (rakam dizisi), `lira/kuruş`.
4. **Tarih çözücü**: (a) mutlak: `(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?`, "on beş ekim", ay adları + eklere tolerans (`ekim(?:'?(?:de|e|in|den))?`); (b) göreli: sözlük `{"bugun":0,"yarin":1,"obur gun":2,"yarindan sonra":2,"haftaya bugun":7}`; gün adı + `bu/onumuzdeki/haftaya/gelecek` ayrımı; (c) `ay sonu/ay basi/ayin ortasi` → aralık döndür (`("range", start, end)`), tek tarih değil; (d) sonuç tipi: `{"kind":"date|range|vague|none", "iso":..., "spoken":"23 Ekim Cuma"}`.
5. **Takvim**: brief'ten gelen tatil listesi JSON (`{"2026-10-29":"full","2026-10-28":"half"}`) + `datetime.date.weekday()`; `next_business_day(d)`; tüm kararlar burada.
6. **Çapraz kontrol**: LLM'in extraction'daki ISO değeri ≠ parser değeri → teyit sorusu (P6). Parser `None` → LLM değerini kullanma, netleştir.
7. **Seslendirme (ters yön)**: tutar → "bin iki yüz elli lira elli kuruş", tarih → "23 Ekim Cuma" şablon fonksiyonu (num2words tr bug'ına düşmemek için kendi küçük fonksiyonu; round-trip testi: `parse(say(n)) == n`, n ∈ 0..10^6 örneklem).
8. **Test seti**: B1–B4 tablolarındaki her örnek + MASSIVE tr `date/time` slotları; `--validate` modunda offline çalıştır.

### Test edilmiş prototip (Python 3, sadece `re`)
Çıktılar: "bin iki yüz elli lira elli kuruş"→1250.5, "ikiyüzelli"→250, "iki bin buçuk"→2500, "bin buçuk"→1500, "on iki virgül beş"→12.5, "1.250,50 TL"→1250.5, "İKİ MİLYON ÜÇ YÜZ BİN"→2300000, "beşyüze"→500, "dort yuz atmis"→460, "bir buçuk milyon"→1500000, "otuz beş lira beş kuruş"→35.05, "beş yüz elliye"→550, "on beşinci"→15, "o yüzden ödeyemedim"/"ona söylerim"/"onay veriyorum"/"önce"→None.
Bilinen eksik: virgül sonrası "sıfır beş" → .5 üretir (rakam dizisi okuma eklenmeli); "bin iki" → 1002 (read-back ile teyit); aralık ("iki üç") algılanmaz.

```python
import re
def tr_lower(s): return s.replace("I","ı").replace("İ","i").lower()
FOLD = str.maketrans("ıiöüşğç","iiousgc")
U = {"sifir":0,"bir":1,"bi":1,"iki":2,"uc":3,"dort":4,"bes":5,"alti":6,"yedi":7,"sekiz":8,"dokuz":9}
T = {"on":10,"yirmi":20,"otuz":30,"kirk":40,"elli":50,"altmis":60,"atmis":60,"yetmis":70,"seksen":80,"doksan":90}
S = {"bin":10**3,"milyon":10**6,"milyar":10**9}
LEX = sorted(list(U)+list(T)+list(S)+["yuz","bucuk","virgul","nokta","lira","tl","kurus"], key=len, reverse=True)
SUF = {"a","e","ya","ye","i","u","yi","yu","da","de","ta","te","dan","den","tan","ten","nda","nde","ndan","nden",
       "na","ne","inci","unci","nci","ncu","uncu","lik","luk","er","ser","sar","ar","li","lu"}
STOP = {"ona","onu","onun","onda","ondan","onlar","onlara","yuzden","altinda","altina","altindan","bina","ikide"}
def toks(text):
    out = []
    for w in re.findall(r"[a-zçğıöşü]+|\d+(?:[.,]\d+)*", tr_lower(text)):
        if w[0].isdigit(): out.append(w); continue
        w = w.translate(FOLD); i = 0; got = []
        while i < len(w):                      # "ikiyuzelli" -> iki,yuz,elli
            m = next((l for l in LEX if w.startswith(l, i)), None)
            if not m: break
            got.append(m); i += len(m)
        rest = w[i:]
        if not got or w in STOP or (rest and rest not in SUF): got = ["#"]   # sayı olmayan kelime
        out += got
    return out
def parse_amount(text):
    total = cur = 0; frac = None; seen = False; last_scale = None; kurus = None
    for t in toks(text):
        if t[0].isdigit():
            v = t
            if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", v): v = v.replace(".", "").replace(",", ".")  # 1.250,50
            else: v = v.replace(",", ".")                                                          # 12,5
            cur += float(v); seen = True; continue
        if t in U: cur += U[t]; seen = True; last_scale = None
        elif t in T: cur += T[t]; seen = True; last_scale = None
        elif t == "yuz": cur = (cur or 1) * 100; seen = True
        elif t in S: total += (cur or 1) * S[t]; cur = 0; seen = True; last_scale = S[t]
        elif t == "bucuk":
            if last_scale: total += last_scale / 2
            else: cur += 0.5
        elif t in ("virgul", "nokta"): total += cur; cur = 0; frac = ""
        elif t in ("lira", "tl"): total += cur; cur = 0; kurus = 0
        elif t == "kurus": kurus = cur; cur = 0
        elif frac is not None and t == "#": break
    if not seen: return None
    if frac is not None: return round(total + float("0." + str(int(cur))) if cur else total, 2)
    if kurus is not None: return round(total + (kurus or 0) / 100 + cur / 100, 2)
    return round(total + cur, 2)
```

TCKN kontrolü (stdlib):
```python
def tckn_ok(s):
    d = [int(c) for c in re.sub(r"\D", "", s)]
    return (len(d) == 11 and d[0] != 0 and d[9] == ((sum(d[0:9:2]) * 7) - sum(d[1:8:2])) % 10
            and d[10] == sum(d[:10]) % 10)
```

**Öneri sırası (hackathon):** (1) tarih çözücü + brief tatil tablosu + "önümüzdeki/haftaya" ayrımı, (2) tutar parser + ±teyit (read-back her zaman kodda üretilen kelime formuyla), (3) telefon/DOB kanonikleştirme, (4) taahhüt-olmayan söz listesi ("bakarız/inşallah tek başına"), (5) MASSIVE tr ile regression.

## Kaynaklar (ek)
- Duckling repo: https://github.com/facebook/duckling (TR: `Duckling/Time/TR/Rules.hs`, `Duckling/Numeral/TR/Rules.hs`, `Duckling/Dimensions/TR.hs`)
- TR saat gösterimi: https://en.wikipedia.org/wiki/Date_and_time_notation_in_Turkey
- 2027 bayramlar: https://www.dunya.com/gundem/2027-bayram-tarihleri-ramazan-bayrami-ve-kurban-bayrami-ne-zaman-kutlanacak-haberi-840413 ; Kurban (EN): https://turkeytravelplanner.com/religion/kurban_bayrami_dates.html
- VYŞ yönetmeliği haberleri: https://www.timeturk.com/ekonomi/varlik-yonetim-sirketlerine-iliskin-yonetmelik-yayimlandi/haber-1693392 ; 2025 değişiklik: https://www.alomaliye.com/2025/08/27/varlik-yonetim-sirketlerinin-kurulus-ve-faaliyet-esaslari-ile-devralinacak-alacaklar-27-08-2025/
- KVKK 2021/1107 (ilgili karar özeti): https://www.kvkk.gov.tr/Icerik/7264/2021-1107
- ITN literatürü (veri artırma fikri): https://arxiv.org/pdf/2207.09674 ; Thutmose tagger: https://arxiv.org/pdf/2208.00064
- Türkçe metin normalizasyonu (sosyal medya, MT yaklaşımı, kod: talha252/tur-text-norm): https://paperswithcode.com/paper/normalizing-non-canonical-turkish-texts-using

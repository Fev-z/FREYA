# Deterministic layer: production agent stack'lerinden Freya'ya uygulanabilir pattern'ler

## 1) Prensip (tek satır)
LLM yalnızca **anlar ve konuşur**; karar, hesap, doğrulama ve yönlendirme **kodda** (code node / pre-post hook / variable routing) yapılır, LLM'e sadece hazır sonuç ve tek bir "sıradaki adım" cümlesi verilir.

## 2) Pattern'ler

**P1. LLM komut/slot üretir, akış kodla ilerler** (Rasa CALM: LLM command generator + flows)
- Ne yapar: LLM sadece `SetSlot(x)` / `StartFlow(y)` gibi komut çıkarır; dallanma flow'daki `next: if slots.age < 18 then ...` koşullarıyla deterministik.
- Freya: Node prompt'u "şunu konuş + şu değişkeni çıkar" ile sınırlı. Transition'lar LLM kararına değil `vars` üzerine kurulu koşullara bağlı (ör. `identity_ok == "true"`, `ptp_status == "valid"`). Her karar noktasının önüne bir **code node** koy; kararı o yazsın, transition sadece string karşılaştırsın.

**P2. Slot-level validation + rejection mesajı** (Rasa CALM `collect` + `rejections: - if: ... utter: ...`, domain-level slot validation)
- Ne yapar: Slot dolar dolmaz koşul kontrol edilir; geçersizse slot reddedilir ve sabit bir "neden reddedildi" cümlesi söylenir, aynı soru tekrar sorulur.
- Freya: Extraction schema'sı dar tutulur (enum, regex, ISO tarih). Extraction sonrası code node: `amount_valid`, `date_valid`, `reject_reason` yazar. Transition: `amount_valid == "false"` -> aynı collect node'a geri dön, prompt `reject_reason`'ı aynen okusun. Retry sayacı (`amount_retry`) code node'da artar; N'de escalation/outcome node.

**P3. Tool gating: kimlik doğrulanmadan hassas tool/bilgi yok** (Sierra "deterministic guards"; Parlant: tool'lar yalnız ilgili guideline tetiklenince context'e girer)
- Ne yapar: Hesap değiştiren/borç bilgisi veren tool'lar auth tamamlanmadan modele hiç sunulmaz; kural prompt'ta değil mimaride.
- Freya: Borç tutarı/ödeme tool'ları yalnız `identity_ok == "true"` sonrası node'larda tanımlı. Ek savunma: tool'un **pre_process_code**'u `vars["identity_ok"] != "true"` ise isteği iptal eder / boş döner ve `what_to_do_next = "Önce kimlik doğrulamasını tamamla; borç detayı verme."` yazar.

**P4. Execution rails: tool girdi/çıktısını kodla doğrula** (NeMo Guardrails execution rails = tool input/output validation; output rails)
- Ne yapar: LLM'in tool'a verdiği argümanlar ve tool'dan dönen sonuç modelden bağımsız kontrol edilir.
- Freya: **pre_process_code** = argüman normalizasyonu + kural kontrolü (tutar >= floor, tarih <= deadline, iş günü mü). **post_process_code** = sonucu sadeleştirip tek alanlı karar + `what_to_do_next` cümlesi ("Söz kaydedildi. Müşteriye tarih ve tutarı bir kez teyit et, sonra kapanışa geç."). Ham API JSON'u modele gitmesin.

**P5. Compute in code, let the LLM talk** (tau-bench: başarı = doğru son DB state + policy-uyumlu trajectory, binary skor; Sierra Agent SDK'nın deklaratif davranış + supervisor yaklaşımı)
- Ne yapar: İş günü sayımı, tatil takvimi, son ödeme tarihi, minimum tutar, kalan borç gibi tüm aritmetik kodda; LLM sadece sonucu söyler.
- Freya: Konuşma başında bir **code node**: `datetime` ile `today`, holiday listesi (sabit JSON), `deadline = add_business_days(today, N)`, `min_amount = max(floor, pct*debt)` hesaplanır ve **söylenecek string** olarak (`deadline_spoken = "15 Ekim Çarşamba"`) `vars`'a yazılır. LLM tarih/tutar türetmez, okur.

**P6. Duckling tarzı normalizasyon** (Duckling: "yarın", "ayın 15'i", "bin beş yüz" -> ISO date / number, reference time + locale ile)
- Ne yapar: Serbest konuşma ifadesini kural tabanlı parser deterministik değere çevirir; relative tarih referans tarihe göre çözülür.
- Freya: Extraction schema'sında hem `raw_text` hem `iso_date`/`amount_number` iste; ardından code node'da `re` + `datetime` ile mini-Duckling: Türkçe sayı kelimeleri, "yarın/öbür gün/haftaya cuma/ayın X'i", hafta sonu/tatile düşerse kural (reddet veya sonraki iş günü). LLM'in doldurduğu ISO değer ile code parse uyuşmazsa code'unki kazanır veya teyit sorusu tetiklenir.

**P7. Canned / templated kritik cümleler** (Parlant canned responses, strict mode: gerekli alanlar context'te yoksa cevap seçilemez; Rasa `utter_*`)
- Ne yapar: Yasal uyarı, kimlik sorusu, söz teyidi, kapanış gibi yüksek riskli cümleler sabit şablon; serbest üretim yok.
- Freya: Code node şablonu doldurur (`confirm_text = f"{amount_spoken} TL, {deadline_spoken} tarihine kadar..."`), node prompt'u "aşağıdaki cümleyi aynen söyle: {{confirm_text}}" der. Zayıf dialogue model için en güvenli yol.

**P8. Outcome code'u kod belirler, LLM değil** (tau-bench: başarı = son DB state + policy-uyumlu trajectory; Rasa flows'ta `set_slots`)
- Ne yapar: Sonuç durumu kayıtlı state'ten türetilir; konuşma özetinden değil.
- Freya: Terminal öncesi tek bir **code node**: `vars` üzerinden karar tablosu (`identity_ok`, `ptp_recorded`, `refused`, `wrong_person`, `callback_requested`) -> `outcome_code`. Promise-to-pay yalnız tool post_process başarı döndüyse `ptp_recorded = "true"`.

## 3) Anti-pattern'ler
- Policy'yi sadece prompt'a yazmak ("kimlik doğrulanmadan borç söyleme") — Sierra: ısrarcı kullanıcı prompt-level kuralı kırar; guard kodda olmalı.
- LLM'e tarih/iş günü/tutar hesaplatmak veya transition kararını LLM'in serbest metnine bırakmak.
- Ham tool JSON'unu modele vermek; `what_to_do_next` olmadan model sıradaki adımı tahmin eder.
- Geniş extraction schema'sı (serbest string) — enum/regex/ISO yerine; doğrulamasız slot'u routing'de kullanmak.
- Retry limiti olmayan validation döngüsü (sonsuz tekrar soru).
- Outcome code'u konuşma sonunda LLM'e "özetle ve kodla" dedirtmek.
- Tek katmana güvenmek: gating (P3) + hook validation (P4) + routing (P1) birlikte, defense in depth.

## Kaynaklar
- Rasa CALM flows / business logic: https://rasa.com/docs/reference/primitives/flows , https://rasa.com/docs/rasa-pro/concepts/flows
- Rasa slots / validation: https://rasa.com/docs/reference/primitives/slots.md , https://rasa.com/docs/reference/integrations/action-server/validation-action/
- Parlant guidelines / journeys / canned responses: https://parlant.io/docs/concepts/customization/guidelines , https://parlant.io/docs/concepts/entities/agents
- NVIDIA NeMo Guardrails (input/output/execution rails, Colang): https://github.com/NVIDIA/NeMo-Guardrails , https://docs.nvidia.com/nemo/guardrails/
- Sierra deterministic guards: https://sierra.ai/blog/defense-in-depth-in-the-age-of-agents ; Agent SDK + tau-bench: https://sierra.ai/blog/benchmarking-ai-agents , https://github.com/sierra-research/tau-bench
- Duckling: https://github.com/facebook/duckling ; Rasa Duckling notları: https://forum.rasa.com/t/duckling-failed-to-extract-date-and-number/55118

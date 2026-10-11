# Final runbook (Pazar 20:00–23:00 İstanbul)

Kural: final belgelerinden **hiçbir şey** builder'a (builder/, .claude/skills/) yazılmaz. Mock'a yazılır, çünkü mock builder değildir.
Builder'da yalnızca çökme gibi bug düzeltilir.

## 0. Hazırlık (19:45'e kadar)
- [ ] `source env.sh` çalışıyor, `.venv` var
- [x] `npx wrangler whoami` giriş yapılmış gösteriyor, subdomain `egemenayrac` kayıtlı, mock yayında
- [ ] GitHub repo push edilmiş, son commit temiz
- [ ] Final belgeleri repo DIŞINA açılacak: `~/Downloads/final-case/`

## 1. 20:00 — Zip'i indir ve oku (15 dk)
```bash
mkdir -p ~/Downloads/final-case && cd ~/Downloads/final-case && unzip ~/Downloads/<zip>.zip
```
- BRIEF.md → README.md → servis sözleşmesi → test müşterileri → duyurular → Q&A → 6 örnek konuşma
- Not al: servis sözleşmesindeki **yollar, alanlar, enum değerleri, hata biçimi**

## 2. 20:15 — Mock'u final sözleşmesine uyarla (45 dk, en riskli adım)
`mock/src/index.js` içinde:
- [ ] `TOOLS` içindeki her araç: sözleşmedeki ad, yol, alanlar, cevap biçimi
- [ ] `verify_identity`: sözleşmedeki kimlik alanları (kod `case.identity` anahtarlarını zaten genel okuyor)
- [ ] Hata biçimi: sözleşme ne diyorsa (500 mü, `ok:false` mı)
- [ ] `mock/cases.json`: test müşterilerini kit formatına çevir (`id, variables, identity, products, script, expected, checks`, `"language": "tr"`)
- [ ] Practice yolları (`/v1/practice/...`) kalsın: builder testleri bunlarla koşar
- [ ] Takım key kontrolü Worker girişinde (`export default fetch`) kalsın, Durable Object içine taşıma (orada secret görünmüyor)

Deploy:
```bash
cd mock
npx wrangler deploy
source ../env.sh && printf '%s' "$FREYA_BANK_TEAM_KEY" | npx wrangler secret put TEAM_KEY
curl -s https://freya-bank-mock-team.egemenayrac.workers.dev/health
```
Duman testi: `python3 mock/smoke.py https://freya-bank-mock-team.egemenayrac.workers.dev <case_id> ...` → sonda `mock OK`

## 3. 21:00 — Builder'ı çalıştır (≤ 30 dk)
```bash
cd ~/Downloads/build-the-builder && source env.sh
.venv/bin/python builder/build.py ~/Downloads/final-case/<klasör> https://freya-bank-mock-team.egemenayrac.workers.dev/v1 --slot final 2>&1 | tee traces/final.log
```
- Sonda `CHECK all tool URLs point at the mock` yazmalı
- Çıktı: `submission/final.workflow.json`, `traces/<zaman>-final.log`
- Çökerse: **sadece bug** düzelt, commit et, yeniden çalıştır (aynı `--slot final` aynı workflow'u günceller)

## 4. 21:30 — Kontrol (15 dk)
- [ ] Freya'da chat ile bir tur: açılış Türkçe mi, ilk soru doğru mu
- [ ] Bir konuşma dökümünü oku
- [ ] Gerekirse 2. çalıştırma (vakit varsa). Hangi çalıştırma gönderilecekse onun trace'i

## 5. 22:00 — Gönder (≤ 22:30 bitir)
```bash
source env.sh; grep -c -F "$FREYA_API_KEY" traces/* submission/*   # hepsi 0 olmalı
git add builder mock submission traces FINAL_RUNBOOK.md && git commit -m "Final run" && git push
```
`submission.json`:
```json
{
  "team": "<takım adı>",
  "members": [{"name": "Egemen ...", "email": "..."}, {"name": "...", "email": "..."}],
  "repo": "https://github.com/<you>/<repo>",
  "commit": "<git rev-parse --short HEAD>",
  "run_command": "python3 builder/build.py {case_folder} {mock_url} --slot final",
  "workflow": "submission/final.workflow.json",
  "trace": "traces/<zaman>-final.log",
  "mock_url": "https://freya-bank-mock-team.egemenayrac.workers.dev"
}
```
- [ ] Mail ile gönder (kit mail'indeki adres), 23:00'den önce
- [ ] **Mock sonuçlar açıklanana kadar ayakta kalsın.** Kapatma, yeniden deploy ederken dikkat.

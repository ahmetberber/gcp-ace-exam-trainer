# GCP ACE Exam Trainer

Google Cloud **Associate Cloud Engineer (ACE)** sertifika sınavına hazırlık için masaüstü pratik uygulaması.
Hazır Türkçe soru bankası, gerçek sınavı taklit eden süreli mod, ilerleme takibi ve Claude ile
**güncel Google Cloud dokümantasyonunu tarayarak yeni soru üretme** özelliği içerir.

> *English summary: a Tkinter desktop quiz app for the Google Cloud Associate Cloud Engineer exam, with a built-in
> Turkish question bank, timed exam simulation, progress tracking, and optional AI-generated up-to-date questions
> (Claude + web search on cloud.google.com).*

## Özellikler

- **88 hazır ACE sorusu**: resmi sınav rehberinin 4 alanına ve 13 konu başlığına göre etiketli
  (IAM, Compute Engine, GKE, Cloud Run, VPC, Cloud Storage, veritabanları, Logging/Monitoring…).
  Sorular güncel ürün adlarına göre yazıldı (Artifact Registry, Cloud Run functions, Infrastructure Manager,
  Workload Identity Federation vb.).
- **Pratik modu**: her sorudan sonra anında doğru/yanlış ve açıklama.
- **Sınav simülasyonu**: gerçek sınav gibi süreli (50 soru / 120 dk), sorular alan ağırlıklarına göre dağıtılır,
  işaretleme (⚑) ve soru listesi ile gezinme.
- **Akıllı tekrar**: daha önce yanlış yaptığınız veya hiç görmediğiniz sorulara öncelik; "yalnızca yanlışlarım" modu.
- **İlerleme**: alan bazında başarı oranı ve oturum geçmişi.
- **✨ AI ile güncel soru üretme** (isteğe bağlı): Claude, cloud.google.com'da web araması yaparak bilgileri doğrular
  ve seçtiğiniz alan/konu/zorlukta yeni sorular üretir. Kaydetmeden önce önizleyebilirsiniz.
- **🤖 Claude'a sor**: anlamadığınız bir soruyu ayrıntılı açıklatın, ek sorular sorun.
- **JSON içe/dışa aktarma**: kendi sorularınızı ekleyin.
- Diğer GCP sınavları (CDL, PCA, PDE, PCD, PCSE, PCNE, PMLE) da listede; bunlar için soruları AI ile üretebilirsiniz.

## Kurulum

Gereksinim: **Python 3.10+** (python.org kurulumu Tkinter'ı içerir).

**Windows:** `start-windows.bat` dosyasına çift tıklayın. İlk açılışta sanal ortam kurulur.

**macOS / Linux:**

```bash
./start.sh
```

Elle çalıştırmak için:

```bash
pip install -r requirements.txt
```

```bash
python main.py
```

> Hazır sorularla çalışmak için ek paket gerekmez; `anthropic` paketi yalnızca AI özellikleri içindir.
> Linux'ta Tkinter yoksa: `sudo apt install python3-tk`

## AI özelliklerini açma

1. [console.anthropic.com](https://console.anthropic.com) üzerinden bir API anahtarı alın.
2. Uygulamada **Ayarlar → API anahtarı** alanına girin (veya `ANTHROPIC_API_KEY` ortam değişkenini tanımlayın).
3. Model (Opus 5.5 / Sonnet 5.5 / Haiku 5.5), efor seviyesi, web araması ve soru dili (Türkçe/İngilizce) ayarlanabilir.

API kullanımı ücretlidir; web araması açıkken her üretim birkaç arama içerir. Anahtar yalnızca bu bilgisayarda
`data/settings.json` içinde düz metin olarak tutulur ve `.gitignore` ile depoya girmez.

## Klavye kısayolları

| Tuş | İşlev |
|---|---|
| `1`–`5` | Seçenek seç / işaretle |
| `Enter` | Kontrol et / sonraki soru |
| `←` `→` | Önceki / sonraki soru |

## Kendi sorularınızı eklemek (JSON)

```json
[
  {
    "exam": "ACE",
    "domain": 2,
    "topic": "Cloud Storage",
    "difficulty": "orta",
    "question": "Soru metni…",
    "options": ["A seçeneği", "B seçeneği", "C seçeneği", "D seçeneği"],
    "correct": [0],
    "explanation": "Neden A doğru…",
    "source_url": "https://cloud.google.com/…"
  }
]
```

`correct` 0 tabanlı indeks listesidir; birden fazla doğru cevap için `[0, 2]` gibi yazın.
Seçenekler her oturumda karıştırılır.

## Proje yapısı

```
main.py                 Başlatıcı
examtrainer/exams.py    Sınav tanımları, alanlar ve ağırlıklar
examtrainer/store.py    Soru bankası, istatistik ve ayar dosyaları
examtrainer/engine.py   Soru seçimi, karıştırma, puanlama
examtrainer/ai.py       Claude API ile soru üretme ve açıklama
examtrainer/gui.py      Tkinter arayüzü
questions/ace.json      Hazır ACE soru bankası
tests/                  Birim testleri (python -m unittest discover -s tests)
data/                   Kişisel veriler (otomatik oluşur, git'e girmez)
```

## Notlar

- Alan adları ve ağırlıkları resmi rehbere göre yaklaşıktır; Google sınavı zaman zaman günceller.
  Güncel rehber: <https://cloud.google.com/learn/certification/cloud-engineer>
- Google geçme notunu açıklamaz; uygulama %70'i hedef olarak kullanır.
- Bu proje Google ile bağlantılı değildir; sorular özgün pratik sorularıdır, gerçek sınav soruları değildir.

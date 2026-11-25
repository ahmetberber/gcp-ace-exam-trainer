# GCP ACE Exam Trainer

Google Cloud **Associate Cloud Engineer (ACE)** sertifika sınavına hazırlık için masaüstü pratik uygulaması.
Hazır Türkçe soru bankası, gerçek sınavı taklit eden süreli mod ve ilerleme takibi içerir.
**Tamamen çevrimdışı çalışır**: internet erişimi, hesap veya ek paket gerekmez.

> *English summary: an offline Tkinter desktop quiz app for the Google Cloud Associate Cloud Engineer exam, with a
> built-in Turkish question bank, timed exam simulation and progress tracking. No dependencies beyond Python.*

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
- **JSON içe/dışa aktarma**: kendi sorularınızı ekleyin.

## Kurulum

Tek gereksinim **Python 3.10+**. [python.org](https://www.python.org/downloads/) kurulumu Tkinter'ı içerir;
kurulumda **"Add python.exe to PATH"** seçeneğini işaretleyin.

**Windows:** `start-windows.bat` dosyasına çift tıklayın. Başka kurulum adımı yoktur.

**macOS / Linux:**

```bash
./start.sh
```

veya doğrudan `python3 main.py`. Linux'ta Tkinter yoksa: `sudo apt install python3-tk`

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
examtrainer/gui.py      Tkinter arayüzü
questions/ace.json      Hazır ACE soru bankası
tests/                  Birim testleri (python -m unittest discover -s tests)
data/                   İlerleme verileri (otomatik oluşur, git'e girmez)
```

## Notlar

- Alan adları ve ağırlıkları resmi rehbere göre yaklaşıktır; Google sınavı zaman zaman günceller.
  Güncel rehber: <https://cloud.google.com/learn/certification/cloud-engineer>
- Google geçme notunu açıklamaz; uygulama %70'i hedef olarak kullanır.
- Bu proje Google ile bağlantılı değildir; sorular özgün pratik sorularıdır, gerçek sınav soruları değildir.

"""Sınav tanımları.

Alan (domain) adları ve ağırlıkları Google'ın resmi sınav rehberlerine göre
yaklaşıktır; Google bunları zaman zaman günceller. Sınava girmeden önce
https://cloud.google.com/learn/certification adresindeki güncel rehberi kontrol edin.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Exam:
    code: str
    name: str
    level: str
    minutes: int
    question_count: int
    domains: dict = field(default_factory=dict)  # {1: ("Ad", ağırlık_yüzde)}
    bank_file: str | None = None
    topics: tuple = ()

    def domain_name(self, idx: int) -> str:
        d = self.domains.get(idx)
        return d[0] if d else f"Alan {idx}"


# ACE kurslarındaki bölüm yapısına benzer konu başlıkları. Alan ağırlıkları resmi rehbere göredir:
# https://services.google.com/fh/files/misc/associate_cloud_engineer_exam_guide_english.pdf
ACE_TOPICS = (
    "Kaynak hiyerarşisi ve faturalandırma",
    "gcloud ve Cloud Shell",
    "IAM ve servis hesapları",
    "Compute Engine",
    "Instance group ve yük dengeleme",
    "GKE (Kubernetes)",
    "Serverless (Cloud Run, Functions, App Engine)",
    "Cloud Storage",
    "Veritabanları",
    "VPC ve ağ",
    "Logging ve Monitoring",
    "Veri ve analitik",
    "IaC ve DevOps",
    "Gemini ve yapay zekâ araçları",
)

EXAMS: dict[str, Exam] = {
    "ACE": Exam(
        "ACE", "Associate Cloud Engineer", "Associate", 120, 50,
        {
            1: ("Bulut çözüm ortamını kurma", 20),
            2: ("Bulut çözümünü planlama ve uygulama", 30),
            3: ("Çözümün başarılı çalışmasını sağlama", 30),
            4: ("Erişim ve güvenliği yapılandırma", 20),
        },
        "ace.json",
        ACE_TOPICS,
    ),
}

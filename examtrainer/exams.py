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


# ACE kurslarındaki (ör. Udemy ACE eğitimleri) bölüm yapısına benzer konu başlıkları.
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
)

EXAMS: dict[str, Exam] = {
    "CDL": Exam(
        "CDL", "Cloud Digital Leader", "Temel", 90, 50,
        {
            1: ("Google Cloud ile dijital dönüşüm", 17),
            2: ("Google Cloud ile veri dönüşümü", 16),
            3: ("Google Cloud yapay zekâsı ile inovasyon", 16),
            4: ("Altyapı ve uygulamaların modernizasyonu", 17),
            5: ("Güven ve güvenlik", 17),
            6: ("Google Cloud operasyonlarıyla ölçeklenme", 17),
        },
        None,
    ),
    "ACE": Exam(
        "ACE", "Associate Cloud Engineer", "Associate", 120, 50,
        {
            1: ("Bulut çözüm ortamını kurma", 23),
            2: ("Bulut çözümünü planlama ve uygulama", 30),
            3: ("Çözümün başarılı çalışmasını sağlama", 27),
            4: ("Erişim ve güvenliği yapılandırma", 20),
        },
        "ace.json",
        ACE_TOPICS,
    ),
    "PCA": Exam(
        "PCA", "Professional Cloud Architect", "Professional", 120, 50,
        {
            1: ("Bulut çözüm mimarisi tasarlama ve planlama", 25),
            2: ("Altyapıyı yönetme ve sağlama", 17.5),
            3: ("Güvenlik ve uyumluluk için tasarım", 17.5),
            4: ("Teknik ve iş süreçlerini analiz/optimize etme", 15),
            5: ("Uygulamayı (implementation) yönetme", 12.5),
            6: ("Çözüm ve operasyon güvenilirliği", 12.5),
        },
        None,
    ),
    "PDE": Exam(
        "PDE", "Professional Data Engineer", "Professional", 120, 50,
        {
            1: ("Veri işleme sistemleri tasarlama", 22),
            2: ("Veri alımı (ingestion) ve işleme", 25),
            3: ("Veriyi depolama", 20),
            4: ("Veriyi analiz için hazırlama ve kullanma", 15),
            5: ("Veri iş yüklerini sürdürme ve otomatikleştirme", 18),
        },
        None,
    ),
    "PCD": Exam(
        "PCD", "Professional Cloud Developer", "Professional", 120, 50,
        {
            1: ("Ölçeklenebilir, erişilebilir, güvenilir cloud-native uygulama tasarımı", 36),
            2: ("Uygulama geliştirme ve test", 23),
            3: ("Uygulama dağıtımı", 20),
            4: ("Uygulamaları Google Cloud hizmetleriyle entegre etme", 21),
        },
    ),
    "PCSE": Exam(
        "PCSE", "Professional Cloud Security Engineer", "Professional", 120, 50,
        {
            1: ("Erişimi yapılandırma", 25),
            2: ("İletişimi güvenli hale getirme ve sınır koruması", 22),
            3: ("Veri korumasını sağlama", 23),
            4: ("Operasyonları yönetme", 19),
            5: ("Uyumluluk gereksinimlerini destekleme", 11),
        },
    ),
    "PCNE": Exam(
        "PCNE", "Professional Cloud Network Engineer", "Professional", 120, 50,
        {
            1: ("Ağ tasarımı, planlama ve prototipleme", 26),
            2: ("VPC ağlarını uygulama", 21),
            3: ("Yönetilen ağ hizmetlerini yapılandırma", 21),
            4: ("Hibrit bağlantıyı uygulama", 18),
            5: ("Ağ operasyonlarını yönetme, izleme ve optimize etme", 14),
        },
    ),
    "PMLE": Exam(
        "PMLE", "Professional Machine Learning Engineer", "Professional", 120, 50,
        {
            1: ("Düşük kodlu yapay zekâ çözümleri tasarlama", 13),
            2: ("Veri ve modelleri ekipler arasında yönetme", 14),
            3: ("Prototipleri ML modellerine ölçeklendirme", 18),
            4: ("Modelleri sunma ve ölçeklendirme", 20),
            5: ("ML pipeline'larını otomatikleştirme ve orkestrasyon", 22),
            6: ("Yapay zekâ çözümlerini izleme", 13),
        },
    ),
}

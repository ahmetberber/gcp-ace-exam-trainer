"""Claude API ile güncel sınav sorusu üretme ve soru açıklama.

Gereksinim: pip install anthropic
API anahtarı: ANTHROPIC_API_KEY ortam değişkeni veya uygulamadaki Ayarlar penceresi.
"""
from __future__ import annotations

import datetime as dt
import json

from .exams import EXAMS
from .store import ValidationError, validate_question

MODELS = {
    "claude-opus-5-5": "Claude Opus 5.5 (en iyi kalite)",
    "claude-sonnet-5-5": "Claude Sonnet 5.5 (hızlı, daha ucuz)",
    "claude-haiku-5-5": "Claude Haiku 5.5 (en ucuz)",
}
EFFORTS = ("low", "medium", "high")

# Reddedilen (refusal) isteklerde sunucu tarafında yedek modele geçiş.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SUBMIT_TOOL = {
    "name": "submit_questions",
    "description": "Hazırlanan sınav sorularını uygulamaya teslim eder. Tüm sorular hazır olduğunda TEK SEFER çağır.",
    "strict": True,
    "eager_input_streaming": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["questions"],
        "properties": {
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["question", "options", "correct", "explanation",
                                 "domain", "topic", "difficulty", "source_url"],
                    "properties": {
                        "question": {"type": "string", "description": "Senaryo tabanlı soru metni"},
                        "options": {"type": "array", "items": {"type": "string"},
                                    "description": "4 seçenek (çoklu seçimde 5)"},
                        "correct": {"type": "array", "items": {"type": "integer"},
                                    "description": "Doğru seçeneklerin 0 tabanlı indeksleri"},
                        "explanation": {"type": "string",
                                        "description": "Doğru cevabın neden doğru, diğerlerinin neden yanlış olduğu"},
                        "domain": {"type": "integer", "description": "Sınav alanı numarası"},
                        "topic": {"type": "string", "description": "Konu başlığı"},
                        "difficulty": {"type": "string", "enum": ["kolay", "orta", "zor"]},
                        "source_url": {"type": "string",
                                       "description": "Doğrulamada kullanılan resmi doküman URL'si (yoksa boş)"},
                    },
                },
            }
        },
    },
}


class AIError(RuntimeError):
    pass


def _client(settings):
    try:
        import anthropic
    except ImportError as e:  # pragma: no cover
        raise AIError("'anthropic' paketi kurulu değil. Komut: pip install anthropic") from e
    key = (settings["api_key"] or "").strip() or None
    try:
        return anthropic, anthropic.Anthropic(api_key=key, max_retries=3)
    except anthropic.AnthropicError as e:
        raise AIError("API anahtarı bulunamadı. Ayarlar'dan anahtar girin veya "
                      "ANTHROPIC_API_KEY ortam değişkenini tanımlayın.") from e


def _api_error_message(anthropic, e: Exception) -> str:
    if isinstance(e, anthropic.AuthenticationError):
        return "API anahtarı geçersiz (401). Ayarlar'dan kontrol edin."
    if isinstance(e, anthropic.PermissionDeniedError):
        return "Bu anahtarın seçilen model/özellik için izni yok (403)."
    if isinstance(e, anthropic.NotFoundError):
        return "Model bulunamadı (404). Ayarlar'dan başka bir model seçin."
    if isinstance(e, anthropic.RateLimitError):
        return "Hız limiti aşıldı (429). Biraz bekleyip tekrar deneyin."
    if isinstance(e, anthropic.BadRequestError):
        return f"İstek reddedildi (400): {e.message}"
    if isinstance(e, anthropic.APIStatusError):
        return f"API hatası ({e.status_code}): {e.message}"
    if isinstance(e, anthropic.APIConnectionError):
        return "Bağlantı hatası. İnternet bağlantınızı kontrol edin."
    return str(e)


def _system_prompt(exam_code: str, language: str) -> str:
    exam = EXAMS[exam_code]
    domains = "\n".join(f"  {k}. {v[0]} (~%{v[1]})" for k, v in exam.domains.items())
    topics = ("\nKonu başlıkları (topic alanında bunlardan birini aynen kullan):\n"
              + "\n".join(f"  - {t}" for t in exam.topics)) if exam.topics else ""
    lang = ("Soruları, seçenekleri ve açıklamaları TÜRKÇE yaz; Google Cloud ürün/özellik adlarını "
            "ve gcloud/kubectl komutlarını orijinal İngilizce halleriyle bırak."
            if language == "tr" else
            "Write questions, options and explanations in ENGLISH, matching the style of the real exam.")
    return f"""Sen Google Cloud sertifika sınavları için soru yazan uzman bir eğitmensin.
Hedef sınav: Google Cloud {exam.name} ({exam.code}).
Bugünün tarihi: {dt.date.today().isoformat()}.

Sınav alanları (domain alanına numarayı yaz):
{domains}{topics}

Kurallar:
- Sorular GÜNCEL olmalı. Ürün adları, özellikler, varsayılanlar ve kullanımdan kaldırılan (deprecated)
  hizmetler konusunda emin olmadığın her şeyi web aramasıyla resmi Google Cloud dokümantasyonundan
  (cloud.google.com) doğrula. Kullanımdan kaldırılmış bir hizmeti (ör. Container Registry,
  Deployment Manager) doğru cevap yapma; ancak geçiş senaryosu soruları sorabilirsin.
- Gerçek sınav gibi kısa senaryo tabanlı sorular yaz: bir şirket/ekip ihtiyacı ve kısıtları
  (maliyet, en az yönetim yükü, güvenlik, erişilebilirlik) verilsin, en uygun çözüm sorulsun.
- Tek doğru cevaplı sorularda tam 4 seçenek; çoklu seçimli sorularda ("İKİ seçenek seçin") 5 seçenek
  ve 2 doğru cevap. Soruların yaklaşık %15'i çoklu seçimli olabilir.
- Çeldiriciler makul olmalı (gerçek ürünler, yaygın yanlış anlamalar); "hepsi"/"hiçbiri" kullanma.
- Doğru cevabın konumunu çeşitlendir.
- Açıklamada doğru cevabın neden doğru olduğunu ve her çeldiricinin neden yanlış olduğunu 2-5 cümlede anlat.
- source_url alanına doğrulamada kullandığın resmi doküman adresini yaz (yoksa boş bırak).
- {lang}
- Bitirince soruların hepsini submit_questions aracını TEK SEFER çağırarak teslim et."""


def generate_questions(settings, exam_code: str, count: int = 10, domain: int | None = None,
                       topic: str | None = None, difficulty: str | None = None,
                       existing: list[dict] | None = None, progress=lambda msg: None) -> list[dict]:
    """Claude ile yeni sorular üretir; doğrulanmış soru sözlükleri döndürür (henüz kaydetmez)."""
    anthropic, client = _client(settings)
    exam = EXAMS[exam_code]

    focus = []
    if domain:
        focus.append(f"Tüm sorular {domain}. alandan olsun: {exam.domain_name(domain)}.")
    else:
        focus.append("Soruları alan ağırlıklarına yakın şekilde alanlara dağıt.")
    if topic:
        focus.append(f"Tüm sorular şu konu başlığına odaklansın: {topic}.")
    if difficulty:
        focus.append(f"Zorluk seviyesi: {difficulty}.")
    avoid = ""
    if existing:
        stems = [q["question"][:110] for q in existing[-80:]]
        avoid = ("\n\nBankada zaten bulunan sorulardan bazıları (bunları tekrar etme, farklı "
                 "senaryolar ve hizmetler seç):\n" + "\n".join(f"- {s}" for s in stems))
    user_msg = (f"{count} adet yeni {exam.code} pratik sorusu hazırla. " + " ".join(focus) + avoid)

    tools = [SUBMIT_TOOL]
    if settings["web_search"]:
        tools.insert(0, {"type": "web_search_20260209", "name": "web_search", "max_uses": 8,
                         "allowed_domains": ["cloud.google.com"]})

    messages = [{"role": "user", "content": user_msg}]
    for _round in range(6):
        progress("Claude soruları hazırlıyor…")
        try:
            with client.beta.messages.stream(
                model=settings["model"],
                max_tokens=64000,
                betas=[FALLBACK_BETA],
                fallbacks="default",
                output_config={"effort": settings["effort"]},
                system=_system_prompt(exam_code, settings["language"]),
                tools=tools,
                messages=messages,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        btype = getattr(event.content_block, "type", "")
                        if btype == "server_tool_use":
                            progress("Google Cloud dokümantasyonunda arıyor…")
                        elif btype == "tool_use":
                            progress("Sorular yazılıyor…")
                msg = stream.get_final_message()
        except anthropic.APIError as e:
            raise AIError(_api_error_message(anthropic, e)) from e

        if msg.stop_reason == "refusal":
            raise AIError("Model isteği yanıtlamayı reddetti. Konuyu değiştirip tekrar deneyin.")
        if msg.stop_reason == "max_tokens":
            raise AIError("Yanıt uzunluk sınırına takıldı. Daha az soru isteyin.")

        submit = next((b for b in msg.content
                       if b.type == "tool_use" and b.name == "submit_questions"), None)
        if submit is not None:
            return _validate_batch(submit.input, exam_code)

        messages.append({"role": "assistant", "content": msg.content})
        if msg.stop_reason != "pause_turn":
            # Model aracı çağırmadan bitirdiyse nazikçe hatırlat.
            messages.append({"role": "user",
                             "content": "Lütfen soruları şimdi submit_questions aracıyla teslim et."})
    raise AIError("Model soruları teslim etmedi. Tekrar deneyin.")


def _validate_batch(tool_input, exam_code: str) -> list[dict]:
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except json.JSONDecodeError as e:
            raise AIError("Modelden gelen yanıt çözümlenemedi.") from e
    raw = tool_input.get("questions") if isinstance(tool_input, dict) else None
    if not isinstance(raw, list):
        raise AIError("Modelden gelen yanıtta soru listesi yok.")
    out = []
    today = dt.date.today().isoformat()
    for q in raw:
        if not isinstance(q, dict):
            continue
        q = {**q, "exam": exam_code, "source": "ai", "created": today}
        try:
            out.append(validate_question(q, exam_code))
        except ValidationError:
            continue
    if not out:
        raise AIError("Üretilen sorular doğrulamadan geçemedi.")
    return out


def explain(settings, q: dict, chosen_texts: list[str], follow_up: str = "") -> str:
    """Bir soruyu daha ayrıntılı açıklatır (Claude'a sor)."""
    anthropic, client = _client(settings)
    correct = [q["options"][i] for i in q["correct"]]
    prompt = (f"Google Cloud {EXAMS[q['exam']].name} sınavına hazırlanıyorum.\n\n"
              f"Soru: {q['question']}\n\nSeçenekler:\n"
              + "\n".join(f"- {o}" for o in q["options"])
              + f"\n\nDoğru cevap: {'; '.join(correct)}\n"
              f"Benim cevabım: {'; '.join(chosen_texts) or '(boş)'}\n\n"
              + (follow_up.strip() or
                 "Bu konuyu sınav açısından açıkla: doğru cevap neden doğru, benim seçimim neden "
                 "yanlış/doğru, bu konuda sınavda dikkat etmem gereken tuzaklar neler? "
                 "Kısa ve maddeli yaz."))
    lang = "Türkçe yanıt ver; ürün adlarını İngilizce bırak." if settings["language"] == "tr" else ""
    try:
        with client.beta.messages.stream(
            model=settings["model"],
            max_tokens=16000,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            output_config={"effort": "low"},
            system=f"Sen sabırlı bir Google Cloud sertifika eğitmenisin. Bugün {dt.date.today()}. {lang}",
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            msg = stream.get_final_message()
    except anthropic.APIError as e:
        raise AIError(_api_error_message(anthropic, e)) from e
    if msg.stop_reason == "refusal":
        raise AIError("Model bu isteği yanıtlamadı.")
    return "\n".join(b.text for b in msg.content if b.type == "text").strip()

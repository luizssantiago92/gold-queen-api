"""Deterministic scope guard for Gold Queen chat (RF05).

Off-topic questions are rejected before quota is consumed or Gemini is called,
keeping the advisor focused on treasury data and app features.
"""

from app.core.locale import Locale

# Finance, treasury, and Gold Queen app vocabulary (EN + PT).
_IN_SCOPE_MARKERS: tuple[str, ...] = (
    "gold",
    "ouro",
    "money",
    "dinheiro",
    "moeda",
    "treasury",
    "tesouro",
    "balance",
    "saldo",
    "spend",
    "spending",
    "gasto",
    "gastos",
    "expense",
    "despesa",
    "income",
    "renda",
    "receita",
    "budget",
    "orcamento",
    "save",
    "saving",
    "poupar",
    "econom",
    "financ",
    "bank",
    "banco",
    "conta",
    "account",
    "transaction",
    "transac",
    "moviment",
    "category",
    "categor",
    "pluggy",
    "open finance",
    "connect",
    "conect",
    "sync",
    "sincron",
    "queen",
    "rainha",
    "advisor",
    "conselh",
    "tip",
    "dica",
    "plan",
    "plano",
    "limit",
    "limite",
    "quota",
    "cota",
    "dashboard",
    "chart",
    "grafico",
    "month",
    "mes",
    "invest",
    "debt",
    "divida",
    "credit",
    "credito",
    "card",
    "cartao",
    "pix",
    "bill",
    "conta de luz",
    "subscription",
    "assinatura",
    "banquet",
    "banquete",
    "food",
    "aliment",
    "transport",
    "housing",
    "moradia",
)

# Clear off-topic intents — general chat, coding, trivia, etc.
_OUT_OF_SCOPE_MARKERS: tuple[str, ...] = (
    "weather",
    "clima",
    "football",
    "futebol",
    "soccer",
    "recipe",
    "receita de bolo",
    "poem",
    "poema",
    "joke",
    "piada",
    "python code",
    "javascript",
    "write code",
    "escreva codigo",
    "capital of",
    "capital da",
    "who is ",
    "quem e ",
    "quem é ",
    "movie",
    "filme",
    "series",
    "serie",
    "game",
    "jogo",
    "politics",
    "politica",
    "election",
    "eleicao",
    "bitcoin price",
    "preco do bitcoin",
    "stock tip",
    "horoscope",
    "horoscopo",
    "translate ",
    "traduz",
    "homework",
    "tarefa de casa",
    "math problem",
    "ignore previous",
    "ignore all",
    "system prompt",
    "jailbreak",
    "roleplay as",
    "finja ser",
)

_OFF_TOPIC_REPLIES: dict[Locale, str] = {
    "en": (
        "Noble subject, the Gold Queen counsels only on your treasury — balances, "
        "spending, categories, bank connections, and this app's limits. "
        "Ask about your gold, not the wider realm."
    ),
    "pt": (
        "Nobre subdito, a Rainha Dourada só dispensa conselhos sobre o vosso tesouro — "
        "saldo, gastos, categorias, bancos conectados e limites deste app. "
        "Perguntai sobre o vosso ouro, não sobre assuntos alheios ao reino financeiro."
    ),
}


def is_chat_in_scope(question: str) -> bool:
    """Return True when the question belongs to treasury / app context."""
    normalized = " ".join(question.lower().split())
    if not normalized:
        return False

    if any(marker in normalized for marker in _OUT_OF_SCOPE_MARKERS):
        return False

    return any(marker in normalized for marker in _IN_SCOPE_MARKERS)


def off_topic_reply(locale: Locale) -> str:
    return _OFF_TOPIC_REPLIES[locale]

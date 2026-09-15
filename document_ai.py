import anthropic
import numpy as np
import os
import random
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# ---- risky legal terms to flags ----
RISK_TERMS = [
    "indemnif", "indemnification",
    "unlimited liability", "personal guarantee",
    "penalty", "irrevocable", "non-cancellable",
    "perpetual", "automatic renewal",
    "sole discretion",
    "time is of the essence",
    "assign all intellectual property",
    "non-compete",
    "non-solicitation",
    "in perpetuity",
    "arbitration",
    "governed by laws of",
    "dollar-denominated",
    "waive",
    "indemnify",
    "force majeure",
    "consequential damage",
    "best endeavours",
]

# --- facts for spinner ---
LEGAL_COMPARISONS = [
    {
        "topic": "Limitation Period for Contract Claims",
        "uk": "The Limitation Act 1980 gives 6 years from breach to bring a contract claim in England and Wales.",
        "nigeria": "Lagos State Limitation Law also provides 6 years, but this varies across Nigerian states — some have 5 years.",
        "difference": "UK limitation is uniform nationally. Nigeria's periods vary by state, making jurisdiction critical."
    },
    {
        "topic": "Verbal Contracts",
        "uk": "Verbal contracts are legally binding in the UK for most agreements. Exceptions include land transfers and guarantees, which must be in writing.",
        "nigeria": "Verbal contracts are also enforceable in Nigeria under common law principles inherited from English law. Land transactions require writing under the Land Use Act 1978.",
        "difference": "Both systems recognise verbal contracts but require writing for land — Nigeria's Land Use Act vests all land in state governors, creating unique title complexities."
    },
    {
        "topic": "Contract Formation",
        "uk": "UK contract law requires: offer, acceptance, consideration, intention to create legal relations, and certainty of terms.",
        "nigeria": "Nigerian contract law follows the same English common law principles: offer, acceptance, consideration, intention, and capacity.",
        "difference": "Both systems share the same foundation — Nigeria inherited English common law. Key differences arise in enforcement and local statutory overlays."
    },
    {
        "topic": "Penalty Clauses",
        "uk": "UK courts may strike down penalty clauses that are disproportionate to the legitimate interest being protected (Cavendish Square v Makdessi, 2015).",
        "nigeria": "Nigerian courts apply similar principles — liquidated damages clauses are enforceable but courts can review and reduce extravagant penalties.",
        "difference": "UK law was clarified by the 2015 Supreme Court ruling. Nigerian courts apply older English principles and may be less predictable on penalty clause enforceability."
    },
    {
        "topic": "Arbitration Clauses",
        "uk": "The Arbitration Act 1996 governs arbitration in England and Wales. Arbitration clauses in contracts are generally upheld.",
        "nigeria": "The Arbitration and Conciliation Act (ACA) 1988 governs arbitration in Nigeria. The ACA was modelled on the UNCITRAL Model Law.",
        "difference": "A Nigerian contract specifying arbitration in London is common for international deals — it removes disputes from Nigerian courts entirely, which some Nigerian parties contest."
    },
    {
        "topic": "Employment Contract Termination",
        "uk": "UK employees with 2+ years service have unfair dismissal protection. Statutory minimum notice is 1 week per year of service up to 12 weeks.",
        "nigeria": "Nigerian labour law under the Labour Act requires 1 month notice for monthly-paid employees. Wrongful termination gives rise to damages, not reinstatement.",
        "difference": "UK law provides stronger employee protections with tribunal-enforced reinstatement as a possible remedy. Nigerian courts rarely order reinstatement."
    },
    {
        "topic": "Intellectual Property in Contracts",
        "uk": "UK IP ownership follows the Copyright, Designs and Patents Act 1988. Work created by an employee in the course of employment belongs to the employer.",
        "nigeria": "Nigeria's Copyright Act 2022 provides that works created by employees in the course of employment vest in the employer — mirroring UK principles.",
        "difference": "Both systems agree on employer ownership of employee-created IP. Nigeria's 2022 Act modernised its copyright framework significantly."
    },
    {
        "topic": "Non-Compete Clauses",
        "uk": "Non-compete clauses are enforceable in the UK only if they protect a legitimate business interest and are reasonable in scope, duration, and geography.",
        "nigeria": "Nigerian courts apply similar reasonableness tests. Excessively broad non-compete clauses are struck down as being in restraint of trade.",
        "difference": "Both systems apply the restraint of trade doctrine. UK case law is more developed — Nigerian courts often follow English precedent on this issue."
    },
    {
        "topic": "Force Majeure",
        "uk": "English law has no general doctrine of force majeure — it must be expressly included in the contract. The doctrine of frustration applies in limited circumstances.",
        "nigeria": "Nigerian law similarly requires an express force majeure clause. Courts apply English frustration principles where no clause exists.",
        "difference": "Unlike many civil law countries, neither UK nor Nigerian common law implies force majeure — making the clause essential to include in any serious contract."
    },
    {
        "topic": "Governing Law Clauses",
        "uk": "Parties to a UK commercial contract can freely choose the governing law. English law is the most commonly chosen law for international contracts globally.",
        "nigeria": "Nigerian parties can also choose governing law. However, Nigerian courts may refuse to apply foreign law where it conflicts with Nigerian public policy.",
        "difference": "English law's global dominance means many Nigerian international contracts specify English law — removing the dispute from Nigerian courts entirely."
    }
]




def get_api_key():
    try:
        import streamlit as st
        return st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    except:
        return os.getenv("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=get_api_key())
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


def get_random_comparison():
    """Returns a random UK vs Nigerian law comparison."""
    return random.choice(LEGAL_COMPARISONS)

def get_loading_fact():
    """Returns a single random legal fact for spinners."""
    facts = [
        "📜 A contract signed under duress is voidable — not automatically void.",
        "⚖️ In Nigeria, all land is vested in state governors under the Land Use Act 1978.",
        "📜 UK courts can imply terms into contracts that are 'obvious' or necessary for business efficacy.",
        "⚖️ Nigerian courts follow English common law precedent where no local statute applies.",
        "📜 An indemnity clause transfers risk — always read it carefully before signing.",
        "⚖️ A 'time is of the essence' clause makes deadlines legally strict in both UK and Nigerian law.",
        "📜 In UK law, consideration must be sufficient but need not be adequate.",
        "⚖️ Nigerian arbitration awards are enforceable internationally under the New York Convention.",
        "📜 A non-disclosure agreement (NDA) is enforceable in both the UK and Nigeria.",
        "⚖️ Under UK law, minors (under 18) cannot be bound by most contracts.",
    ]
    return random.choice(facts)


def chunk_text(text, chunk_size=2500, overlap=200):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    step = chunk_size - overlap

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():     # skip empty chunks
            chunks.append(chunk)
        start += step 

    return chunks

def get_embeddings(chunks):
    """Embed a list of text chunks."""
    return embedding_model.encode(chunks)

def cosine_similarity(a, b):
    """Calculate similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def find_relevant_chunks(question, chunks_data, top_k=3):
    """RAG retrieval - find most relevant chunks for a question."""
    question_embedding = embedding_model.encode(question)

    results = []
    for chunk in chunks_data:
        score = cosine_similarity(
            question_embedding,
            chunk["embedding"]
        )
        results.append((chunk["chunk_text"], score))

    results.sort(key=lambda x: x[1], reverse=True)
    return [text for text, score in results[:top_k]]


def analyse_document(extracted_text, filename):
    """Extract key clauses and summary from document."""
    system = """You are an experienced legal analyst specialising in contract review 
    for both UK and Nigerian law.
    
    Analyse the document and produce a structured report with these exact sections:
    1. EXECUTIVE SUMMARY
       What is this document? What is its purpose?
       3-4 sentences maximum.

    2. KEY PARTIES
       Who are the parties? What is each party's role?

    3. CORE OBLIGATIONS
       What must each party do? List clearly.

    4. IMPORTANT DATES AND DEADLINES
       Any time-sensitive terms, notice periods, renewal dates.

    5. PAYMENT TERMS
       Amounts, schedules, penalties for late payment.
       If none, state: No payment terms found.

    6. TERMINATION CONDITIONS
       How can this contract be ended by either party?

    7. JURISDICTION AND GOVERNING LAW
       Which country's law applies? Where must disputes be resolved?

    Use plain English alongside legal terms.
    Format with each clear section headers.
    Be precise - if something is unclear or missing, say so."""

    # for very long documents, use first 15,000 chars for summary
    text_for_analysis = extracted_text[:15000]
    if len(extracted_text) > 15000:
        text_for_analysis += "\n\n[Document truncated for summary - full text searchable via Q&A]"

    prompt = f"""Analyse this legal document: {filename}

{text_for_analysis}"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def find_risk_flags(extracted_text):
    """Scan full document text for risky legal terms."""
    text_lower = extracted_text.lower()
    found_flags = []

    for term in RISK_TERMS:
        if term.lower() in text_lower:
            # find the surrounding context
            idx = text_lower.find(term.lower())
            start = max(0, idx - 100)
            end = min(len(extracted_text), idx + 200)
            context = extracted_text[start:end].strip()
            found_flags.append({
                "term": term,
                "context": f"...{context}..."
            })

    return found_flags


def answer_question(question, chunks_data, filename):
    """RAG-based Q&A on the document."""
    relevant_chunks = find_relevant_chunks(
        question, chunks_data, top_k=3
    )

    context = "\n\n---\n\n".join(relevant_chunks)

    system = """You are an expert legal analyst.
Answer questions about the legal document provided using ONLY the context given.
If the answer is not in the context, say:
'This information was not found in the provided document sections.
Try rephrasing your question or ask about a different clause.'
Be precise, professional, and cite specific clauses when possible."""

    prompt = f"""Document: {filename}

Relevant sections:
{context}

Question: {question}"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text



































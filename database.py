import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.errors
import bcrypt 
import json 
import os 
import streamlit as st 
from dotenv import load_dotenv 
from datetime import datetime 

load_dotenv()

def get_connection():
    try:
        db_url = st.secrets.get("DATABASE_URL") or os.getenv("DATABASE_URL")
    except:
        db_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(db_url, sslmode="require")
    return conn


# ---- AUTH ----

def register_user(username, password):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        )
        cursor.execute("""
            INSERT INTO users (username, password, created_at)
            VALUES (%s, %s, %s)
        """, (
            username, hashed.decode("utf-8"),
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()
        return True
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False
    finally:
        conn.close()


def login_user(username, password):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute(
            "SELECT * FROM users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()
        if user and bcrypt.checkpw(
            password.encode("utf-8"),
            user["password"].encode("utf-8")
        ):
            return dict(user)
        return None
    finally:
        conn.close()


# ---- DOCUMENTS ----

def save_document(user_id, filename, file_type, extracted_text):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            INSERT INTO documents (user_id, filename, file_type, extracted_text, upload_date)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            user_id, filename, file_type, extracted_text,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        result = cursor.fetchone()
        conn.commit()
        return result["id"]
    finally:
        conn.close()


def get_documents(user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT id, filename, file_type, upload_date, summary, risk_flags
            FROM documents
            WHERE user_id = %s
            ORDER BY upload_date DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_document_by_id(document_id, user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT * FROM documents
            WHERE id = %s AND user_id = %s
        """, (document_id, user_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_document_analysis(document_id, summary, risk_flags):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            UPDATE documents
            SET summary = %s, risk_flags = %s
            WHERE id = %s
        """, (summary, risk_flags, document_id))
        conn.commit()
    finally:
        conn.close()


def delete_document(document_id, user_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            DELETE FROM documents
            Where id = %s AND user_id = %s
        """, (document_id, user_id))
        conn.commit()
    finally:
        conn.close()


# ---- CHUNKS ----

def save_chunks(document_id, chunks, embeddings):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            cursor.execute("""
                INSERT INTO document_chucks (documnet_id, chunk_index, chunk_text, embedding)
                VALUES (%s, %s, %s, %s)
            """, (document_id, i, chunk, json.dumps(embedding.tolist()))
            )
        conn.commit()
    finally:
        conn.close()


def get_chunks(document_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT chunk_index, chunk_text, embedding
            FROM document_chunks
            WHERE document_id = %s
            ORDER BY chunk_index ASC
        """, (document_id,))
        rows = cursor.fetchall()
        chunks = []
        for row in rows:
            chunks.append({
                "chunk_index": row["chunk_index"],
                "chunk_text": row["chunk_text"],
                "embedding": json.loads(row["embedding"])
            })
        return chunks
    finally:
        conn.close()


# ---- QUESTIONS ----

def save_question(document_id, user_id, question, answer):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            INSERT INTO questions (document_id, user_id, question, answer, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            document_id, user_id, question, answer, datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        conn.commit()
    finally:
        conn.close()


def get_questions(document_id):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("""
            SELECT question, answer, timestamp
            FROM questions
            WHERE document_id = %s
            ORDER BY timestamp DESC
        """, (document_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()















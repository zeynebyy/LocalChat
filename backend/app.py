from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import sys
import uuid
import requests
import sqlite3
from datetime import datetime

# 📁 Veritabanı yolu
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "chat_history.db"))

# Üst dizindeki klasörlere erişim
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 📦 Veritabanı fonksiyonları
from database.db import (
    create_tables,
    save_message,
    get_conversations,
    get_messages,
    set_conversation_title,
    delete_conversation,
    set_favorite_message,
    get_favorite_messages,
    set_conversation_favorite,
    save_settings,
    get_settings
)

app = Flask(__name__)
CORS(app)
create_tables()

# 🧠 Prompt oluşturucu
def build_prompt(history, current_input, system_behavior=""):
    prompt = ""
    if system_behavior:
        prompt += f"<<SYS>>\n{system_behavior.strip()}\n<</SYS>>\n\n"
    for msg in history:
        role = "User" if msg["role"] == "user" else "Assistant"
        prompt += f"{role}: {msg['text']}\n"
    prompt += f"User: {current_input}\nAssistant:"
    return prompt

# 🔥 Ana sohbet endpoint
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    prompt = data.get("prompt")
    conversation_id = data.get("conversation_id")
    passed_settings = data.get("settings")

    if not prompt:
        return jsonify({"error": "Eksik bilgi: prompt eksik"}), 400

    new_chat = False
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        new_chat = True

    history = get_messages(conversation_id)[-10:] if not new_chat else []

    try:
        if passed_settings:
            save_settings(
                conversation_id,
                passed_settings.get("behavior", ""),
                float(passed_settings.get("temperature", 0.7)),
                float(passed_settings.get("top_p", 0.9)),
                int(passed_settings.get("top_k", 40)),
                float(passed_settings.get("repetition_penalty", 1.0))
            )
    except Exception as e:
        return jsonify({"error": f"Ayarlar kaydedilemedi: {str(e)}"}), 500

    settings = get_settings(conversation_id)
    system_behavior = settings.get("behavior", "Tüm cevaplarını sadece Türkçe olarak ver. Açık ve sade yanıtla.")
    temperature = settings.get("temperature", 0.7)
    top_p = settings.get("top_p", 0.9)
    top_k = settings.get("top_k", 40)
    repetition_penalty = settings.get("repetition_penalty", 1.0)

    enhanced_prompt = build_prompt(history, prompt, system_behavior)

    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": enhanced_prompt,
            "stream": False,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repeat_penalty": repetition_penalty
        })
        if response.status_code != 200:
            return jsonify({"error": "Ollama modeli yanıt vermedi"}), 500

        response_text = response.json().get("response", "").strip()
        save_message(conversation_id, "user", prompt)
        save_message(conversation_id, "assistant", response_text)

    except Exception as e:
        return jsonify({"error": f"Model çalışırken hata oluştu: {str(e)}"}), 500

    if new_chat:
        first_sentence = prompt.split(".")[0].strip()
        title = first_sentence if len(first_sentence) >= 5 else "Yeni Sohbet"
        set_conversation_title(conversation_id, title)

    return jsonify({
        "response": response_text,
        "conversation_id": conversation_id
    })

# 🔧 Ayar güncelleme (mevcut sohbet için)
@app.route("/settings/<conversation_id>", methods=["POST"])
def update_settings(conversation_id):
    try:
        data = request.get_json()
        save_settings(
            conversation_id,
            data.get("behavior", ""),
            float(data.get("temperature", 0.7)),
            float(data.get("top_p", 0.9)),
            int(data.get("top_k", 40)),
            float(data.get("repetition_penalty", 1.0))
        )
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": f"Ayar kaydedilemedi: {str(e)}"}), 500

# 🔧 Ayarları getir
@app.route("/settings/<conversation_id>", methods=["GET"])
def fetch_settings(conversation_id):
    settings = get_settings(conversation_id)
    return jsonify(settings)

# 🧾 Diğer endpointler (favori, silme, listeleme vs.)
@app.route("/conversations", methods=["GET"])
def list_conversations():
    return jsonify(get_conversations())

@app.route("/conversation/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, message, id, favorite FROM messages WHERE conversation_id = ?", (conversation_id,))
    rows = cursor.fetchall()
    conn.close()
    return jsonify([
        {"role": row[0], "text": row[1], "id": row[2], "favorite": bool(row[3])} for row in rows
    ])

@app.route("/conversation/<conversation_id>", methods=["DELETE"])
def delete_conversation_route(conversation_id):
    delete_conversation(conversation_id)
    return jsonify({"status": "deleted", "conversation_id": conversation_id})

@app.route("/rename/<conversation_id>", methods=["POST"])
def rename_conversation(conversation_id):
    data = request.get_json()
    new_title = data.get("title", "").strip()
    if not new_title:
        return jsonify({"error": "Başlık boş olamaz"}), 400
    set_conversation_title(conversation_id, new_title)
    return jsonify({"message": "Başlık güncellendi", "title": new_title})

@app.route("/favorites", methods=["GET"])
def list_favorite_messages():
    try:
        messages = get_favorite_messages()
        return jsonify(messages)
    except Exception as e:
        return jsonify({"error": f"Favoriler alınamadı: {str(e)}"}), 500

@app.route("/conversation/<conv_id>/favorite", methods=["POST"])
def toggle_conv_fav(conv_id):
    fav = bool(request.json.get("favorite", False))
    set_conversation_favorite(conv_id, fav)
    return {"favorite": fav}

@app.route("/favorites/<conversation_id>", methods=["GET"])
def get_favorites(conversation_id):
    try:
        favorites = get_favorite_messages(conversation_id)
        return jsonify(favorites)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/conversation/<conv_id>/archive", methods=["POST"])
def archive_conversation(conv_id):
    archived = bool(request.json.get("archived", True))
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE conversations SET archived = ? WHERE id = ?", (1 if archived else 0, conv_id))
    conn.commit()
    conn.close()
    return jsonify({"archived": archived})

@app.route("/conversations/archived", methods=["GET"])
def list_archived_conversations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, last_time, favorite
        FROM conversations
        WHERE archived = 1
        ORDER BY last_time DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return jsonify([
        {
            "id": r["id"],
            "title": r["title"] if r["title"] else "Arşivli Sohbet",
            "last_time": r["last_time"],
            "favorite": bool(r["favorite"]),
        }
        for r in rows
    ])

@app.route("/conversations/favorites", methods=["GET"])
def list_favorite_conversations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, last_time, favorite
        FROM conversations
        WHERE favorite = 1
        ORDER BY last_time DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return jsonify([
        {
            "id": r["id"],
            "title": r["title"] if r["title"] else "Favori Sohbet",
            "last_time": r["last_time"],
            "favorite": bool(r["favorite"]),
        }
        for r in rows
    ])



if __name__ == "__main__":
    app.run(debug=True, port=5000)

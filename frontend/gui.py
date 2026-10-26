import tkinter as tk
from tkinter import scrolledtext
import requests
from functools import partial

API_URL = "http://127.0.0.1:5000/chat"
CONV_URL = "http://127.0.0.1:5000/conversation/"
FAV_URL = "http://127.0.0.1:5000/favorite/"

conversation_id = None  # Sunucudan alınacak
messages = []  # Mesaj geçmişi

# Mesajları ekrana yaz

def display_messages():
    response_box.config(state=tk.NORMAL)
    response_box.delete("1.0", tk.END)
    for msg in messages:
        fav = "★" if msg.get("favorite") else "☆"
        role = "👤" if msg["role"] == "user" else "🤖"
        response_box.insert(tk.END, f"{fav} {role}: {msg['text']}\n")
    response_box.config(state=tk.DISABLED)

# Favori durumunu değiştir

def toggle_favorite(message_id, current_fav):
    try:
        r = requests.post(f"{FAV_URL}{message_id}", json={"favorite": not current_fav})
        if r.status_code == 200:
            load_messages()  # Güncel favori durumunu çek
    except Exception as e:
        response_box.config(state=tk.NORMAL)
        response_box.insert(tk.END, f"\n⚠️ Favori güncellenemedi: {str(e)}")
        response_box.config(state=tk.DISABLED)

# Mesajları backend'den çek

def load_messages():
    global messages
    if not conversation_id:
        return
    try:
        r = requests.get(f"{CONV_URL}{conversation_id}")
        if r.status_code == 200:
            messages.clear()
            messages.extend(r.json())
            display_messages()
    except Exception as e:
        response_box.config(state=tk.NORMAL)
        response_box.insert(tk.END, f"\n⚠️ Mesajlar yüklenemedi: {str(e)}")
        response_box.config(state=tk.DISABLED)

# Mesaj gönder

def send_prompt():
    global conversation_id
    prompt = prompt_entry.get("1.0", tk.END).strip()
    if not prompt:
        return
    payload = {"prompt": prompt}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            result_json = response.json()
            if not conversation_id:
                conversation_id = result_json.get("conversation_id")
            load_messages()
        else:
            response_box.config(state=tk.NORMAL)
            response_box.insert(tk.END, "\n\n❌ Hata: Geçersiz sunucu yanıtı.")
            response_box.config(state=tk.DISABLED)
    except Exception as e:
        response_box.config(state=tk.NORMAL)
        response_box.insert(tk.END, f"\n\n⚠️ Hata: {str(e)}")
        response_box.config(state=tk.DISABLED)

# Arayüz
root = tk.Tk()
root.title("LLM Chat (GUI)")
root.geometry("600x500")

tk.Label(root, text="Prompt girin:", font=("Arial", 12)).pack()
prompt_entry = tk.Text(root, height=5, width=70)
prompt_entry.pack()

tk.Button(root, text="Gönder", command=send_prompt, bg="lightblue").pack(pady=10)

response_box = scrolledtext.ScrolledText(root, height=15, width=70, state=tk.DISABLED)
response_box.pack()

# Favori güncelleme için mesajlara tıklama desteği
def on_message_click(event):
    index = response_box.index(f"@{event.x},{event.y}")
    line = int(index.split(".")[0]) - 1
    if 0 <= line < len(messages):
        msg = messages[line]
        toggle_favorite(msg["id"], msg.get("favorite", 0))

response_box.bind("<Button-1>", on_message_click)

root.after(500, load_messages)
root.mainloop()

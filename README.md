# School Data Chatbot - Website Version

Unga terminal script (`school_rag_gemini.py`) -oda RAG logic-ah edhuthu,
oru proper website-a maathi kudukirom. Same Firebase + LlamaIndex + Gemini
backend, but ipo browser-la chat pannalam.

## Folder structure

```
school_chat_app/
  app.py              <- FastAPI backend (RAG logic + /chat API)
  static/index.html   <- Chat UI (frontend)
  requirements.txt
  serviceAccountKey.json   <- (neenga copy pannunga, idhu indha folder-laye irukkanum)
```

## Setup steps

1. **Idha venum: `serviceAccountKey.json`** - unga Firebase service account
   key-a indha `school_chat_app` folder-laye podunga (`app.py` irukkura
   same folder).

   IMPORTANT: Unga key-a already oru AI chat-la share pannitinga.
   Andha key-a **safe-a vekkanum-na**, Firebase console -> Project Settings
   -> Service Accounts -la poi, pazhaiya key-a delete pannitu, pudhusa
   generate pannunga. Apparam andha pudhusa key-a use pannunga.

2. **Install pannunga:**
   ```
   cd school_chat_app
   pip install -r requirements.txt --break-system-packages
   ```

3. **API key set pannunga** (terminal-la):
   ```
   export GOOGLE_API_KEY="unga-gemini-key-inga"
   ```
   (Windows-la: `set GOOGLE_API_KEY=unga-key`)

4. **Run pannunga:**
   ```
   python app.py
   ```
   First time run pannumbodhu, Firebase-la irundhu data fetch panni,
   index build pannum (konjam time edukum). Apparam "storage" folder
   create aagum -- adutha thadava fast-a start aagum.

5. **Browser-la thirakkunga:**
   ```
   http://localhost:8000
   ```

   Idhu dhan unga chatbot website! Question type pannunga, "Send"
   click pannunga, answer varum.

## Notes

- Marupadiyum data update pannanum-na (students data change aana),
  `storage` folder-a delete pannitu, server-a restart pannunga --
  fresh-a re-index aagum.
- Port already use-la irundha (`8000`), `app.py` last line-la
  `port=8000`-a vera number-a maathikonga.
- Idhu local-a mattum run aagum. Internet-la publish pannanum-na,
  apparam vera step venum (deploy panna) -- adhu pathi kekkalam.

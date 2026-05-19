# """
# assistant_brain.py
# Saare modules ko connect karta hai.
# User ka command leta hai → sahi module call karta hai → response deta hai.
# """

import os
import requests
import json
from dotenv import load_dotenv

# जनरेशन को रोकने के लिए ग्लोबल फ्लैग
should_interrupt = False

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")

def process_command(text, reminder_callback=None, update_ui_callback=None):
    """
    text: user ka voice/text input
    reminder_callback: function jo reminder fire hone pe call hoga
    update_ui_callback: 🆕 UI का फंक्शन जो हर एक शब्द (chunk) आने पर स्क्रीन अपडेट करेगा
    """
    global should_interrupt
    should_interrupt = False  # हर नए सवाल पर फ्लैग को रीसेट करें
    
    result = {
        "intent": "general_chat",
        "action": "none",
        "response": ""
    }
    
    if not text or text.strip() == "":
        return result

    try:
        if should_interrupt:
            result["response"] = "⏹ जनरेशन को यूज़र द्वारा रोक दिया गया।"
            return result

        # सर्वर से लाइव स्ट्रीमिंग ऑन करें
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a helpful AI Student Assistant. Keep answers friendly and short."},
                    {"role": "user", "content": text}
                ],
                "max_tokens": 500,
                "temperature": 0.7,
                "stream": True  
            },
            timeout=15,
            stream=True
        )

        if response.status_code == 200:
            full_response = ""
            
            # हर एक लाइन (शब्द) के आते ही लूप चलेगा
            for line in response.iter_lines():
                # 🚨 सबसे ज़रूरी: अगर यूजर ने STOP दबाया, तो लूप को तुरंत तोड़ दो!
                if should_interrupt:
                    full_response += "\n\n⏹ [जनरेशन को यूज़र द्वारा बीच में रोक दिया गया]"
                    if update_ui_callback:
                        update_ui_callback("\n\n⏹ [जनरेशन को यूज़र द्वारा बीच में रोक दिया गया]")
                    break
                
                if line:
                    decoded_line = line.decode('utf-8').replace('data: ', '')
                    if decoded_line.strip() == "[DONE]":
                        break
                    try:
                        json_data = json.loads(decoded_line)
                        delta = json_data['choices'][0]['delta']
                        if 'content' in delta:
                            chunk = delta['content']
                            full_response += chunk
                            
                            # 🆕 अगर UI का कोई अपडेट फंक्शन पास किया गया है, तो उसे तुरंत शब्द भेजें
                            if update_ui_callback:
                                update_ui_callback(chunk)
                    except:
                        continue
                        
            result["response"] = full_response
        else:
            try:
                error_msg = response.json().get("error", {}).get("message", "Unknown error")
            except:
                error_msg = f"HTTP Error {response.status_code}"
            result["response"] = f"Groq API Error: {error_msg}"
            if update_ui_callback:
                update_ui_callback(result["response"])

    except Exception as e:
        if should_interrupt:
            result["response"] = "⏹ जनरेशन को यूज़र द्वारा रोक दिया गया।"
        else:
            result["response"] = f"Error connecting to AI Server: {str(e)}"
        if update_ui_callback:
            update_ui_callback(result["response"])

    return result


def load_pdf_context(file_path):
    """PDF से टेक्स्ट निकालकर Groq API से उसकी असली समरी जनरेट करना"""
    global _pdf_context
    from pathlib import Path
    import os
    import requests
    import json
    
    file_name = Path(file_path).name
    
    # 1. PDF से टेक्स्ट एक्सट्रेक्ट करना (pypdf या pdfplumber के ज़रिए)
    raw_text = ""
    try:
        # अगर pypdf इंस्टॉल्ड है तो उससे टेक्स्ट निकालें
        import pypdf
        reader = pypdf.PdfReader(file_path)
        page_count = len(reader.pages)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"
    except Exception as e:
        # अगर लाइब्रेरी न हो तो एरर हैंडलिंग
        return {"success": False, "summary": f"PDF Read Error: {str(e)} या pypdf लाइब्रेरी इंस्टॉल नहीं है।"}

    if not raw_text.strip():
        return {"success": False, "summary": "PDF से कोई टेक्स्ट नहीं निकाला जा सका। कृपया पक्का करें कि PDF स्कैन्ड इमेज न हो।"}

    # ग्लोबल कॉन्टेक्स्ट में सेव करें ताकि चैट में इसपर सवाल पूछे जा सकें
    _pdf_context = raw_text
    word_count = len(raw_text.split())

    # 2. Groq API को कॉल करके समरी मांगना
    try:
        # प्रॉम्ट तैयार करना (शुरुआती 4000 वर्ड्स टोकन लिमिट के लिए सेफ हैं)
        summary_prompt = f"Please provide a comprehensive and clear summary of the following document text:\n\n{raw_text[:8000]}"
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are an expert academic assistant. Summarize documents clearly with bullet points."},
                    {"role": "user", "content": summary_prompt}
                ],
                "max_tokens": 8000,
                "temperature": 0.5
            },
            timeout=25
        )

        if response.status_code == 200:
            ai_summary = response.json()['choices'][0]['message']['content']
            return {
                "success": True,
                "file_name": file_name,
                "page_count": page_count,
                "word_count": word_count,
                "summary": ai_summary # 👈 यहाँ आएगी असली शानदार समरी!
            }
        else:
            return {"success": False, "summary": f"Groq Error: {response.status_code}"}

    except Exception as e:
        return {"success": False, "summary": f"API से समरी जनरेट करने में दिक्कत आई: {str(e)}"}


def on_startup(reminder_callback=None):
    pass

def interrupt_generation():
    """जब UI का Stop बटन दबेगा, तो यह ग्लोबल फ्लैग को True कर देगा"""
    global should_interrupt
    should_interrupt = True
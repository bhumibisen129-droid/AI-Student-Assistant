# """
# assistant_brain.py
# User command → module call  → response .
# """

import os
import requests
import json
from dotenv import load_dotenv


should_interrupt = False

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")

def process_command(text, reminder_callback=None, update_ui_callback=None):
    
    global should_interrupt
    should_interrupt = False  
    
    result = {
        "intent": "general_chat",
        "action": "none",
        "response": ""
    }
    
    if not text or text.strip() == "":
        return result

    try:
        if should_interrupt:
            result["response"] = "⏹ The generation was stopped by the user."
            return result

        
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
            
            
            for line in response.iter_lines():
                
                if should_interrupt:
                    full_response += "\n\n⏹ [The generation was stopped by the user.]"
                    if update_ui_callback:
                        update_ui_callback("\n\n⏹ [The generation was stopped by the user.]")
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
            result["response"] = "⏹ The generation was stopped by the user."
        else:
            result["response"] = f"Error connecting to AI Server: {str(e)}"
        if update_ui_callback:
            update_ui_callback(result["response"])

    return result


def load_pdf_context(file_path):
    
    global _pdf_context
    from pathlib import Path
    import os
    import requests
    import json
    
    file_name = Path(file_path).name
    
    
    raw_text = ""
    try:
        
        import pypdf
        reader = pypdf.PdfReader(file_path)
        page_count = len(reader.pages)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                raw_text += text + "\n"
    except Exception as e:
        
        return {"success": False, "summary": f"PDF Read Error: {str(e)} Or the pypdf library is not installed."}

    if not raw_text.strip():
        return {"success": False, "summary": "No text could be extracted from the PDF. Please make sure the PDF is not a scanned image."}

    
    _pdf_context = raw_text
    word_count = len(raw_text.split())

    
    try:
       
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
                "summary": ai_summary 
            }
        else:
            return {"success": False, "summary": f"Groq Error: {response.status_code}"}

    except Exception as e:
        return {"success": False, "summary": f"There was an issue generating the summary through the API {str(e)}"}


def on_startup(reminder_callback=None):
    pass

def interrupt_generation():
    
    global should_interrupt
    should_interrupt = True
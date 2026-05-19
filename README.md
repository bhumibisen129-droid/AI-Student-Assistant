# AI Student Assistant 🤖📚

An intelligent, AI-powered assistant designed to streamline student workflows, manage academic notes, handle documents, and track reminders efficiently. Powered by advanced Large Language Models (LLMs) via the Groq API, this assistant acts as a personalized digital brain for students.

---

## 🌟 Key Features

* **Intelligent Document Handling (PDFs):** Smart processing and extraction of insights from academic PDFs and study materials.
* **Contextual Assistant Brain:** Multi-turn conversational AI that understands academic contexts, explains complex topics, and answers queries.
* **Automated Notes Management:** Create, structure, and organize study notes seamlessly.
* **Smart Reminders:** Built-in task and scheduling tracking system to keep students updated on deadlines and exams.

---

## 🛠️ Tech Stack

* **Language:** Python 3.10+
* **LLM Orchestration:** Groq API (High-speed inference)
* **Environment Management:** Python-Dotenv (Secure API Key handling)
* **Core Libraries:** PyPDF2 / pdfplumber (for document extraction), OS, JSON

---

## 🚀 Getting Started

Follow these steps to set up and run the AI Student Assistant locally on your system.

### 1. Prerequisites
Ensure you have Python installed. You will also need a **Groq API Key**. You can get one from the Groq Console.

### 2. Installation & Setup

Clone the repository and navigate to the project directory:

```bash
git clone [https://github.com/bhumibisen129-droid/AI-Student-Assistant.git](https://github.com/bhumibisen129-droid/AI-Student-Assistant.git)
cd AI-Student-Assistant/student_assistant
```

Create a virtual environment (Recommended):
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

Install the required dependencies:
pip install -r requirements.txt

3. Environment Configuration
GROQ_API_KEY=your_actual_groq_api_key_here

4. Running the Application
python main.py

📂 Project Structure
student_assistant/

├── main.py              ← App entry point

├── core/

│   ├── voice_engine.py  ← Speech-to-text + Text-to-speech

│   ├── nlp_engine.py    ← Intent detection

│   ├── pdf_handler.py   ← PDF summarization

│   ├── reminder.py      ← Reminder system

│   ├── timetable.py     ← Timetable manager

│   └── notes.py         ← Note generation

├── ui/

│   └── dashboard.py     ← Tkinter GUI

├── data/

│   ├── reminders.json

│   ├── timetable.json

│   └── notes/

├── requirements.txt

└── .env

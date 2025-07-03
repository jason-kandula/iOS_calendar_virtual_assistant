import json
import datetime
import requests
import re

'''
MODELFILE
name: helper

is created using
create NAME -f ./Modelfile

'''
# === CONFIGURATION ===
OLLAMA_MODEL = "helper"  # change to your local model name
SCHEDULE_FILE = "schedule.json"

# === Load schedule once ===
def load_schedule(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_schedule(file_path, schedule):
    with open(file_path, "w") as f:
        json.dump(schedule, f, indent=2)

def format_schedule(schedule):
    schedule_lines = [
        f"- {item['date']}: {item['event']}" for item in schedule
    ]
    return "\n".join(schedule_lines)



# === Build system prompt with schedule ===
def build_system_message(schedule_str):
    return f"""
You are a smart productivity assistant. Here is the user's monthly schedule:

{schedule_str}

The user will now ask questions about their time, availability, and how to approach tasks. 
Answer with specific references to their schedule and give helpful advice when possible.
"""
# === Handle user input for new events ===
def try_add_event(user_input, schedule):
    pattern = r"(?:add|schedule) (.+?) on (\w+ \d+)(?: at ([\d:apm\s]+))?"
    match = re.search(pattern, user_input.lower())
    if match:
        event, date_str, time = match.groups()
        try:
            date_obj = datetime.datetime.strptime(date_str.title(), "%B %d").replace(year=datetime.datetime.today().year)
            date_iso = date_obj.date().isoformat()
            description = event.strip().capitalize()
            if time:
                description += f" at {time.strip()}"
            new_event = {"date": date_iso, "event": description}
            schedule.append(new_event)
            schedule.sort(key=lambda e: e["date"])
            save_schedule(SCHEDULE_FILE, schedule)
            return f"✅ Event added: {new_event['date']}: {new_event['event']}", True
        except ValueError:
            return "❌ Could not understand the date. Please use 'Month Day' format (e.g. July 9).", True
    return "", False


# === Send prompt to Ollama ===
def query_ollama(system_msg, user_msg):
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "stream": False
        }
    )
    return response.json()["message"]["content"]

# === MAIN LOOP ===
if __name__ == "__main__":
    schedule = load_schedule(SCHEDULE_FILE)

    print("🤖 Assistant is ready! Ask about your schedule, or add events (e.g. 'Add dentist appointment on July 9 at 2pm').")
    print("Type 'show schedule' to view current events, or 'exit' to quit.\n")

    while True:
        user_input = input("🧑 You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        if user_input.lower() == "show schedule":
            print("\n📅 Your Schedule:\n" + format_schedule(schedule) + "\n")
            continue

        # Try to process event add request
        add_response, matched = try_add_event(user_input, schedule)
        if matched:
            print(f"\n{add_response}\n")
            continue

        # Normal query
        system_prompt = build_system_message(format_schedule(schedule))
        response = query_ollama(system_prompt, user_input)
        print(f"\n🤖 Assistant: {response}\n")
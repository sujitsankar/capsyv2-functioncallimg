import json
import re
import time
from openai import OpenAI
from . import config
import os

def saveFileOpenAI(location):
    client = OpenAI(api_key=config.API_KEY)
    try:
        with open(location, "rb") as f:
            file = client.files.create(file=f, purpose='assistants')
        return file.id
    finally:
        # Ensure the file is properly closed before attempting to delete it
        if os.path.exists(location):
            try:
                os.remove(location)
            except Exception as e:
                print(f"Error removing file: {e}")

def createVectorStore(file_ids, name):
    client = OpenAI(api_key=config.API_KEY)
    vector_store = client.beta.vector_stores.create(name=name, file_ids=file_ids)
    return vector_store.id

def startAssistantThread(prompt, vector_id):
    messages = [{"role": "user", "content": prompt}]
    client = OpenAI(api_key=config.API_KEY)
    tool_resources = {"file_search": {"vector_store_ids": [vector_id]}}
    thread = client.beta.threads.create(messages=messages, tool_resources=tool_resources)
    return thread.id

def runAssistant(thread_id):
    client = OpenAI(api_key=config.API_KEY)
    assistant_id = config.ASSISTANT_ID
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=assistant_id)
    return run.id

def checkRunStatus(thread_id, run_id):
    client = OpenAI(api_key=config.API_KEY)
    run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
    return run.status

def retrieveThread(thread_id):
    client = OpenAI(api_key=config.API_KEY)
    thread_messages = client.beta.threads.messages.list(thread_id)
    list_messages = thread_messages.data
    thread_messages = []
    for message in list_messages:
        obj = {}
        obj['content'] = message.content[0].text.value
        obj['role'] = message.role
        obj['timestamp'] = message.created_at  # Include the timestamp
        thread_messages.append(obj)
    return thread_messages[::-1]


def addMessageToThread(thread_id, prompt):
    client = OpenAI(api_key=config.API_KEY)
    thread_message = client.beta.threads.messages.create(thread_id, role="user", content=prompt)

def extract_company_name(content):
    match = re.search(r'\b[A-Z]{3,}\b', content)
    return match.group(0) if match else "Company"

def runreportgeneration(thread_id):
    client = OpenAI(api_key=config.API_KEY)
    rg_assistant_id = config.RG_ASSISTANT_ID
    run = client.beta.threads.runs.create(thread_id=thread_id, assistant_id=rg_assistant_id)
    return run.id

def run_report_assistant(thread_id):
    client = OpenAI(api_key=config.API_KEY)
    rg_assistant_id = config.RG_ASSISTANT_ID
    # Step 1: Initiate the Run
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=rg_assistant_id,
    )
    
    # Step 2: Check Run Status and Process Tool Calls
    if run.status == 'requires_action':
        # Define the list to store tool outputs
        tool_outputs = []

        # Loop through each tool in the required action section
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            # Here you can add your logic to process each tool call
            if tool.function.name == "generate_overall_report":
                # Assuming you have a function that generates the report
                report_output = generate_overall_report(tool.function.arguments,thread_id)
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": json.dumps(report_output)
                })

        # Submit all tool outputs at once after collecting them in a list
        if tool_outputs:
            try:
                run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                print("Tool outputs submitted successfully.")
            except Exception as e:
                print("Failed to submit tool outputs:", e)
        else:
            print("No tool outputs to submit.")
    
    # Step 3: Final Status Check
    if run.status == 'completed':
        messages = client.beta.threads.messages.list(
            thread_id=thread_id
        )
        return messages
    else:
        return {"status":run.status}

def generate_overall_report(arguments, thread_id):
    # Parse the arguments
    args = json.loads(arguments)

    # Initialize the report dictionary with required fields
    report = {
        "startup_name": args["startup_name"],
        "tagline": args.get("tagline", ""),
        "author_name": args["author_name"],
        "contact_information": args["contact_information"],
        "date_of_report": args["date_of_report"],
        "relevant_urls": args.get("relevant_urls", [])
    }

    # Function to generate content for a specific section
    

    # Generate content for each section
    sections = [
        "executive_summary",
        "company_overview",
        "founder_and_team",
        "product_service_description",
        "market_analysis",
        "business_model",
        "go_to_market_strategy",
        "financial_projections",
        "technology_intellectual_property",
        "operational_plan",
        "risk_analysis",
        "swot_analysis",
        "conclusion",
        "analysts_recommendation"
    ]

    for section in sections:
        section_content = generate_section_content(section, args[section], thread_id)
        report[section] = section_content

    return report

def generate_section_content(section_name, section_args, thread_id):
        prompt = f"Generate the {section_name.replace('_', ' ')} based on the following details:\n{json.dumps(section_args, indent=2)}"
        addMessageToThread(thread_id, prompt)
        run_id = runAssistant(thread_id)
        status = "running"
        while status!="completed":
            time.sleep(5)
            status = checkRunStatus(run_id)
        messages = retrieveThread(thread_id)
        for message in reversed(messages):  # Loop from the end to get the latest message first
            if message['role'] == 'assistant':
                report_content = message['content']
                break
        return report_content
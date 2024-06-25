import streamlit as st
import requests
import time
import base64

backend_url = "http://127.0.0.1:8000"

def display_and_save_id(id_type, id_value):
    st.write(f"{id_type}: {id_value}")
    st.session_state[id_type] = id_value

def process_run(thread_id):
    run_response = requests.post(f"{backend_url}/assistant/run_assistant", data={"thread_id": thread_id})
    if run_response.status_code == 200:
        run_id = run_response.json().get("run_id")
        display_and_save_id("Run ID", run_id)

        status = 'running'
        while status != 'completed':
            with st.spinner('Waiting for assistant response . . .'):
                time.sleep(20)
                status_response = requests.get(f"{backend_url}/assistant/check_run_status", params={"thread_id": thread_id, "run_id": run_id})
                status = status_response.json().get("status")

        messages_response = requests.get(f"{backend_url}/assistant/retrieve_thread", params={"thread_id": thread_id})
        messages = messages_response.json().get("messages")

        for message in messages:
            if message['role'] == 'user':
                st.write('User Message:', message['content'])
            else:
                st.write('Assistant Response:', message['content'])
                st.session_state.last_message_timestamp = message['timestamp']
    else:
        st.error(f"Failed to run assistant. Error: {run_response.json().get('detail')}")

def process_follow_up(thread_id):
    if "last_message_timestamp" in st.session_state:
        last_timestamp = st.session_state.last_message_timestamp
    else:
        last_timestamp = None

    run_response = requests.post(f"{backend_url}/assistant/run_assistant", data={"thread_id": thread_id})
    if run_response.status_code == 200:
        run_id = run_response.json().get("run_id")
        display_and_save_id("Run ID", run_id)

        status = 'running'
        while status != 'completed':
            with st.spinner('Waiting for assistant response . . .'):
                time.sleep(20)
                status_response = requests.get(f"{backend_url}/assistant/check_run_status", params={"thread_id": thread_id, "run_id": run_id})
                status = status_response.json().get("status")

        messages_response = requests.get(f"{backend_url}/assistant/retrieve_thread", params={"thread_id": thread_id})
        messages = messages_response.json().get("messages")

        for message in messages:
            if message['timestamp'] > last_timestamp:
                if message['role'] != 'user':
                    st.write('Assistant Response:', message['content'])
                    st.session_state.last_message_timestamp = message['timestamp']
    else:
        st.error(f"Failed to run assistant. Error: {run_response.json().get('detail')}")

def generate_report(thread_id):
    report_response = requests.post(f"{backend_url}/assistant/generate_report", data={"thread_id": thread_id})
    if report_response.status_code == 200:
        pdf_path = report_response.json().get("pdf_path")
        with open(pdf_path, "rb") as pdf_file:
            base64_pdf = base64.b64encode(pdf_file.read()).decode('utf-8')
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="700" height="900" type="application/pdf">'
            st.markdown(pdf_display, unsafe_allow_html=True)
            st.markdown(f"[Download PDF](data:application/octet-stream;base64,{base64_pdf})", unsafe_allow_html=True)
    else:
        st.error(f"Failed to generate report. Error: {report_response.json().get('detail')}")


def main():
    st.title("🧑‍💻Capsy 💬 Assistant V2")
    
    if 'Vector Store ID' not in st.session_state:
        # Step 1: Upload file
        st.header("Step 1: Upload File")
        company_name = st.text_input("Enter the Company Name")
        uploaded_files = st.file_uploader("Upload Files for the Assistant", accept_multiple_files=False, key="uploader")
        upload_button = st.button("Upload and Generate Summary")

        if upload_button and company_name and uploaded_files:
            uploaded_file = uploaded_files
            file_location = f"files/{uploaded_file.name}"
            with open(file_location, "wb+") as f:
                f.write(uploaded_file.getvalue())

            with st.spinner(f"Uploading {uploaded_file.name}..."):
                try:
                    with open(file_location, "rb") as file:
                        upload_response = requests.post(f"{backend_url}/assistant/upload_file", files={"file": file})
                    if upload_response.status_code == 200:
                        file_id = upload_response.json().get("file_id")
                        if file_id:
                            st.write(f"File ID: {file_id}")
                            st.session_state.file_id = file_id

                            # Create vector store
                            create_response = requests.post(f"{backend_url}/assistant/create_vector_store", data={"file_ids": file_id, "name": company_name})
                            if create_response.status_code == 200:
                                vector_store_id = create_response.json().get("vector_store_id")
                                display_and_save_id("Vector Store ID", vector_store_id)

                                # Start thread
                                initiation = "Generate an executive summary for the uploaded pitch deck."
                                thread_response = requests.post(f"{backend_url}/assistant/start_thread", data={"prompt": initiation, "vector_id": vector_store_id})
                                if thread_response.status_code == 200:
                                    thread_id = thread_response.json().get("thread_id")
                                    display_and_save_id("Thread ID", thread_id)

                                    # Run assistant
                                    process_run(thread_id)
                                else:
                                    st.error(f"Failed to start thread. Status code: {thread_response.status_code}")
                            else:
                                st.error(f"Failed to create vector store. Status code: {create_response.status_code}")
                        else:
                            st.error(f"Failed to upload {uploaded_file.name}. No file ID returned.")
                    else:
                        st.error(f"Failed to upload {uploaded_file.name}. Status code: {upload_response.status_code}")
                except Exception as e:
                    st.error(f"Exception during file upload: {str(e)}")

    if 'Thread ID' in st.session_state:
        # Follow-up questions
        st.header("Follow-up Questions")
        follow_up = st.text_input("Enter your follow-up question", key="follow_up")
        if st.button("Submit Follow-up"):
            try:
                requests.post(f"{backend_url}/assistant/add_message_to_thread", data={"thread_id": st.session_state["Thread ID"], "prompt": follow_up})
                process_follow_up(st.session_state["Thread ID"])
            except Exception as e:
                st.error(f"Exception during follow-up submission: {str(e)}")

        # Generate Report
        if st.button("Generate Report"):
            try:
                generate_report(st.session_state["Thread ID"])
            except Exception as e:
                st.error(f"Exception during report generation: {str(e)}")

if __name__ == "__main__":
    main()

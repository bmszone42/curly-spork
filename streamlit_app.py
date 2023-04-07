# Import required libraries
import streamlit as st
from streamlit import experimental_rerun
import redis
import json
import time
import io
import os
import pandas as pd
from io import BytesIO
import openai
from docx import Document
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

# Get Redis configuration from st.secrets
redis_host = st.secrets["redis"]["host"]
redis_port = st.secrets["redis"]["port"]
redis_password = st.secrets["redis"]["password"]

# Get OpenAI configuration from st.secrets
openai.api_key = st.secrets["openai"]["api_key"]

# Connect to Redis database
r = redis.Redis(host=redis_host, port=redis_port, password=redis_password, db=0)

# Function to read text from different file formats
def read_pdf(file):
    try:
        pdf_reader = PdfReader(file)
    except PdfReadError:
        st.error("Unsupported PDF format")
        return ""

    text = ""
    for page_num in range(min(len(pdf_reader.pages), 5)):
        text += pdf_reader.pages[page_num].extract_text()
    return text

def read_txt(file):
    return file.read()

def read_docx(file):
    try:
        doc = Document(file)
    except docx.opc.exceptions.PackageNotFoundError:
        st.error("Unsupported Word document format")
        return ""

    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

# Function to split text into chunks
def split_text(text, chunk_size=4096):
    lines = text.split("\n")
    wrapped_lines = [word for line in lines for word in line.split(" ")]
    return [wrapped_lines[i:i+chunk_size] for i in range(0, len(wrapped_lines), chunk_size)]

# Function to generate answer using GPT-3
def generate_answer(key, temperature=0.5, max_tokens=150, top_p=1.0):
    try:
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=key,
            max_tokens=max_tokens,
            n=1,
            stop=None,
            temperature=temperature,
            top_p=top_p,
        )
        value = response.choices[0].text.strip()
        timestamp = time.time()
        data = {
            "value": value,
            "created": timestamp,
        }
        r.set(key, json.dumps(data))
    except (openai.error.InvalidRequestError, openai.error.AuthenticationError, openai.error.APIConnectionError,
            openai.error.APIError, openai.error.RateLimitError) as e:
        st.error(f"An error occurred while generating the answer: {e}")
        return ""
    
def process_uploaded_file(uploaded_file):
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    switcher = {
        ".pdf": read_pdf,
        ".docx": read_docx,
        ".txt": read_txt,
    }
    func = switcher.get(file_extension, lambda: st.error("Unsupported file format"))
    return func(uploaded_file)

def get_sorted_data():
    data = {}
    for key in r.keys():
        try:
            json_data = r.get(key).decode("utf-8")
            deserialized_data = json.loads(json_data)
            if "created" in deserialized_data:
                data[(key.decode("utf-8"))] = deserialized_data
        except json.JSONDecodeError:
            pass
    return dict(sorted(data.items(), key=lambda item: item[1]["created"]))

def delete_all_keys():
    for key in r.keys():
        r.delete(key)

def save_data_to_excel(sorted_data):
    data_list = []

    for key, data in sorted_data.items():
        data_list.append({
            "Key": key,
            "Value": data["value"],
            "Created": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data["created"]))
        })

    df = pd.DataFrame(data_list)

    with BytesIO() as bIO:
        with pd.ExcelWriter(bIO, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, index=False)
        bIO.seek(0)
        return bIO.read()

# Streamlit app
def main():
    st.set_page_config(page_title="PDF Q&A", page_icon=":books:")

    st.title("PDF Q&A")
    st.sidebar.title("Options")
    
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])

    if uploaded_file:
        document_text = process_uploaded_file(uploaded_file)
        if document_text:
            st.write("Document Content:")
            st.write(document_text)

            # GPT-3 Settings
            st.sidebar.title("GPT-3 Settings")
            temperature = st.sidebar.slider("Temperature", 0.1, 1.0, 0.5, 0.1)
            max_tokens = st.sidebar.slider("Max Tokens", 10, 500, 150, 10)
            top_p = st.sidebar.slider("Top-p", 0.0, 1.0, 1.0, 0.1)
            
            key = st.text_area("Ask a question about the document:")

            chunk_size = 4096
            chunks = [document_text[i:i+chunk_size] for i in range(0, len(document_text), chunk_size)]

            answer = ""

            if st.button("Get Answer"):
                for chunk in chunks:
                    prompt = f"Answer the following question based on the document's content:\n\n{chunk}\n\nQuestion: {key}\nAnswer:"
                    chunk_answer = generate_answer(prompt, temperature, max_tokens, top_p)
                    answer += chunk_answer
                st.write("Answer:")
                st.write(answer)

                                        
    # Button to store data
    if st.button("Store data"):
        store_data_in_redis(key, value)
        st.success(f"Data stored successfully: Key: {key}, Value: {value}")
        
    # Reset and delete all data with confirmation
    with st.sidebar.expander("Reset and delete all data"):
        st.warning("This will delete all of your data. Are you sure?")
        if st.button("Yes, delete all data"):
            delete_all_keys()
            st.success("All data has been deleted.")

     # Display stored data in the sidebar
    st.sidebar.subheader("Stored data")
    sorted_data = get_sorted_data()
    for key, data in sorted_data.items():

        # Add a checkbox for each entry
        delete_entry = st.sidebar.checkbox(f"Key: {key}, Value: {data['value']}, Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['created']))}")
        if delete_entry:
            r.delete(key)
            st.sidebar.success(f"Data with Key: {key} has been deleted.")
            experimental_rerun()
        
     # Button to save data to an Excel file
    excel_data = save_data_to_excel(sorted_data)
    st.download_button(
        label="Save data to Excel",
        data=excel_data,
        file_name="output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
        
# Run the Streamlit app
if __name__ == "__main__":
    main()

import os
import cv2
import json
import easyocr
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.service_account import Credentials
import google.generativeai as genai
from PIL import Image

# Initialize EasyOCR reader
reader = easyocr.Reader(['en', 'ar'])

# Google Generative AI setup
genai.configure(api_key="AIzaSyDcbFtWlJXlRy-aAwteRmMY3wV1HHJ4Nfs")
model = genai.GenerativeModel("gemini-1.5-flash")

# Authenticate Google Drive using Service Account
def authenticate_google_drive():
    SCOPES = ['https://www.googleapis.com/auth/drive']
    service_account_file = 'credentials.json'

    credentials = Credentials.from_service_account_file(
        service_account_file, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)

# OCR function to extract text from images using EasyOCR
def extract_text_from_image(image_path):
    image = cv2.imread(image_path)
    result = reader.readtext(image)
    text = " ".join([item[1] for item in result])
    return text.strip()

# Enhanced LLM function to handle valid and out-of-scope questions
def ask_questions_with_enhancements(text, question):
    prompt = f"""
    You are an AI expert in processing Arabic invoices. The invoice contains the following extracted text:
    
    {text}

    Based on this text, answer questions strictly related to the invoice details, such as:
    - Product names, quantities, and prices.
    - Invoice numbers and dates.
    - Total amounts and specific product costs.

    If the question is outside the scope of invoice-related details or the answer cannot be derived from the text, respond with:
    "I'm sorry, this question is outside the scope of the invoice details or the provided text does not contain the requested information."

    Question: {question}

    Your response should be clear, concise, and directly address the user's question or clarify limitations.
    """
    response = model.generate_text(prompt=prompt)
    return response.text.strip()

# Function to fetch files from Google Drive folder
def fetch_files_from_drive(folder_id):
    service = authenticate_google_drive()
    query = f"'{folder_id}' in parents"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()

    files = results.get('files', [])
    file_details = []
    if not files:
        return []

    for file in files:
        file_id = file['id']
        file_name = file['name']
        file_details.append({"id": file_id, "name": file_name})
    return file_details

# Function to download a file from Google Drive
def download_file_from_drive(file_id, file_name):
    service = authenticate_google_drive()
    request = service.files().get_media(fileId=file_id)
    file_path = os.path.join("downloads", file_name)

    with open(file_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
    return file_path

# Streamlit App
st.title("Arabic Invoice Chat Assistant")

# Sidebar options
option = st.sidebar.selectbox(
    "Choose an Option",
    ("Chat with Uploaded Image", "Chat with Google Drive File")
)

# Option 1: Chat with uploaded image
if option == "Chat with Uploaded Image":
    st.header("Upload an Image to Chat About It")
    uploaded_file = st.file_uploader("Upload an Image", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        image_path = os.path.join("uploads", uploaded_file.name)
        with open(image_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Display uploaded image
        st.image(image_path, caption="Uploaded Image", use_column_width=True)

        # Extract text
        extracted_text = extract_text_from_image(image_path)
        st.subheader("Extracted Text")
        st.write(extracted_text)

        # Chat interface
        question = st.text_input("Ask a question about the invoice:")
        if st.button("Submit Question"):
            if question:
                response = ask_questions_with_enhancements(extracted_text, question)
                st.subheader("Response")
                st.write(response)

# Option 2: Chat with Google Drive file
elif option == "Chat with Google Drive File":
    st.header("Access Files from Google Drive")
    folder_id = st.text_input("Enter Google Drive Folder ID:")

    if folder_id:
        files = fetch_files_from_drive(folder_id)
        if files:
            st.subheader("Available Files")
            file_name = st.selectbox("Select a File", [f["name"] for f in files])
            selected_file = next(f for f in files if f["name"] == file_name)

            if st.button("Process Selected File"):
                file_path = download_file_from_drive(selected_file["id"], selected_file["name"])
                st.image(file_path, caption="Downloaded File", use_column_width=True)

                # Extract text
                extracted_text = extract_text_from_image(file_path)
                st.subheader("Extracted Text")
                st.write(extracted_text)

                # Chat interface
                question = st.text_input("Ask a question about the invoice:")
                if st.button("Submit Question", key="drive_question"):
                    if question:
                        response = ask_questions_with_enhancements(extracted_text, question)
                        st.subheader("Response")
                        st.write(response)

# Ensure necessary directories exist
if not os.path.exists("uploads"):
    os.mkdir("uploads")
if not os.path.exists("downloads"):
    os.mkdir("downloads")

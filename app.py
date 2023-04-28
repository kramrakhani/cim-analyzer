import os
import re
from urllib import response
import openai
from flask import Flask, request, render_template
from io import BytesIO
from pdf2image import convert_from_bytes
import pytesseract
from transformers import pipeline

app = Flask(__name__)

summary_pipeline = pipeline('summarization')
# risk_pipeline = pipeline('text-classification', model='distilbert-base-uncased', return_all_scores=True)
openai.api_key = "API KEY"


# def extract_due_diligence_questions(text):
#     prompt = "Generate a list of key questions to ask during due diligence based on the following text:\n\n"
#     chunk_size = 3900  # maximum context length minus some buffer
#     chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

#     questions = []
#     for chunk in chunks:
#         response = openai.Completion.create(
#             engine="text-davinci-003",
#             prompt=prompt + chunk,
#             max_tokens=100,
#             n=1,
#             stop=None,
#             temperature=0.5
#         )

#         for line in response.choices[0].text.strip().split('\n'):
#             question = line.strip()
#             if question:
#                 questions.append(question)

#     return questions


# def extract_financial_data(text):
#     prompt = "Extract key financial data points such as revenue, EBITDA, and market share from the following text:\n\n"
#     chunk_size = 3900  # maximum context length minus some buffer
#     chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

#     financial_data = {}
#     for chunk in chunks:
#         response = openai.Completion.create(
#             engine="text-davinci-003",
#             prompt=prompt + chunk,
#             max_tokens=100,
#             n=1,
#             stop=None,
#             temperature=0.5
#         )
#         print("$$$$$$$$$$$$$$$")
#         print(response.choices[0].text)
#         # for key, value in response.choices[0].text.strip().split('\n'):
#         #     key = key.strip()
#         #     value = value.strip()
#         #     if key and value:
#         #         financial_data[key] = value

#         for line in response.choices[0].text.strip().split('\n'):
#             parts = line.strip().split(':')
#             if len(parts) == 2:
#                 key, value = parts
#                 print(key + "  " + value)
#                 financial_data[key.strip()] = value.strip()

#     return financial_data
# # ... rest of the app.py code

def extract_financial_data(text):
    prompt = "Extract key financial data points such as revenue, EBITDA, and market share from the following text:\n\n"
    chunk_size = 3900  # maximum context length minus some buffer
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    financial_data = {}
    for chunk in chunks:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt + chunk,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.5
        )
        for line in response.choices[0].text.strip().split('\n'):
            parts = line.strip().split(':')
            if len(parts) == 2:
                key, value = parts
                financial_data[key.strip()] = value.strip()

    return financial_data


@app.route('/')
def index():
    return render_template('index.html')

# ... other parts of the code


# def process_text_in_chunks(text, pipeline, chunk_size=450):
#     tokens = text.split()
#     chunks = [' '.join(tokens[i:i+chunk_size])
#               for i in range(0, len(tokens), chunk_size)]
#     results = []
#     for chunk in chunks:
#         results.extend(pipeline(chunk))
#     return results
def process_text_in_chunks(text, pipeline, chunk_size=450):
    tokens = text.split()
    chunks = [' '.join(tokens[i:i+chunk_size])
              for i in range(0, len(tokens), chunk_size)]
    results = []
    for chunk in chunks:
        results.extend(pipeline(chunk))
    return results


def extract_due_diligence(text):
    prompt = "Generate a list of key questions to ask bankers and management teams based on the following text:\n\n"
    chunk_size = 3900  # maximum context length minus some buffer
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    due_diligence = []
    for chunk in chunks:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt + chunk,
            max_tokens=100,
            n=1,
            stop=None,
            temperature=0.5
        )
        for line in response.choices[0].text.strip().split('\n'):
            line = line.strip()
            if line:
                due_diligence.append(line)

    return due_diligence


# ... other parts of the code
# def extract_sections(text):
#     sections = []
#     current_section = ""
#     for line in text.split("\n"):
#         if line.startswith("SECTION"):
#             if current_section:
#                 sections.append(current_section.strip())
#                 current_section = ""
#         current_section += line + "\n"
#     sections.append(current_section.strip())
#     return sections

def extract_sections(text):
    sections = []
    current_section = ""
    for line in text.split("\n"):
        if line.startswith("SECTION"):
            if current_section:
                sections.append(current_section.strip())
                current_section = ""
        current_section += line + "\n"
    sections.append(current_section.strip())
    return sections


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return 'No file part', 400

    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400

    text = ""
    if file.filename.lower().endswith('.pdf'):
        images = convert_from_bytes(file.read())
        for image in images:
            page_text = pytesseract.image_to_string(image)
            text += "SECTION " + page_text + "\n"
        with open("output.txt", "w") as output_file:
            output_file.write(text)
    elif file.filename.lower().endswith('.txt'):
        text = file.read().decode('utf-8')

    if text:
        sections = extract_sections(text)
        section_summaries = []
        for section in sections:
            section_summary_results = process_text_in_chunks(
                section, summary_pipeline, chunk_size=400)
            if section_summary_results:
                section_summaries.append(
                    ' '.join([result['summary_text'] for result in section_summary_results]))
            else:
                section_summaries.append("No summary available.")

        final_summary_results = process_text_in_chunks(
            '\n'.join(section_summaries), summary_pipeline, chunk_size=400)
        if final_summary_results:
            final_summary = ' '.join([result['summary_text']
                                     for result in final_summary_results])
            # final_summary = cleanSummary(final_summary)
        else:
            final_summary = "No final summary available."

        financial_data = extract_financial_data(text)
        due_diligence = extract_due_diligence(text)
        return render_template('result.html', summary=final_summary, financial_data=financial_data, due_diligence=due_diligence)

    return 'Unsupported file type', 400


if __name__ == '__main__':
    app.run(debug=True)

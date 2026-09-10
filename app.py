from flask import Flask, render_template, request

import pdfplumber
import os
import re
import spacy

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

nlp = spacy.load("en_core_web_sm")


# --------------------------------
# Normalize text for heading detection
# --------------------------------

def normalize_heading(text):

    text = text.lower().strip()

    # Remove bullets and symbols from beginning
    text = re.sub(r'^[•●▪■◦\-\–\—:]+', '', text)

    # Remove symbols from end
    text = re.sub(r'[•●▪■◦\-\–\—:]+$', '', text)

    # Replace & with and
    text = text.replace("&", "and")

    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


# --------------------------------
# Section definitions
# --------------------------------

SECTION_KEYWORDS = {

    "Personal Details": [
        "personal details",
        "personal information",
        "personal profile",
        "personal data",
        "contact details",
        "contact information",
        "contact"
    ],

    "Profile": [
        "profile",
        "professional profile",
        "profile summary",
        "summary",
        "professional summary",
        "about me"
    ],

    "Objective": [
        "objective",
        "career objective",
        "career goal",
        "career goals"
    ],

    "Education": [
        "education",
        "educational qualification",
        "educational qualifications",
        "educational background",
        "academic qualification",
        "academic qualifications",
        "academic background",
        "academic details",
        "academic profile",
        "qualification",
        "qualifications"
    ],

    "Technical Skills": [
        "skills",
        "technical skills",
        "technical skill",
        "key skills",
        "core skills",
        "technical expertise",
        "technical knowledge",
        "programming skills"
    ],

    "Experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "work history",
        "career experience"
    ],

    "Internship": [
        "internship",
        "internships",
        "internship experience",
        "internship experiences",
        "internship training",
        "industrial training",
        "training"
    ],

    "Projects": [
        "projects",
        "project",
        "project experience",
        "project experiences",
        "project work",
        "academic projects",
        "personal projects",
        "major projects",
        "project details"
    ],

    "Certifications": [
        "certifications",
        "certification",
        "certificates",
        "certificate",
        "professional certifications",
        "professional certification"
    ],

    "Achievements": [
        "achievements",
        "achievement",
        "awards",
        "award",
        "awards and achievements"
    ],

    "Hobbies & Interests": [
        "hobbies",
        "hobby",
        "interests",
        "hobbies and interests",
        "extra curricular activities",
        "extracurricular activities"
    ],

    "Languages": [
        "languages",
        "language",
        "languages known",
        "language proficiency"
    ]
}


# --------------------------------
# Detect section heading
# --------------------------------

def detect_section(line):

    normalized_line = normalize_heading(line)

    # Exact heading match
    for section_name, keywords in SECTION_KEYWORDS.items():

        for keyword in keywords:

            normalized_keyword = normalize_heading(keyword)

            if normalized_line == normalized_keyword:
                return section_name


    # Heading with a colon or small extra text
    for section_name, keywords in SECTION_KEYWORDS.items():

        for keyword in keywords:

            normalized_keyword = normalize_heading(keyword)

            if (
                normalized_line.startswith(normalized_keyword)
                and len(normalized_line) <= len(normalized_keyword) + 12
            ):
                return section_name


    return None


# --------------------------------
# Find person's name
# --------------------------------

def find_name(lines):

    ignored_words = {
        "resume",
        "curriculum vitae",
        "curriculum",
        "vitae",
        "objective",
        "profile",
        "summary",
        "education",
        "skills",
        "technical skills",
        "experience",
        "internship",
        "projects",
        "certifications",
        "achievements",
        "languages",
        "personal details",
        "contact details",
        "java",
        "python",
        "javascript",
        "html",
        "css",
        "sql",
        "mysql",
        "php",
        "c++",
        "web technologies"
    }

    # Check the first few lines because names are normally at the top
    for line in lines[:8]:

        clean_line = line.strip()

        if not clean_line:
            continue

        lower_line = clean_line.lower()

        if lower_line in ignored_words:
            continue

        # Ignore lines containing contact information
        if (
            "@" in clean_line
            or re.search(r'\d{7,}', clean_line)
            or "linkedin" in lower_line
            or "github" in lower_line
            or "address" in lower_line
        ):
            continue

        # Name should contain 2-4 alphabetic words
        if re.fullmatch(
            r"[A-Za-z]+(?:\s+[A-Za-z]+){1,3}",
            clean_line
        ):

            # Avoid technical terms
            technical_words = [
                "java",
                "python",
                "javascript",
                "html",
                "css",
                "sql",
                "mysql",
                "php",
                "bootstrap",
                "technologies",
                "development",
                "engineering"
            ]

            if not any(
                word in lower_line
                for word in technical_words
            ):
                return clean_line.upper()

    return ""


# --------------------------------
# Main route
# --------------------------------

@app.route("/", methods=["GET", "POST"])
def home():

    extracted_text = ""
    name = ""
    email = ""
    phone = ""

    sections = {}

    if request.method == "POST":

        file = request.files.get("resume")

        if file and file.filename.lower().endswith(".pdf"):

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                file.filename
            )

            file.save(filepath)


            # --------------------------------
            # Extract text from PDF
            # --------------------------------

            with pdfplumber.open(filepath) as pdf:

                for page in pdf.pages:

                    text = page.extract_text()

                    if text:
                        extracted_text += text + "\n"


            # --------------------------------
            # Prepare lines
            # --------------------------------

            lines = [
                line.strip()
                for line in extracted_text.splitlines()
                if line.strip()
            ]


            # --------------------------------
            # Find email
            # --------------------------------

            email_match = re.search(
                r'[\w\.-]+@[\w\.-]+\.\w+',
                extracted_text
            )

            if email_match:
                email = email_match.group()


            # --------------------------------
            # Find phone number
            # --------------------------------

            phone_match = re.search(
                r'(\+91[\s-]?)?[6-9]\d{9}',
                extracted_text
            )

            if phone_match:
                phone = phone_match.group()


            # --------------------------------
            # Find name
            # --------------------------------

            name = find_name(lines)


            # --------------------------------
            # Parse resume sections
            # --------------------------------

            current_section = None

            for line in lines:

                clean_line = line.strip()

                found_section = detect_section(clean_line)


                # A new section heading was found
                if found_section:

                    current_section = found_section

                    if current_section not in sections:
                        sections[current_section] = []

                    continue


                # Add text only to the current section
                if current_section:

                    sections[current_section].append(clean_line)


            # --------------------------------
            # Clean section content
            # --------------------------------

            cleaned_sections = {}

            for section, content in sections.items():

                cleaned_content = []

                for item in content:

                    item = item.strip()

                    if not item:
                        continue

                    # Remove repeated bullet symbols
                    item = re.sub(
                        r'^[•●▪■◦]+\s*',
                        '',
                        item
                    )

                    # Avoid duplicate lines
                    if item not in cleaned_content:
                        cleaned_content.append(item)


                if cleaned_content:
                    cleaned_sections[section] = cleaned_content


            sections = cleaned_sections


    return render_template(
        "index.html",
        extracted_text=extracted_text,
        name=name,
        email=email,
        phone=phone,
        sections=sections
    )


# --------------------------------
# Run application
# --------------------------------

if __name__ == "__main__":
    app.run(debug=True)
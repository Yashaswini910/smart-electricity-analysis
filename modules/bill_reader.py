
import io
import re


def extract_bill_text(uploaded_file):
    filename = uploaded_file.name.lower()
    file_bytes = uploaded_file.getvalue()

    if filename.endswith(".pdf"):
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )

    if filename.endswith((".png", ".jpg", ".jpeg")):
        from PIL import Image
        import pytesseract

        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image)

    raise ValueError("Unsupported bill file format.")


def parse_bill_fields(text):
    patterns = {
        "units": [
            r"(?:units consumed|consumption|kwh|units)"
            r"\D{0,25}([0-9]+(?:\.[0-9]+)?)",
            r"([0-9]+(?:\.[0-9]+)?)\s*(?:kwh|units)",
        ],
        "amount": [
            r"(?:total amount|amount payable|net amount|"
            r"bill amount|total due)"
            r"\D{0,30}(?:₹|rs\.?|inr)?\s*"
            r"([0-9,]+(?:\.[0-9]{1,2})?)",
        ],
        "days": [
            r"(?:billing days|no\.?\s*of\s*days)"
            r"\D{0,15}([0-9]{1,3})",
        ],
    }

    extracted = {}

    for field, expressions in patterns.items():
        for pattern in expressions:
            match = re.search(pattern, text, flags=re.IGNORECASE)

            if match:
                try:
                    extracted[field] = float(
                        match.group(1).replace(",", "")
                    )
                    break
                except ValueError:
                    pass

    return extracted

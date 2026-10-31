
# ⚡ Smart Home Electricity Auditor

A Streamlit-based residential electricity consumption analysis application designed for users across India.

## Features

- State and Union Territory selection
- Electricity provider (DISCOM) selection
- Residential/domestic connection category
- Appliance-wise electricity consumption
- Custom appliance entry
- Monthly kWh estimation
- Tariff-based bill estimation for configured verified schedules
- Slab-wise energy charge calculation
- Electricity bill PDF and image upload
- OCR-based bill text extraction
- Actual bill and meter reading comparison
- Consumption charts and insights
- Energy-saving recommendations
- Savings simulator
- Monthly consumption history
- CSV report downloads

## Project Structure

```text
Smart-Home-Electricity-Auditor/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── data/
│   ├── states.json
│   └── tariffs/
│       ├── andhra_pradesh.json
│       ├── telangana.json
│       └── README.md
└── modules/
    ├── __init__.py
    ├── tariff_engine.py
    └── bill_reader.py
```

## Installation

Install Python 3.10 or newer.

Clone the repository:

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd Smart-Home-Electricity-Auditor
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app.py
```

## OCR Requirement

For image-based electricity bill reading, install the Tesseract OCR application separately.

The Python package `pytesseract` is only a wrapper around the Tesseract application.

If Tesseract is not automatically detected on Windows, configure its path in `modules/bill_reader.py`.

## Tariff Accuracy

The application supports state and provider selection across India.

It calculates a tariff estimate only when a matching schedule is present and explicitly marked as verified.

Electricity tariffs can vary by:
- State and DISCOM
- Domestic consumer category
- Consumption slabs
- Sanctioned load
- Billing period
- Applicable duties and adjustments
- Subsidies and other billing rules

Do not use unverified tariff values for bill estimates.

The application is an educational estimation tool, not an official electricity billing system.

## Deployment

The application can be deployed using Streamlit Community Cloud.

1. Push the project to GitHub.
2. Open Streamlit Community Cloud.
3. Connect your GitHub account.
4. Select this repository.
5. Select `app.py` as the main file.
6. Deploy.

## License

For educational and community-service use.

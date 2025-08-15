# Nym Rewards Scraper

This project provides a Python script to fetch rewards from a Nym node and store them in CSV files (daily and monthly).  
The script is designed to run automatically on a Google Cloud VM using **cron**.

## Installation

1. Clone the repository:
   ```bash
   git clone <REPOSITORY_URL>
   cd <PROJECT_NAME>
   ```

2. (Optional but recommended) Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Local Usage

Run the script manually:

```bash
python nym_scraper.py
```

## Automated Execution on VM with cron

On your VM, edit the crontab:

```bash
crontab -e
```

Example to run every day at 12:00:

```bash
0 12 * * * /home/USER/venv/bin/python /home/USER/nym_scraper.py >> /home/USER/log_nym.txt 2>&1
```

## Output

* **nym\_rewards\_daily.csv** → Daily operator rewards log.
* **nym\_rewards\_monthly.csv** → Monthly accumulated rewards.

These files are excluded from the repository
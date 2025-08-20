# Nym Rewards Scraper

This project provides Python scripts to fetch operator rewards from a Nym node, store them in daily and monthly CSV files, and send daily updates to a Telegram bot.  
The scripts are designed to run automatically on a Google Cloud VM using **cron**.

## Features

- Scrapes your Nym node's rewards using Selenium.
- Stores daily and monthly rewards in CSV files.
- Sends daily reward updates (including daily difference and monthly summary) to a Telegram chat.
- Configurable via `.env` file.

## Installation

1. **Clone the repository:**
   ```bash
   git clone <REPOSITORY_URL>
   cd <PROJECT_NAME>
   ```

2. **(Recommended) Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   Create a `.env` file in the project root with the following content (edit values as needed):

   ```
   NYM_NODE_URL=https://explorer.nym.spectredao.net/nodes/YourNodeId
   NYM_BOND_AMOUNT=175
   TELEGRAM_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```

## Usage

### Manual Run

- To fetch rewards and update CSVs only:
  ```bash
  python main.py
  ```

- To fetch rewards, update CSVs, and send a Telegram notification:
  ```bash
  python main_telegram.py
  ```

### Automated Execution with cron (on Linux/VM)

Edit your crontab:
```bash
crontab -e
```

Example to run main_telegram every day at 12:00:
```bash
0 12 * * * /home/USER/venv/bin/python /home/USER/main_telegram.py >> /home/USER/log_telegram.txt 2>&1
```

## Output

- **nym_rewards_daily.csv** → Daily operator rewards log.
- **nym_rewards_monthly.csv** → Monthly accumulated rewards.
- **log_telegram.txt** → Log file for cron output (optional).

These files are excluded from the repository via `.gitignore`.

## Requirements

- Python 3.8+
- Google Chrome or Chromium installed on the VM
- ChromeDriver compatible with your Chrome/Chromium version
- The dependencies listed in `requirements.txt`

## Notes

- The script uses Selenium in headless mode, suitable for VMs without a graphical interface.
- If you see Chrome/Chromium GPU warnings, you can ignore them or use the provided Chrome options to suppress them.
- The daily reward difference will be `0.0` if there is no previous day's record.
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime
import os

# Change URL depending on your node
URL = "https://explorer.nym.spectredao.net/nodes/2BsuTctgodMkyS3YE2ggqL5PrwcmoZmTtt92RxMJ1vvy"

# Change the amount bonded to your node depending on your node
BOND_AMOUNT = 175.0

def get_stake_selenium():
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)
    
    driver.get(URL)

    wait = WebDriverWait(driver, 10)
    stake_element = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "span.text-white.font-medium"))
    )
    stake = stake_element.text

    driver.quit()
    return stake

def stake_to_operator_rewards(stake):
    stake_value = float(stake.replace("NYM", "").replace(",", "").strip())
    operator_rewards_value = stake_value - BOND_AMOUNT
    return operator_rewards_value

def save_to_csv(operator_rewards_value):
    today = datetime.now().strftime("%Y-%m-%d")
    filename = "nym_rewards_daily.csv"

    if os.path.exists(filename):
        df = pd.read_csv(filename)
    else:
        df = pd.DataFrame(columns=["date", "operator_rewards_value"])

    new_row = pd.DataFrame({"date": [today], "operator_rewards_value": [operator_rewards_value]})
    if df.empty:
        df = new_row
    else:
        df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv(filename, index=False)

def update_monthly_rewards(operator_rewards_value):
    monthly_file = "nym_rewards_monthly.csv"
    today = datetime.now()
    current_month = today.strftime("%Y-%m")

    daily_file = "nym_rewards_daily.csv"
    df_daily = pd.read_csv(daily_file)
    df_daily["date"] = pd.to_datetime(df_daily["date"])

    df_daily = df_daily.sort_values("date")

    if len(df_daily) < 2:
        return

    last = df_daily.iloc[-1]
    prev = df_daily.iloc[-2]
    diff = last["operator_rewards_value"] - prev["operator_rewards_value"]

    if diff <= 0:
        return

    if os.path.exists(monthly_file):
        df_monthly = pd.read_csv(monthly_file)
    else:
        df_monthly = pd.DataFrame({
            "month": pd.Series(dtype="str"),
            "reward_sum": pd.Series(dtype="float")
        })

    if current_month in df_monthly["month"].values:
        df_monthly.loc[df_monthly["month"] == current_month, "reward_sum"] += diff
    else:
        new_row = pd.DataFrame({"month": [current_month], "reward_sum": [diff]})
        df_monthly = pd.concat([df_monthly, new_row], ignore_index=True)

    df_monthly.to_csv(monthly_file, index=False)

if __name__ == "__main__":
    try:
        stake = get_stake_selenium()
        operator_rewards_value = stake_to_operator_rewards(stake)
        save_to_csv(operator_rewards_value)
        update_monthly_rewards(operator_rewards_value)
        print(f"{datetime.now()} - Saved operator rewards: {operator_rewards_value}")
    except Exception as e:
        print(f"Error: {e}")

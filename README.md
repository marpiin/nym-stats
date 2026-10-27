# nym-stats

![CI](https://github.com/marpiin/nym-stats/actions/workflows/ci.yml/badge.svg)

nym-stats takes one reading a day of a Nym node from the official Nym API, stores it in
SQLite and sends a summary to Telegram, with an alert when the node's performance stays
low or the reading keeps failing. It is for someone who runs a single node and wants
to know each morning what it earned and whether something needs attention.

I first wrote this by opening the network explorer in headless Chrome, reading one
`span` by its CSS class and subtracting my bond from it. It broke whenever the page
changed, and when it broke it still exited cleanly. I also could not say which figure
the span held, so I could not say what the subtraction meant. This version reads the
mixnet contract's own numbers through nym-api, stores every reading, and fails loudly.

## Example

All numbers here and in the tests are synthetic. Node 900001 does not exist.

`nym-stats report`:

```
Nym node 900001, reading of 2026-10-25 (UTC)

Alerts
Performance below 0.80 for the last 3 readings

Total stake: 48,375.500000 NYM
Operator pledge: 100.000000 NYM
Operator rewards not yet withdrawn: 25.500000 NYM
Change since 2026-10-24: +0.850000 NYM
Profit margin: 20.0 %
Operating cost per interval: 40.000000 NYM
Performance: 0.4800
Uptime on 2026-10-24: 99 %

Rewards per month (NYM)
2026-09        4.250000
2026-10       21.250000
```

`nym-stats notify` sends the same content as Telegram HTML:

```html
<b>Nym node 900001, reading of 2026-10-25 (UTC)</b>

<b>Alerts</b>
Performance below 0.80 for the last 3 readings

Total stake: 48,375.500000 NYM
Operator pledge: 100.000000 NYM
Operator rewards not yet withdrawn: 25.500000 NYM
Change since 2026-10-24: +0.850000 NYM
Profit margin: 20.0 %
Operating cost per interval: 40.000000 NYM
Performance: 0.4800
Uptime on 2026-10-24: 99 %

Rewards per month (NYM)
<pre>2026-09        4.250000
2026-10       21.250000</pre>
```

## Installation

Python 3.11 or newer.

```sh
git clone https://github.com/marpiin/nym-stats.git
cd nym-stats
python -m venv .venv
```

Then, on Linux or macOS:

```sh
.venv/bin/pip install -r requirements.txt -e .
```

On Windows (PowerShell):

```powershell
.\.venv\Scripts\pip install -r requirements.txt -e .
```

The runtime dependencies are `requests` (HTTP) and `python-dotenv` (reading `.env`).

## Configuration

Copy `.env.example` to `.env` in the directory you run the tool from and fill it in.
Variables already set in the environment take precedence over `.env`. Empty values
mean "use the default".

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `NYM_NODE_ID` | yes | | Numeric node id, as shown on the explorer or in `nym-nodes/bonded` |
| `NYM_API_URL` | no | `https://validator.nymtech.net/api` | nym-api base URL |
| `NYM_STATS_DB` | no | `nym_stats.sqlite3` | SQLite file, relative to the working directory |
| `TELEGRAM_BOT_TOKEN` | for `notify` | | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | for `notify` | | Chat the bot writes to |
| `ALERT_MIN_PERFORMANCE` | no | `0.8` | Performance (0 to 1) below which a reading counts as low |
| `ALERT_CONSECUTIVE` | no | `3` | Low readings, or failed fetches, in a row before alerting |

The token is never logged. Errors name the request ("telegram sendMessage") instead
of printing its URL, because the Telegram URL contains the token.

## Usage

```sh
nym-stats fetch                      # read the node, store today's reading
nym-stats report                     # print the summary
nym-stats notify                     # send the summary to Telegram
nym-stats export --out readings.csv  # all readings as CSV
nym-stats export --monthly --out monthly.csv
```

`fetch` stores at most one reading per node per UTC day. If today's reading is already
there it does nothing, without calling the API. Every fetch, good or bad, is recorded,
which is how the failure alert counts consecutive failures.

Any failure is logged with its cause and the command exits with code 1.

## Scheduled runs

Run `fetch` and then `notify` once a day. `notify` runs even when `fetch` failed, so a
failure still reaches Telegram once it has happened `ALERT_CONSECUTIVE` times.

cron (Linux), every day at 06:15:

```cron
15 6 * * * cd "$HOME/nym-stats" && (.venv/bin/nym-stats fetch; .venv/bin/nym-stats notify) >> nym-stats.log 2>&1
```

Windows Task Scheduler, from PowerShell, every day at 08:15:

```powershell
$dir = "$env:USERPROFILE\nym-stats"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -WorkingDirectory $dir -Argument '-NoProfile -Command ".\.venv\Scripts\nym-stats.exe fetch; .\.venv\Scripts\nym-stats.exe notify"'
Register-ScheduledTask -TaskName "nym-stats" -Action $action -Trigger (New-ScheduledTaskTrigger -Daily -At 08:15)
```

## Where the data comes from

Three requests to nym-api per `fetch`:

- `GET /v1/nym-nodes/bonded`: stake, pledge, profit margin and operating cost
- `GET /v1/nym-nodes/performance/{node_id}`: current performance, 0 to 1
- `GET /v1/nym-nodes/uptime-history/{node_id}`: daily uptime, the latest day is kept

Nym's API documentation: <https://nym.com/docs/apis/introduction>, with the Swagger UI
at <https://validator.nymtech.net/api/swagger/index.html>. The field-by-field mapping,
and the two places where the live API differs from its spec, are in
[docs/data-sources.md](docs/data-sources.md).

### What "rewards" means here

`rewarding_details.operator` is documented as "total pledge and compounded reward earned
by the node operator". Subtracting `original_pledge` gives the operator rewards earned
and not yet withdrawn. That is the "Operator rewards not yet withdrawn" line, and it
comes straight from the mixnet contract.

The monthly figures are the sum of the increases of that number between consecutive
readings, computed in SQL from the stored readings. Nothing is accumulated by hand, so
running a day twice cannot change a total.

## What it does not do, and what limits it

- It does not convert to USD or EUR. The old version did, by scraping a price from the
  explorer and calling an exchange-rate API with a key. nym-api has no price endpoint,
  and I did not want to add a third service to get one.
- A withdrawal of rewards drops the number to zero. That step counts as zero, so the
  rewards earned between the last reading and the withdrawal are not counted.
- If you change your pledge, the monthly figure is only right if the contract updates
  `original_pledge` when you do. I have not checked that.
- One reading per day: a change in performance that lasts a few hours can be missed.
- It watches one node and trusts one nym-api instance.
- Amounts are stored as floating point NYM, which is exact to well below 1 unym for any
  realistic stake but is not decimal arithmetic.
- Only the direct dependencies are pinned.

## Development

```sh
pip install -r requirements-dev.txt -e .
ruff format --check .
ruff check .
pytest
detect-secrets-hook --baseline .secrets.baseline $(git ls-files)
```

In PowerShell, the last line is `detect-secrets-hook --baseline .secrets.baseline (git ls-files)`.
Tests run offline against hand-written fixtures in `tests/fixtures/`.

## License

MIT

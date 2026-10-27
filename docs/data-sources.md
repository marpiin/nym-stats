# Data sources

All node data comes from nym-api, the API Nym runs in front of the Nyx chain and
the mixnet contract. Nym lists it with the other public APIs at
<https://nym.com/docs/apis/introduction> and <https://nym.com/docs/apis/nym-api>.

- Swagger UI: <https://validator.nymtech.net/api/swagger/index.html>
- OpenAPI spec: <https://validator.nymtech.net/api/api-docs/openapi.json>
  (version 1.1.90 when this was written, October 2026)

I also went through the Node Status API
(<https://mainnet-node-status-api.nymtech.cc/swagger/>). It has no per-node
endpoint with rewarding data, so it is not used.

## Requests per `fetch`

Base URL: `https://validator.nymtech.net/api` (override with `NYM_API_URL`).
One request per endpoint, three in total.

### `GET /v1/nym-nodes/bonded?per_page=5000`

Schema `PaginatedResponse_NymNodeDetails`. There is no single-node version, so the
whole bonded set is requested in one page and the node is found by `node_id`. In
October 2026 that was about 1100 nodes and the API returned all of them in one
page. If a page ever comes back short, `fetch` fails with a message saying so
instead of looping over pages.

| Field | Spec description | Stored as |
|---|---|---|
| `data[].bond_information.node_id` | Unique id assigned to the bonded node | `node_id` |
| `data[].bond_information.original_pledge.amount` (`denom` = `unym`) | Original amount pledged by the operator of this node | `pledge_nym` |
| `data[].rewarding_details.operator` | Total pledge and compounded reward earned by the node operator | `operator_nym` |
| `data[].rewarding_details.delegates` | Total delegation and compounded reward earned by all node delegators | `delegates_nym` |
| `data[].rewarding_details.cost_params.profit_margin_percent` | The desired percent of the reward to be distributed to the operator | `profit_margin` |
| `data[].rewarding_details.cost_params.interval_operating_cost.amount` | Operating cost of the associated node per the entire interval | `operating_cost_nym` |
| `pagination.total` | | only checked |

Amounts are in unym; 1 NYM = 1,000,000 unym. Total stake is `operator + delegates`.

### `GET /v1/nym-nodes/performance/{node_id}`

Schema `NodePerformanceResponse`: `node_id`, `performance` (number, nullable,
0 to 1). Stored as `performance`.

### `GET /v1/nym-nodes/uptime-history/{node_id}`

Schema `PerformanceHistoryResponse`: `node_id`, `history.data[]`. The entry with
the latest `date` is stored as `uptime_percent` and `uptime_date`.

## Where the spec and the live API differ

I made three anonymous GET requests to the live API, one per endpoint above, to
check field names. Two things did not match the spec:

- `original_pledge.amount` and `interval_operating_cost.amount` are declared as
  integers but come back as strings. The parser accepts both.
- `uptime-history` entries are declared as `{date, performance}` but come back as
  `{date, uptime}`, with `uptime` an integer percentage. The parser reads `uptime`.
  The fixture in `tests/fixtures/uptime_history.json` follows the live shape.

All fixtures are hand-written and synthetic. None of them is a recorded response.

## Not used

- `/v1/nym-nodes/described` is marked deprecated in the spec, and the
  self-described data has nothing about stake or rewards.
- `/v1/nym-nodes/performance-history/{node_id}` returns the same schema as
  `uptime-history`; I did not request it, so its live field names are unchecked.
- `/v2/nym-nodes/annotation/{node_id}` has a detailed score breakdown. It would
  be a fourth request for data this tool does not report.

## Telegram

`POST https://api.telegram.org/bot<token>/sendMessage` with `chat_id`, `text` and
`parse_mode=HTML` (<https://core.telegram.org/bots/api#sendmessage>). Text is
escaped as the HTML style section requires: `<`, `>` and `&` become entities
(<https://core.telegram.org/bots/api#html-style>).

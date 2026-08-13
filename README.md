# Client Proxy setup instructions

## Overview

The client proxy is a local HTTP service that sits between Power BI
Desktop and a Snowflake XMLA endpoint. It accepts HTTP
Basic authentication — where the password is a Snowflake Programmatic
Access Token (PAT).

The proxy can run on the same machine as PBI Desktop or on a
reachable host on the LAN. 

If you are using Parallels, the proxy can run either inside the
Windows VM or on the host Mac — it binds to all interfaces by default
when `XMLA_CLIENT_PROXY_BIND=0.0.0.0` is set (see below).

## Prerequisites

- Python 3.9 or newer.
- Install the single small dependencies: `pip install -r requirements.txt`
  (installs `requests`; add `--user` on a system Python).

## Environment variables

Configure the proxy through environment variables. Only
`XMLA_CLIENT_PROXY_HOST` is strictly required in most deployments.
`XMLA_CLIENT_PROXY_USERNAME` is strictly required in most deployments.
`XMLA_CLIENT_PROXY_PASSWORD` is strictly required in most deployments.

| Name | Default | Meaning |
|---|---|---|
| `XMLA_CLIENT_PROXY_HOST` | Required | Snowflake XMLA Endpoint host (no scheme, no path), e.g. `sf-xmla-myendpoint.spec-account.snowflakecomputing.app`. |
| `XMLA_CLIENT_PROXY_USERNAME` | Required | Your snowflake username |
| `XMLA_CLIENT_PROXY_PASSWORD` | Required | The snowflake PAT for your username |
| `XMLA_CLIENT_PROXY_PORT` | `8000` | Port to listen on. |
| `XMLA_CLIENT_PROXY_BIND` | `localhost` | Bind address. Set to `0.0.0.0` when PBI Desktop connects from a VM or another host. |
| `XMLA_CLIENT_PROXY_LOGGING` | True | Turns logging on (True) or off (False). |
| `XMLA_CLIENT_LOG_TO_CONSOLE` | False | When True, log output to console window |
| `XMLA_CLIENT_PROXY_LOG_MESSAGES` | False | Include request/response bodies in the log. |
| `XMLA_CLIENT_PROXY_LOG_LEVEL` | `INFO` | Numeric log level (`10`, `20`, `30`, …). |
| `XMLA_CLIENT_PROXY_LOG_FILE` | `XmlaClientProxyService.log` | Log file path (relative to CWD). |

## Start the proxy

### macOS / Linux

```sh
cd XmlaClientProxy
pip install -r requirements.txt
cd src
XMLA_CLIENT_PROXY_HOST=<your-snowflake-service-url> 
XMLA_CLIENT_USERNAME=<your-snowflake-username> 
XMLA_CLIENT_USERNAME=<your-snowflake-pat> 
python3 -u xmlaClientProxy.py
```

### Windows PowerShell (original venv-based flow)

```powershell
cd XmlaClientProxy
pip install -r .\requirements.txt
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # may need: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
$env:XMLA_CLIENT_PROXY_HOST=<your-snowflake-service-url> 
$env:XMLA_CLIENT_USERNAME=<your-snowflake-username> 
$env:XMLA_CLIENT_USERNAME=<your-snowflake-pat> 
python3 -u src\xmlaClientProxy.py
```

You should see:

```
XMLA Client Proxy Service is Running!
Hit Control+C to stop
```

## Connect from Power BI Desktop

1. **Get data → More → Analysis Services database**.
2. **Server**: `http://<proxy-host>:8000/engine/xmla`
   The path suffix `/engine/xmla` is required — PBI Desktop does not
   append it automatically, and without it the request lands on the
   Snowflake web UI (405 Method Not Allowed).
3. Either **Connect live** or **Import** works.
4. When prompted for credentials, choose **Basic** and enter any
   username plus your Snowflake PAT as the password. (The username is
   informational only; only the PAT is forwarded upstream.)

If a previous attempt cached bad credentials, clear them first:
**Options → Data source settings → (pick the entry) → Clear Permissions
/ Delete**. *Retry* from the error dialog does **not** re-prompt.


## Troubleshooting

Every request/response is logged to `XmlaClientProxyService.log` (same directory
you started `xmlaClientProxy.py` from).

# Client Proxy setup instructions

## Overview

The client proxy is a local HTTP service that sits between Power BI
Desktop and a Snowflake XMLA endpoint. The XmlaClientProxy inserts 
Basic Authentication headers consisting of the Snowflake Username and 
Programmatic Access Token (PAT) into the messages from PowerBI to the 
Snowflake XMLA Endpoint.

The proxy can run on the same machine as PBI Desktop or on a
reachable host on the LAN. 

If you are using Parallels, the proxy can run either inside the
Windows VM or on the host Mac — it binds to all interfaces by default
when `XMLA_CLIENT_PROXY_BIND=0.0.0.0` is set (see below).

## Prerequisites

- Python 3.9 or newer.
- Install the dependencies: `pip install -r requirements.txt`
  (installs `requests` component).

## Environment variables

Configure the proxy through environment variables. Only
`XMLA_CLIENT_PROXY_HOST` is strictly required in most deployments.
`XMLA_CLIENT_PROXY_USERNAME` is strictly required in most deployments.
`XMLA_CLIENT_PROXY_PASSWORD` is strictly required in most deployments.

| Name | Default | Meaning |
|---|---|---|
| `XMLA_CLIENT_PROXY_HOST` | Required | Snowflake XMLA Endpoint host (no scheme, no path), e.g. `sf-xmla-myendpoint.spec-account.snowflakecomputing.app`. |
| `XMLA_CLIENT_PROXY_USERNAME` | Required | Your Snowflake username |
| `XMLA_CLIENT_PROXY_PASSWORD` | Required | The Snowflake PAT for your username |
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
cd xmla-client-proxy
pip install -r requirements.txt
cd src
XMLA_CLIENT_PROXY_HOST=<your-snowflake-service-url> (do not include https://)
XMLA_CLIENT_USERNAME=<your-snowflake-username> 
XMLA_CLIENT_PASSWORD=<your-snowflake-pat> 
python3 -u src/xmlaClientProxy.py
```
### Windows Cmd (venv-based)

```bat
cd xmla-client-proxy
python -m venv .venv
.\.venv\Scripts\Activate  
pip install -r .\requirements.txt
set XMLA_CLIENT_PROXY_HOST=<your-snowflake-service-url> # do not include https://
set XMLA_CLIENT_USERNAME=<your-snowflake-username> 
set XMLA_CLIENT_PASSWORD=<your-snowflake-pat> 
python3 src\xmlaClientProxy.py
```

### Windows PowerShell (venv-based)

```powershell
cd xmla-client-proxy
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # may need: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
pip install -r .\requirements.txt
$env:XMLA_CLIENT_PROXY_HOST=<your-snowflake-service-url> #do not include https://
$env:XMLA_CLIENT_USERNAME=<your-snowflake-username> 
$env:XMLA_CLIENT_PASSWORD=<your-snowflake-pat> 
python3 src\xmlaClientProxy.py
```

You should see:

```
XMLA Client Proxy Service is Running!
Hit Control+C to stop
```

## Connect from Power BI Desktop

1. **Get data → More → Analysis Services database**.
2. **Server**: `http://localhost:8000/engine/xmla`
   The path suffix `/engine/xmla` is required — PBI Desktop does not
   append it automatically, and without it the request lands on the
   Snowflake web UI (405 Method Not Allowed).
3. **Connect live** 
4. When prompted for credentials, you can just hit OK, the credentials 
   will be inserted by the XmlaClientProxy using the environment
   variables you've set.

## Shut down the XmlaClientProxy

To shut down the XmlaClientProxy, just hit Control+C from the terminal,cmd or powershell window

## Troubleshooting

Every request/response is logged to `XmlaClientProxyService.log` (same directory
you started `xmlaClientProxy.py` from).

If you want to see the log output to the console, set the 
`XMLA_CLIENT_LOG_TO_CONSOLE` environment variable to True.

If you need to see the content of the XMLA messages coming from PowerBI, set the `XMLA_CLIENT_PROXY_LOG_MESSAGES` environment variable to True.

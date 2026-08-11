import os
import sys
import base64
import logging
import ssl
from typing import Optional
from http.server import ThreadingHTTPServer
from http.server import BaseHTTPRequestHandler
import requests

# Environment Variable Names
ENV_XMLA_CLIENT_PROXY_USERNAME="XMLA_CLIENT_PROXY_USERNAME"
ENV_XMLA_CLIENT_PROXY_PASSWORD="XMLA_CLIENT_PROXY_PASSWORD"
ENV_XMLA_CLIENT_PROXY_HOST="XMLA_CLIENT_PROXY_HOST"
ENV_XMLA_CLIENT_PROXY_PORT="XMLA_CLIENT_PROXY_PORT"
ENV_XMLA_CLIENT_PROXY_LOG_MESSAGES="XMLA_CLIENT_PROXY_LOG_MESSAGES"
ENV_XMLA_CLIENT_PROXY_LOG_LEVEL="XMLA_CLIENT_PROXY_LOG_LEVEL"
ENV_XMLA_CLIENT_PROXY_LOG_FILE="XMLA_CLIENT_PROXY_LOG_FILE"
ENV_XMLA_CLIENT_PROXY_BIND="XMLA_CLIENT_PROXY_BIND"
ENV_XMLA_CLIENT_LOGGING="XMLA_CLIENT_LOGGING"
ENV_XMLA_CLIENT_LOG_TO_CONSOLE="XMLA_CLIENT_LOG_TO_CONSOLE"

REQUIRED_ENV_VARS = [ENV_XMLA_CLIENT_PROXY_USERNAME, ENV_XMLA_CLIENT_PROXY_PASSWORD, ENV_XMLA_CLIENT_PROXY_HOST]

# Defaults
DEFAULT_PORT = 8000
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOGGING = True
DEFAULT_LOG_TO_CONSOLE = False
DEFAULT_LOG_MESSAGE_CONTENT = False
DEFAULT_LOG_FILE="XmlaClientProxyService.log"
DEFAULT_BIND = "localhost"

logger = logging.getLogger()
currentPath = os.path.dirname(os.path.abspath(__file__))

def main():
    service = ProxyService()
    service.Start()

class ProxyService(ThreadingHTTPServer):
    def __init__(self, 
            forwardingHost: Optional[str] = os.environ.get(ENV_XMLA_CLIENT_PROXY_HOST), 
            port: int = int(os.environ.get(ENV_XMLA_CLIENT_PROXY_PORT,DEFAULT_PORT)), 
            doLogging: bool = bool(os.environ.get(ENV_XMLA_CLIENT_LOGGING, DEFAULT_LOGGING)),
            logToConsole: bool = bool(os.environ.get(ENV_XMLA_CLIENT_LOG_TO_CONSOLE,DEFAULT_LOG_TO_CONSOLE)),
            logMessages: bool = bool(os.environ.get(ENV_XMLA_CLIENT_PROXY_LOG_MESSAGES,DEFAULT_LOG_MESSAGE_CONTENT)),
            logLevel = int(os.environ.get(ENV_XMLA_CLIENT_PROXY_LOG_LEVEL,DEFAULT_LOG_LEVEL)),
            logFileName: str = os.environ.get(ENV_XMLA_CLIENT_PROXY_LOG_FILE,DEFAULT_LOG_FILE),
            sslCrtFile: Optional[str] = None,#os.path.join(currentPath,"localhost.crt"),
            sslKeyFile: Optional[str] = None, #os.path.join(currentPath,"localhost.key"),
            hostname: str = os.environ.get(ENV_XMLA_CLIENT_PROXY_BIND, DEFAULT_BIND)):

        self.__logger = logger
        self.__isSSL = False
        self.__logger.setLevel(level=logLevel)
        self.__doLogging = doLogging

		# set the logger handlers
        if (logToConsole == True):
            consoleHandler = logging.StreamHandler(sys.stdout)
            consoleHandler.setLevel(self.__logger.level)
            self.__logger.addHandler(consoleHandler)
            
        logHandler = logging.FileHandler(logFileName)
        self.__logger.addHandler(logHandler)

        for h in logger.root.handlers:
            h.setFormatter(logging.Formatter(fmt="%(asctime)s\t%(levelname)s\t%(name)s\t%(message)s"))

        self.LogInfo("Initializing XMLA Client Proxy")

		# Check to make sure all the required environment variables are set
        self.LogDebug("Checking for Required Environment Variables")
        errors = []
        for requiredEnvVar in REQUIRED_ENV_VARS:
            if (os.environ.get(requiredEnvVar) is None):
                error = f"Required Environment Variable {requiredEnvVar} is not set"
                self.LogError(error)
                errors.append(error)

        if len(errors) > 0:
            raise ValueError("\n".join(errors))
            
        if sslCrtFile is not None:
            if not os.path.exists(sslCrtFile):
                raise ValueError(f"Invalid sslCrtFile: {sslCrtFile} does not exist")
        if sslKeyFile is not None:
            if not os.path.exists(sslKeyFile):
                raise ValueError(f"Invalid sslKeyFile: {sslKeyFile} does not exist")
            
        self.__sslCrtFile = sslCrtFile
        self.__sslKeyFile = sslKeyFile
        self.__hostname = hostname
        self.__forwardingHost = forwardingHost
        self.__requestId = 0
        self.__port = port
        self.__logMessages = logMessages

        super().__init__(server_address=(self.Hostname, self.Port), RequestHandlerClass=MessageHandler, bind_and_activate=False)
                
    @property
    def IsSSL(self):
        return self.__isSSL

    @property
    def DoLogging(self):
        return self.__doLogging
    
    @property
    def Logger(self):
        return self.__logger

    @property
    def Hostname(self):
        return self.__hostname

    @property
    def ForwardingHost(self):
        return self.__forwardingHost

    @property
    def Port(self):
        return self.__port

    @property
    def LogMessages(self):
        return self.__logMessages

    def server_bind(self) -> None:
        super().server_bind()
        if self.__sslCrtFile is not None:
            self.LogInfo(f"Wrapping socket with SSL using CrtFile: {self.__sslCrtFile} and KeyFile: {self.__sslKeyFile}")
            sslContext = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            sslContext.check_hostname = False
            sslContext.verify_mode = ssl.CERT_NONE
            sslContext.load_cert_chain(certfile=self.__sslCrtFile, keyfile=self.__sslKeyFile)
            self.socket = sslContext.wrap_socket(self.socket, server_side=True)
            self.__isSSL = True

    def server_activate(self):
        super().server_activate()		
        self.LogInfo("XMLA Client Proxy Service is Ready!")
		
    def GetRequestId(self):
        self.__requestId = self.__requestId + 1
        return self.__requestId

    def server_close(self):
        self.LogInfo("XMLA Client Proxy Service Http Server is Closing")
        super().server_close()
        self.LogInfo("XMLA Client Proxy Service Http Server is Closed!")

    def Start(self):
        self.LogInfo("XMLA Client Proxy Service Starting Up")
        # Create and run the HTTP server
        
        self.server_bind()
        protocol = "http"
        if self.IsSSL:
            protocol = "https"

        self.LogInfo(f"Starting XMLA Client Proxy Service on {protocol}://{self.Hostname}:{self.Port} forwarding messages to {self.ForwardingHost}")
        
        try:
            self.server_activate()
        except Exception as e:
            self.LogError(f"Failure starting the XMLA Client Proxy Service: {e}")
            return
        self.serve_forever()

    def GetAuthorizationHeaderValue(self):
        authorizationHeader: Optional[str] = None
        username: Optional[str] = os.environ.get(ENV_XMLA_CLIENT_PROXY_USERNAME)
        password: Optional[str] = os.environ.get(ENV_XMLA_CLIENT_PROXY_PASSWORD)
        if (username is not None and password is not None):
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            authorizationHeader = f"Basic {token}"
        return authorizationHeader

    def Log(self, level: str, msg: str):
        if self.__doLogging:
            if level == "info":
                self.__logger.info(msg)
            elif level == "debug":
                self.__logger.debug(msg)
            elif level == "error":
                self.__logger.error(msg)

    def LogInfo(self, msg: str):
        self.Log("info", msg)

    def LogError(self, msg: str):
        self.Log("error", msg)

    def LogDebug(self, msg: str):
        self.Log("debug", msg)
            
class MessageHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, request, client_address, server: ProxyService):
        self.__logger =  logging.getLogger(__name__)
        self.__body: Optional[bytes] = None
        self.__requestId: Optional[int] = None
        self.__parent = server
        self.__processedMessage = False
        super().__init__(request, client_address, server)

    @property
    def Logger(self):
        return self.__logger

    @property
    def Parent(self):
        return self.__parent

    @property
    def LogMessages(self):
        return self.Parent.LogMessages
    
    @property
    def RequestId(self):
        if self.__requestId is None:
            self.__requestId = self.Parent.GetRequestId()
        return self.__requestId

    @property
    def ForwardingHost(self):
        return self.Parent.ForwardingHost

    def GetRequestBody(self):
        if self.__body is None:
            body = b""
            if "Content-Length" in self.headers:
                content_length = int(self.headers["Content-Length"])
                body = self.rfile.read(content_length)
            elif "chunked" in self.headers.get("Transfer-Encoding", ""):
                body = b""
                while True:
                    line = self.rfile.readline().strip()
                    if line == b"":
                        break
                    else:
                        chunk_length = int(line, 16)

                        if chunk_length != 0:
                            chunk = self.rfile.read(chunk_length)
                            body = body + chunk

                        # Each chunk is followed by an additional empty newline
                        # that we have to consume.
                        self.rfile.readline()

                    # Finally, a chunk size of 0 is an end indication
                    if chunk_length == 0:
                        break

            # remove the BOM if its there
            if body.startswith(b"\xef\xbb\xbf"):
                body = body[3:]
            if len(body) > 0:
                self.__body = body
        return self.__body
   
    @staticmethod
    def _redactHeadersForLog(headers):
        # Non-mutating: returns a new dict with Authorization redacted. Used
        # when we log the outbound (forwarded) headers, which carry the
        # translated `Snowflake Token="<PAT>"` value.
        redacted = {}
        for k, v in headers.items():
            if isinstance(k, str) and k.lower() == "authorization":
                if isinstance(v, str):
                    scheme = v.split(" ", 1)[0] if v else ""
                    redacted[k] = f"{scheme} <redacted>"
                else:
                    redacted[k] = "<redacted>"
            else:
                redacted[k] = v
        return redacted

    def handle_expect_100(self):
        if self.__processedMessage == True:
            newRequestId = self.Parent.GetRequestId()
            self.LogDebug(f"Recycling Message Handler {self.RequestId}->{newRequestId}")
            self.__requestId = newRequestId
            self.__body = None
            self.__processedMessage = False
        return True
        #response = self.ProxyMessage(is100Continue=True)
        #self.SendResponse(response) 
        #if response is not None and response.status_code < 400: 
        #    return True       
        #return False

    def do_GET(self):
        response = self.ProxyMessage()
        self.SendResponse(response)

    def do_PATCH(self):
        response = self.ProxyMessage()
        self.SendResponse(response)

    def do_PUT(self):
        response = self.ProxyMessage()
        self.SendResponse(response)

    def do_DELETE(self):
        response = self.ProxyMessage()
        self.SendResponse(response)

    def do_POST(self):
        response = self.ProxyMessage()
        self.SendResponse(response)

    def GetRequestFunction(self):
        request_function = None
        if self.command == "GET":
            request_function = requests.get
        elif self.command == "POST":
            request_function = requests.post
        elif self.command == "PATCH":
            request_function = requests.patch
        elif self.command == "PUT":
            request_function = requests.put
        elif self.command == "DELETE":
            request_function = requests.delete
        return request_function

    def ProxyMessage(self):
        if self.__processedMessage == True:
            newRequestId = self.Parent.GetRequestId()
            self.LogDebug(f"Recycling Message Handler {self.RequestId}->{newRequestId}")
            self.__requestId = newRequestId
            self.__body = None
            self.__processedMessage = False
        
        requestBodyBytes: Optional[bytes] = None
        requestBodyString: Optional[str] = None
        
        type = "REQUEST"

        # force the authentication header to use the environment user/password
        authorizationHeaderValue = self.Parent.GetAuthorizationHeaderValue()
        if authorizationHeaderValue is not None:
            self.LogDebug(f"{self.RequestId}\tAdding Authorization Header")
            self.headers.add_header("Authorization", authorizationHeaderValue)
            
        requestBodyBytes = self.GetRequestBody()

        if self.LogMessages:
            if requestBodyBytes is not None:
                requestBodyString = requestBodyBytes.decode(errors="ignore").replace("\n","").replace("\r","").replace("\t","")
            else:
                requestBodyString = ""
            self.LogInfo(f'{self.RequestId}\t{type}\t{self.command}\t{self.path}\t{self.client_address}\t{self._redactHeadersForLog(dict(self.headers))}\t{requestBodyString}')
        else:
            self.LogInfo(f'{self.RequestId}\t{type}\t{self.command}\t{self.path}\t{self.client_address}\t{self._redactHeadersForLog(dict(self.headers))}\t')
        
        response: Optional[requests.Response] = None
        headers = {}

        for k,v in self.headers.items():
            if k.lower() == "host":
                headers[k] = self.ForwardingHost
            elif k.lower() in ["transfer-encoding", "expect"]:
                pass
            else:
                headers[k] = v
        
        if "Content-Length" not in headers and requestBodyBytes is not None:
            headers["Content-Length"] = str(len(requestBodyBytes))
            
        forwardUrl = f"https://{self.ForwardingHost}{self.path}"
        
        request_function = self.GetRequestFunction()
        
        if request_function is not None:
            if self.LogMessages and len(requestBodyString or "") > 0:
                self.LogDebug(f"{self.RequestId}\tPROXY {type} TO {forwardUrl}\t{self.command}\t{self.path}\t{self.client_address}\t{self._redactHeadersForLog(dict(headers))}\t{requestBodyString}")
            else:               
                self.LogDebug(f"{self.RequestId}\tPROXY {type} TO {forwardUrl}\t{self.command}\t{self.path}\t{self.client_address}\t{self._redactHeadersForLog(dict(headers))}\t")
    
            response = request_function(forwardUrl, data=requestBodyBytes, headers=headers)
        else:
            response = None

        self.__processedMessage = True
        return response

    def SendResponse(self, response: Optional[requests.Response]):
        if response is None:
            self.LogError("No response received")
            self.send_response_only(code=404)            
            return

        responseHeaders: dict = dict(response.headers)
        contentBytes: Optional[bytes] = None
        contentString: Optional[str] = None

        if response.content is not None:
            if isinstance(response.content, str):
                contentBytes = response.content.encode()
                contentString = str(response.content)
            elif isinstance(response.content, bytes):
                contentBytes = response.content
                contentString = contentBytes.decode()
            else:
                self.LogError(f"{self.RequestId}\tResponse is not a string or bytes")

        if "Content-Length" not in responseHeaders and contentBytes is not None:
            responseHeaders["Content-Length"] = len(contentBytes)
        
        self.send_response(response.status_code)
        
        for k,v in responseHeaders.items():
            if k.lower() not in ("transfer-encoding"):
                self.send_header(k, v)            
        self.end_headers()

        if contentBytes is not None:
            self.wfile.write(contentBytes)

        responseStr = ""
        if self.LogMessages and contentString is not None:            
            responseStr = contentString.replace("\n","").replace("\r","").replace("\t","")
        self.LogInfo(f"{self.RequestId}\tRESPONSE\t{self.command}\t{response.status_code}\t{self.client_address}\t{self._redactHeadersForLog(dict(responseHeaders))}\t{responseStr}")
        return
    
    def Log(self, level: str, msg: str):
        if self.Parent.DoLogging:
            if level == "info":
                self.__logger.info(msg)
            elif level == "debug":
                self.__logger.debug(msg)
            elif level == "error":
                self.__logger.error(msg)
    
    def LogInfo(self, msg: str):
        self.Log("info", msg)

    def LogError(self, msg: str):
        self.Log("error", msg)

    def LogDebug(self, msg: str):
        self.Log("debug", msg)
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"XMLA Client Proxy Failed:\n{e}")

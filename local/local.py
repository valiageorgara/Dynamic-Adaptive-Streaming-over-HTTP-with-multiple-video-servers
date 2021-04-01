from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
import errno
import http.client
import logging
import mimetypes
import os
import posixpath
import requests
import shutil
import socket
import sys
from datetime import datetime
import time
import re
import numpy


timestamp = None
mean_rate = None
rate_per_sec = None
counter_per_sec = None
chunk_size = 8192


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    """ Handler to handle POST requests for actions.
    """
    index = None
    serve_path = None
    remote_server1_ip = None
    remote_server1_port = None
    remote_server2_ip = None
    remote_server2_port = None

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
    })

    def do_GET(self):
        """Serve a GET request."""
        self.send_head()
        print("GET timestamp " + str(datetime.now()))

    def do_HEAD(self):
        """Serve a HEAD request."""
        self.send_head()

    def send_head(self):
        """Common code for GET and HEAD commands."""
        segment = self.path[1:]

        # logging.info('Client from %s requested %s\n', self.client_address[0], segment)

        if not (segment in SimpleHTTPRequestHandler.index):
            # CACHE MISS
            # logging.info('CACHE MISS %s', segment + '\n')
            success = self.request_and_respond(segment, SimpleHTTPRequestHandler.remote_server1_ip,
                                               SimpleHTTPRequestHandler.remote_server1_port)
            if not success:
                success = self.request_and_respond(segment, SimpleHTTPRequestHandler.remote_server2_ip,
                                                   SimpleHTTPRequestHandler.remote_server2_port)
            if not success:
                # It's dead Jim
                self.send_response_only(404)
                self.send_header('Connection', 'close')
                self.end_headers()
        else:
            # CACHE HIT
            # logging.info('CACHE HIT %s', segment + '\n')
            self.respond(segment)

    def request_and_respond(self, segment, address, port):
        """
        Request file from a remote server and stream it to the client.

        First, attempt to request the file from Server No. 1.
        If Server No. 1 can not serve it, request the file from Server No. 2
        """
        global timestamp
        global mean_rate
        global rate_per_sec
        global counter_per_sec
        
        file_path = SimpleHTTPRequestHandler.serve_path + "/" + segment
        url = f"http://{address}:{port}/{segment}"

        success = False

        try:
            # Attempt to fetch segment from server No. 1
            # logging.info('Attempting to fetch %s from Server 1 at %s\n', segment, address)

            connection = http.client.HTTPConnection(address, port)
            connection.request("GET", f"/{segment}")

            # Another way - for testing only
            # url = "http://" + address + ":" + str(port) + "/" + segment
            # r = requests.get(url, allow_redirects=True, stream=True)

            # Ubuntu download - for testing only
            # connection = http.client.HTTPConnection("releases.ubuntu.com")
            # connection.request("GET", f"/focal/{segment}")

            r = connection.getresponse()

            # Another way - for testing only
            # if r.status_code >= 400:
            # logging.error("Unexpected status code %s accessing URL: %s\n", r.status_code, url)
            if r.status >= 400:
                # logging.error("Unexpected status code %s requesting %s from %s\n", r.status, segment, address)
                pass
            else:
                self.send_response_only(200)

                self.send_header("Content-Length", r.headers.get("Content-Length"))
                self.send_header("Content-Type", r.headers.get("Content-Type"))
                self.send_header("Last-Modified", r.headers.get("Last-Modified"))
                self.end_headers()
                total_bytes = int(r.headers.get('Content-Length'))

                # Another way - for testing only
                # self.send_header("Content-Length", r.headers["Content-Length"])
                # self.send_header("Content-Type", r.headers["Content-Type"])
                # self.send_header("Last-Modified", r.headers["Last-Modified"])
                # self.send_header("Connection", "close")
                # total_bytes = int(r.headers["Content-length"])
                # r.raise_for_status()
                # for chunk in r.iter_content(chunk_size=8192):

                with open(file_path, 'wb+') as f:
                    #mean_rate = (8 * 1024 * 1024) / 8
                    count = 0
                    if not timestamp:
                        timestamp = datetime.now() # make global
                        rate_per_sec = numpy.random.rayleigh(numpy.sqrt(2/numpy.pi) * mean_rate, 1)
                        counter_per_sec = rate_per_sec # make global
                    
                    while count < total_bytes:
                        chunk = r.read(chunk_size)
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        # if chunk:
                        l = len(chunk)
                        timestamp_now = datetime.now()
                        time_diff_millies = str(timestamp_now - timestamp)
                        time_diff = float(re.sub('[0-9]*:[0-9]*:', '', time_diff_millies))
                        # time_diff = (timestamp_now - timestamp).seconds
                        print(str(timestamp_now) + "-" + str(timestamp) + "=" + str(time_diff))
                        print(str(rate_per_sec) + ":" + str(l) + ":" + str(count) + ":" + str(counter_per_sec))
                        if l < chunk_size:
                            print("new segment")
                        if time_diff >= 1.0:
                            print(1)
                            rate_per_sec = numpy.random.rayleigh(numpy.sqrt(2 / numpy.pi) * mean_rate, 1)
                            counter_per_sec += rate_per_sec - l
                            timestamp = datetime.now()
                            self.wfile.write(chunk)
                            f.write(chunk)
                            count += l
                        else:
                            if counter_per_sec >= 0:
                                print(2)
                                self.wfile.write(chunk)
                                f.write(chunk)
                                count += l
                                counter_per_sec -= l
                            else:
                                print(3)
                                time.sleep(1.0 - time_diff)
                                rate_per_sec = numpy.random.rayleigh(numpy.sqrt(2 / numpy.pi) * mean_rate, 1)
                                counter_per_sec += rate_per_sec - l
                                timestamp = datetime.now()
                                self.wfile.write(chunk)
                                f.write(chunk)
                                count += l

                    # ging.info('Received and forwarded %s bytes\n', l)
                    logging.info('[%s] %s %s\n', datetime.now(), segment, address)

                    self.wfile.flush()

                # logging.info('Request from %s served\n', self.client_address[0])
                SimpleHTTPRequestHandler.index[segment] = file_path
                success = True

            connection.close()
        except (requests.exceptions.InvalidSchema, requests.exceptions.MissingSchema) as err:
            logging.error("Bad schema, expecting http:// or https://:\n %s\n", err)
        except ConnectionError as err:
            logging.error("Couldn't establish connection to %s:\n %s\n", url, err)
        except requests.exceptions.InvalidURL as err:
            logging.error("Invalid URL %s:\n %s\n", url, err)
        except requests.exceptions.RequestException as err:
            logging.error("Unknown error connecting to %s:\n %s\n", url, err)
        except OSError as err:
            logging.error("Error reading/writing to file\n %s\n", err)

        return success

    def respond(self, segment):
        """
        Stream the segment to the client.
        """
        global timestamp
        global mean_rate
        global rate_per_sec
        global counter_per_sec
        
        file_path = SimpleHTTPRequestHandler.index[segment]
        ctype = self.guess_type(file_path)

        if os.access(file_path, os.R_OK):
            try:
                with open(file_path, 'rb') as f:
                    fs = os.fstat(f.fileno())

                    self.send_response_only(200)
                    self.send_header("Content-type", ctype)
                    self.send_header("Content-Length", str(fs.st_size))
                    self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
                    self.end_headers()

                    #shutil.copyfileobj(f, self.wfile)
                    
                    #mean_rate = (8 * 1024 * 1024) / 8
                    count = 0
                    
                    if not timestamp:
                        timestamp = datetime.now() # make global
                        rate_per_sec = numpy.random.rayleigh(numpy.sqrt(2/numpy.pi) * mean_rate, 1)
                        counter_per_sec = rate_per_sec # make global
                    
                    while count < fs.st_size:
                        chunk = f.read(chunk_size)
                        # If you have chunk encoded response uncomment if
                        # and set chunk_size parameter to None.
                        # if chunk:
                        l = len(chunk)
                        timestamp_now = datetime.now()
                        time_diff_millies = str(timestamp_now - timestamp)
                        time_diff = float(re.sub('[0-9]*:[0-9]*:', '', time_diff_millies))
                        # time_diff = (timestamp_now - timestamp).seconds
                        print(str(timestamp_now) + "-" + str(timestamp) + "=" + str(time_diff))
                        print(str(rate_per_sec) + ":" + str(l) + ":" + str(count) + ":" + str(counter_per_sec))
                        if time_diff >= 1.0:
                            print(1)
                            rate_per_sec = numpy.random.rayleigh(numpy.sqrt(2 / numpy.pi) * mean_rate, 1)
                            counter_per_sec += rate_per_sec - l
                            timestamp = datetime.now()
                            self.wfile.write(chunk)
                            count += l
                        else:
                            if counter_per_sec >= 0:
                                print(2)
                                self.wfile.write(chunk)
                                count += l
                                counter_per_sec -= l
                            else:
                                print(3)
                                time.sleep(1.0 - time_diff)
                                print("time difference = " + str(time_diff))
                                print("counter_per_sec = " + str(counter_per_sec))
                                rate_per_sec = numpy.random.rayleigh(numpy.sqrt(2 / numpy.pi) * mean_rate, 1)
                                counter_per_sec += rate_per_sec - l
                                timestamp = datetime.now()
                                self.wfile.write(chunk)
                                count += l

                    # ging.info('Received and forwarded %s bytes\n', l)
                    logging.info('[%s] %s\n', datetime.now(), segment)

                self.wfile.flush()
            except OSError as err:
                logging.error("OS error: %s", err)
            except:
                logging.error("Unexpected error:", sys.exc_info()[0])
        else:
            self.send_response_only(404)
            self.send_header('Connection', 'close')
            self.end_headers()

    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """
        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']


def index_dir(serve_path):
    index = {}
    for r, d, f in os.walk(serve_path):
        for name in f:
            key = name.split('/')[-1]
            index[key] = os.path.join(r, name)
        # if name.endswith(".m4s"):
        # key = name.split('/')[-1]
        # index[key] = os.path.join(r, name)
        # elif name.endswith(".mpd"):
        # index[name] = os.path.join(r, name)
        # elif name.endswith(".zsync"):
        # index[name] = os.path.join(r, name)
    return index


def run_server(address="0.0.0.0", port=8000, serve_path=None, server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler,
               next_attempts=100):
    logging.basicConfig(level=logging.INFO)

    httpd = None
    print(mean_rate)
    
    while next_attempts > 0:
        try:
            server_address = (address, port)
            httpd = server_class(server_address, handler_class)

            SimpleHTTPRequestHandler.index = index_dir(serve_path)
            SimpleHTTPRequestHandler.serve_path = serve_path
            
            logging.info(f'{timestamp} Starting httpd at {address}:{port}...\n')
            httpd.serve_forever()
        except socket.error as e:
            if e.errno == errno.EADDRINUSE:
                next_attempts -= 1
                port += 1
            else:
                raise
        except KeyboardInterrupt:
            if httpd:
                logging.info('Stopping httpd...\n')
                httpd.server_close()
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rate", help="data rate", default=1000000, type=float)
    parser.add_argument("-a", "--address", help="serving port", default="127.0.0.3")
    parser.add_argument("-p", "--port", help="serving port", default=8003, type=int)
    parser.add_argument("-d", "--directory", help="segments directory (relative path)", default="./")
    parser.add_argument("-s1", "--server1", help="remote server No. 1", default="127.0.0.4")
    parser.add_argument("-p1", "--port1", help="serving port of remote server No. 1", default=8004, type=int)
    parser.add_argument("-s2", "--server2", help="remote server No. 2", default="127.0.0.4")
    parser.add_argument("-p2", "--port2", help="serving port of remote server No. 2", default=8004, type=int)
    args = parser.parse_args()

    SimpleHTTPRequestHandler.remote_server1_ip = args.server1
    SimpleHTTPRequestHandler.remote_server1_port = args.port1
    SimpleHTTPRequestHandler.remote_server2_ip = args.server2
    SimpleHTTPRequestHandler.remote_server2_port = args.port2
    
    mean_rate = args.rate * 1024 * 1024 / 8

    # Check directory existence and create it if necessary
    path = os.getcwd() + "/" + args.directory
    if not os.path.isdir(path):
        os.makedirs(path)

    if not os.path.isdir(path):
        sys.exit("Non-existent directory")

    run_server(args.address, args.port, path)

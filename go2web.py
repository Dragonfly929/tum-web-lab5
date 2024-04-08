import argparse
import ssl
import socket

from urllib.parse import urlparse
from bs4 import BeautifulSoup
from lxml import etree

HTTP_PORT = 80
HTTPS_PORT = 443


class Parser:

    def parse_url(self, url):
        parsed_url = urlparse(url)

        scheme = parsed_url.scheme
        host = parsed_url.netloc
        path = parsed_url.path

        return [scheme, host, path]

    def parse_html_page(self, data):
        soup = BeautifulSoup(data, 'html.parser')
        return soup.get_text()

    def parse_html_links(self, data):
        soup = BeautifulSoup(data, "html.parser")
        dom = etree.HTML(str(soup))

        links = dom.xpath("//span/a//following-sibling::h3/../@href")
        return links


class HTTPHandler:

    def __init__(self):
        self.search_link = "https://www.google.com/search?q={}"
        self.search_path = "/search?q={}"
        self.parser = Parser()

    def request(self, host, port, path):
        response = b""  # Initialize response as bytes
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))

        if port == HTTPS_PORT:
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(sock, server_hostname=host)

        sock.sendall(
            (f"GET {path} HTTP/1.1\r\n" +
             f"Host: {host}\r\n" +
             "Connection: close\r\n" +
             "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0\r\n" +
             "Accept: */*\r\n" +
             "\r\n").encode()
        )

        while True:
            data = sock.recv(4096)
            if not data:
                break
            response += data  # Append received data to response bytes

        sock.close()

        try:
            response_text = response.decode("utf-8")  # Attempt to decode response
        except UnicodeDecodeError as e:
            print(f"Error decoding response: {e}")
            return None, None  # Return None values to indicate decoding failure

        headers, body = response_text.split("\r\n\r\n", 1)
        return headers, body

    def search(self, queries):
        search_query = '+'.join(queries)

        port = HTTPS_PORT
        path = self.search_path.format(search_query)
        host = urlparse(
            self.search_link.format(search_query)
        ).netloc

        _, body = self.request(host, port, path)
        if body:
            return self.parser.parse_html_links(body)
        else:
            return []


def main():
    parser = argparse.ArgumentParser(description="Search for a word in a file or convert the contents to uppercase")
    parser.add_argument('-u', '--url', type=str, help='Make an HTTP request to URL and print the response')
    parser.add_argument('-s', '--search', type=str, help='Make an HTTP request to search and print top 10 results')
    args = parser.parse_args()

    if args.url:
        http_handler = HTTPHandler()
        url = args.url
        scheme, host, path = http_handler.parser.parse_url(url)
        if scheme == "http":
            port = HTTP_PORT
        else:
            port = HTTPS_PORT

        header, body = http_handler.request(host, port, path)
        if body:
            print(http_handler.parser.parse_html_page(body))
        else:
            print("No response received.")
    elif args.search:
        http_handler = HTTPHandler()
        links = http_handler.search([args.search])
        for idx, link in enumerate(links, 1):
            print(f"{idx}. {link}")
    else:
        print("Please provide a valid option. Use '-u' for making an HTTP request to a URL or '-s' for searching.")

if __name__ == "__main__":
    main()

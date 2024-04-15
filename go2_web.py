import argparse
import ssl
import socket
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from lxml import etree
import os

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
        # Get the text content and remove unnecessary whitespace
        text_content = soup.get_text().strip()
        return text_content

    def parse_html_links(self, data):
        soup = BeautifulSoup(data, "html.parser")
        dom = etree.HTML(str(soup))
        # Extract links and format them nicely
        links = dom.xpath("//span/a//following-sibling::h3/../@href")
        formatted_links = [link.replace('/url?q=', '') for link in links]
        return formatted_links


class HTTPHandler:
    def __init__(self):
        self.search_link = "https://www.google.com/search?q={}"
        self.search_path = "/search?q={}"
        self.parser = Parser()
        self.cache_dir = "cached_responses"
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.cache = {}

    def request(self, host, port, path, redirect_count=5):
        if redirect_count == 0:
            return None, None

        # Check if the response is cached
        cache_key = (host, port, path)
        cache_file_path = os.path.join(self.cache_dir, f"{hash(cache_key)}.txt")
        if os.path.exists(cache_file_path):
            with open(cache_file_path, "r") as f:
                headers, body = f.read().split("\n\n", 1)
            print("Fetching response from cache...")
            return headers, body.encode()

        response = b""
        with socket.create_connection((host, port)) as sock:
            if port == HTTPS_PORT:
                context = ssl.create_default_context()
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    request_string = (
                        f"GET {path} HTTP/1.1\r\n"
                        f"Host: {host}\r\n"
                        "Connection: close\r\n"
                        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0\r\n"
                        "Accept: */*\r\n"
                        "\r\n"
                    )
                    ssock.sendall(request_string.encode())
                    while True:
                        data = ssock.recv(4096)
                        if not data:
                            break
                        response += data
            else:
                request_string = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {host}\r\n"
                    "Connection: close\r\n"
                    "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0\r\n"
                    "Accept: */*\r\n"
                    "\r\n"
                )
                sock.sendall(request_string.encode())
                while True:
                    data = sock.recv(4096)
                    if not data:
                        break
                    response += data

        try:
            response_text = response.decode("utf-8")
        except UnicodeDecodeError as e:
            print(f"Error decoding response: {e}")
            return None, None

        headers, body = response_text.split("\r\n\r\n", 1)
        status_line = headers.split("\r\n")[0]
        status_code = int(status_line.split(" ")[1])

        if status_code in [301, 302]:  # Handle redirects
            redirect_url = headers.split("\r\n")[7].split(" ")[1]
            redirect_host, redirect_path = self.parser.parse_url(redirect_url)[1:]
            return self.request(redirect_host, port, redirect_path, redirect_count - 1)

        # Cache the response before returning
        with open(cache_file_path, "w", encoding="utf-8") as f:
            f.write(f"{headers}\n\n{body}")
        self.cache[cache_key] = (headers, body.encode())
        return headers, body.encode()

    def search(self, queries):
        search_query = '+'.join(queries)
        port = HTTPS_PORT
        path = self.search_path.format(search_query)
        host = urlparse(self.search_link.format(search_query)).netloc

        if path in self.cache:
            return self.cache[path]

        headers, body = self.request(host, port, path)
        if body:
            links = self.parser.parse_html_links(body)[:10]
            self.cache[path] = links
            return links
        else:
            return []


def main():
    parser = argparse.ArgumentParser(description="Search for a word in a file or convert the contents to uppercase")
    parser.add_argument('-u', '--url', type=str, help='Make an HTTP request to URL and print the response')
    parser.add_argument('-s', '--search', nargs='+', type=str,
                        help='Make an HTTP request to search and print top 10 results')
    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        print(f"Error: {e}")
        return

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
        links = http_handler.search(args.search)
        for idx, link in enumerate(links, 1):
            print(f"{idx}. {link}")

        if links:
            while True:
                try:
                    choice = int(input("Select a search result (1-10): "))
                    if 1 <= choice <= 10:
                        break
                    else:
                        print("Invalid choice. Please select a number between 1 and 10.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")

            selected_link = links[choice - 1]
            scheme, host, path = http_handler.parser.parse_url(selected_link)
            if scheme == "http":
                port = HTTP_PORT
            else:
                port = HTTPS_PORT

            header, body = http_handler.request(host, port, path)
            if body:
                print(http_handler.parser.parse_html_page(body))
            else:
                print("No response received.")
    else:
        print("Please provide a valid option. Use '-u' for making an HTTP request to a URL, or '-s' for searching.")


if __name__ == "__main__":
    main()
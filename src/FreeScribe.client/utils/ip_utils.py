import ipaddress
from urllib.parse import urlparse
import re


def extract_ip_from_url(url):
  """
  Extract the IP address from a URL.

  :param url: The URL to extract the IP address from.
  :type url: str
  :return: The extracted IP address.
  :rtype: str
  """
  parsed_url = urlparse(url)
  return parsed_url.hostname

def is_private_ip(ip_or_url):
  """
  Check if the given IP address is a private IP address (RFC 1918).

  :param ip: The IP address to check.
  :type ip: str
  :return: True if the IP address is private, False otherwise.
  :rtype: bool
  """
  try:
      ip = extract_ip_from_url(ip_or_url) if '://' in ip_or_url else ip_or_url
      ip_obj = ipaddress.ip_address(ip)
      return ip_obj.is_private
  except ValueError:
      # Handle invalid IP address
      return False

def is_valid_url(url):
    """
    Validates if the provided string is a URL.

    A URL is considered valid if it starts with 'http://' or 'https://', 
    optionally includes 'www.', and contains a combination of alphanumeric 
    characters, dots, and slashes.

    Args:
        url (str): The URL string to validate.

    Returns:
        bool: True if the string is a valid URL, False otherwise.
    """

    url_regex = re.compile(r'https?://(?:www\.)?[a-zA-Z0-9./]+')
    return re.match(url_regex, url) is not None

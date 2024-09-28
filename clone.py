import requests
from bs4 import BeautifulSoup
import os
import re
import urllib.parse
import tinycss2
import jsbeautifier

def get_html_css_js(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Get HTML
        html = str(soup)

        # Get and beautify CSS
        css_tags = soup.select('style, link[rel="stylesheet"]')
        css = ''
        for tag in css_tags:
            if tag.name == 'style':
                css += tag.string if tag.string else ''
            elif tag.name == 'link' and 'href' in tag.attrs:
                css_url = urllib.parse.urljoin(url, tag['href'])
                css_response = requests.get(css_url, stream=True, timeout=10)
                css_response.raise_for_status()
                if 'Content-Type' in css_response.headers and css_response.headers['Content-Type'].startswith('text/css'):
                    css += css_response.text
                else:
                    print(f"Skipped {css_url}: Not a CSS file (Content-Type: {css_response.headers.get('Content-Type')})")

        # Beautify CSS
        beautified_css = beautify_css(css)

        # Get and beautify JavaScript
        js_tags = soup.select('script[src], script:not([src])')
        js = ''
        for tag in js_tags:
            if tag.name == 'script' and 'src' in tag.attrs:
                js_url = urllib.parse.urljoin(url, tag['src'])
                js_response = requests.get(js_url, stream=True, timeout=10)
                js_response.raise_for_status()
                js += js_response.text
            elif tag.name == 'script' and tag.string:
                js += tag.string

        # Beautify JavaScript
        beautified_js = beautify_js(js)

        return html, beautified_css, beautified_js

    except requests.exceptions.RequestException as e:
        print(f"Error requesting {url}: {e}")
        return None, None, None

def beautify_css(css_code):
    try:
        # Use tinycss2 to parse the CSS code
        parsed_rules = tinycss2.parse_stylesheet(css_code, skip_whitespace=True)
        beautified_css = []

        # Iterate over rules and create a structured output
        for rule in parsed_rules:
            if rule.type == 'qualified-rule':
                # Serialize the selector (rule.prelude) and its content
                selector = tinycss2.serialize(rule.prelude).strip()
                beautified_css.append(f"{selector} {{")
                declarations = tinycss2.parse_declaration_list(rule.content)
                for declaration in declarations:
                    if declaration.type == 'declaration':
                        prop = declaration.name
                        value = tinycss2.serialize(declaration.value).strip()
                        beautified_css.append(f"    {prop}: {value};")
                beautified_css.append("}")
            elif rule.type == 'error':
                print(f"CSS Parsing error: {rule.message}")

        return "\n".join(beautified_css)

    except tinycss2.CSSParseError as e:
        print(f"CSS Parsing error: {e}")
        return None

def beautify_js(js_code):
    try:
        # Use jsbeautifier to beautify JavaScript code
        beautifier_options = jsbeautifier.default_options()
        beautifier_options.indent_size = 2
        beautifier_options.space_before_conditional = True
        beautifier_options.keep_array_indentation = True
        beautifier_options.break_chained_methods = True

        beautified_js = jsbeautifier.beautify(js_code, beautifier_options)
        return beautified_js

    except jsbeautifier.BeautifierError as e:
        print(f"JavaScript beautification error: {e}")
        return None

def download_image(url, file_path):
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type')
        if content_type and 'image' in content_type:
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as file:
                    for chunk in response:
                        file.write(chunk)
                print(f"Downloaded and saved {url} to {file_path}")  # Debugging line
            else:
                print(f"File {file_path} already exists. Skipping download.")
        else:
            print(f"Skipped {url}: Not an image (Content-Type: {content_type})")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")

def extract_image_urls(html, base_url):
    urls = []
    soup = BeautifulSoup(html, 'html.parser')
    img_tags = soup.find_all('img')
    for img in img_tags:
        src = img.get('src')
        if src:
            full_url = urllib.parse.urljoin(base_url, src)
            print(f"Found image URL: {full_url}")  # Debugging line
            urls.append(full_url)
    return urls

def main():
    url = 'https://www.netflix.com/in/'  # Replace with the website URL you want to clone
    html, css, js = get_html_css_js(url)
    if html and css and js:
        image_urls = extract_image_urls(html, url)

        # Create a directory to save the cloned website
        if not os.path.exists('cloned_website'):
            os.makedirs('cloned_website')

        # Save the HTML, CSS, and JavaScript to files
        with open('cloned_website/index.html', 'w', encoding='utf-8') as f:
            f.write(re.sub(r'<head>', '<head><link rel="stylesheet" href="styles.css">', html))

        with open('cloned_website/styles.css', 'w', encoding='utf-8') as f:
            f.write(css)

        with open('cloned_website/scripts.js', 'w', encoding='utf-8') as f:
            f.write(js)

        # Download the images
        for i, img_url in enumerate(image_urls):
            file_name = f'cloned_website/image_{i}.jpg'
            download_image(img_url, file_name)

if __name__ == "__main__":
    main()
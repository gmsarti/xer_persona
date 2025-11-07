import random
import time
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .config import BASE_URL, HEADERS
from .db import insert_tale


def fetch_page(client, url):
    """Faz a requisição HTTP e retorna um objeto BeautifulSoup."""
    try:
        response = client.get(url, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except httpx.RequestError as e:
        print(f'Erro ao acessar {url}: {e}')
        return None


def get_tales_links(client, start_url):
    """Busca a página inicial e extrai os links para as páginas de contos."""
    print(f'Buscando links de categorias em: {start_url}')
    soup = fetch_page(client, start_url)
    if not soup:
        return []

    target_urls = set()
    all_links = soup.find_all('a', href=True)
    for link in all_links:
        href = link['href']
        if (
            href.endswith('.html')
            and not href.startswith('#')
            and not href.startswith('http')
            and href != 'folktexts.html'
        ):
            full_url = urljoin(BASE_URL, href)
            target_urls.add(full_url)

    print(f'Encontrados {len(target_urls)} links de categorias.')
    return list(target_urls)


def scrape_tales_from_page(soup, tale_url):
    """Extrai todos os contos de uma única página."""
    page_tales_data = []
    all_h2s = soup.find_all('h2')

    tale_headers = [
        h2 for h2 in all_h2s if not h2.find('a', attrs={'name': 'contents'})
    ]

    for h2 in tale_headers:
        current_tale = {
            'title': h2.get_text(strip=True),
            'url': tale_url,
            'origin': 'N/A',
        }
        content_nodes = []

        for sibling in h2.find_next_siblings():
            if sibling.name == 'h2':
                break
            if sibling.name in ('hr', 'p') and not sibling.get_text(strip=True):
                continue
            content_nodes.append(sibling)

        story_parts = []
        for node in content_nodes:
            if not node.name:
                continue
            if node.name == 'h3':
                current_tale['origin'] = node.get_text(strip=True)
            elif node.name in ('p', 'blockquote'):
                story_parts.append(node.get_text(strip=True))

        current_tale['story'] = '\n\n'.join(story_parts)
        page_tales_data.append(current_tale)

    return page_tales_data


def run_scraper(conn, limit_pages=None):
    """Orquestra o processo completo de raspagem e salvamento."""
    with httpx.Client(verify=False, headers=HEADERS) as client:
        # Pega os links das categorias (ex: german, french, etc.)
        tales_pages_urls = get_tales_links(client, urljoin(BASE_URL, 'folktexts.html'))

        if limit_pages:
            tales_pages_urls = tales_pages_urls[:limit_pages]
            print(
                f'Limitando a raspagem para as primeiras {limit_pages} páginas de categoria.'
            )

        # Itera sobre cada página de categoria para extrair os contos
        for tale_url in tales_pages_urls:
            print(f'Raspando página: {tale_url}')
            soup = fetch_page(client, tale_url)
            if not soup:
                continue

            tales_data = scrape_tales_from_page(soup, tale_url)
            print(f'  Encontrados {len(tales_data)} contos.')

            for tale in tales_data:
                insert_tale(
                    conn, tale['title'], tale['origin'], tale['url'], tale['story']
                )

            # Pausa para não sobrecarregar o servidor
            delay = random.uniform(1, 3)
            print(f'  Aguardando {delay:.2f} segundos...')
            time.sleep(delay)
    print('Raspagem concluída.')

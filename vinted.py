from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import asyncio

async def fetch_vinted_items(search_url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_extra_http_headers(headers)
            await page.goto(search_url)

            # Check if the region dropdown exists before setting its value
            if await page.query_selector('select[name="region"]'):
                await page.evaluate("() => { document.querySelector('select[name=\"region\"]').value = 'es'; }")

            # Reject cookies
            if await page.query_selector('button[aria-label="Reject all"]'):
                await page.evaluate("() => { document.querySelector('button[aria-label=\"Reject all\"]').click(); }")

            # Wait for JavaScript to load the articles
            await page.wait_for_selector(".feed-grid__item")

            html_content = await page.content()
            await browser.close()

    except Exception as e:
        print(f"Error fetching the URL: {e}")
        return []

    soup = BeautifulSoup(html_content, "lxml")

    items = []

    for item_div in soup.select(".feed-grid__item"):
        link_tag = item_div.find("a")
        img_tag = item_div.find("img")

        title = img_tag["alt"] if img_tag and img_tag.has_attr("alt") else "No title"
        url = link_tag["href"] if link_tag and link_tag.has_attr("href") else "No link"
        thumbnail = img_tag["src"] if img_tag and img_tag.has_attr("src") else "No thumbnail"

        # Skip items without proper links
        if url == "No link":
            continue

        title_parts = title.split(", ")

        # Extract the first part of the title, the "marca:" part, and the "modelo:" part
        description = title_parts[0] if title_parts else ""
        marca_part = next((part for part in title_parts if "marca:" in part), "")
        modelo_part = next((part for part in title_parts if "modelo:" in part), "")

        # Add the text after "marca:" and "modelo:" to the main description
        if marca_part:
            description += f", {marca_part}"
        if modelo_part:
            description += f", {modelo_part}"

        estado_part = next((part for part in title_parts if "estado:" in part), "No estado")
        first_price = next((part for part in title_parts if "€" in part), "No price")

        items.append({
            "description": description,
            "conditions": estado_part,
            "price": first_price,
            "url": url,
            "thumbnail": thumbnail
        })

    return items

if __name__ == "__main__":
    search_url = "https://www.vinted.es/catalog?search_text=iphone%2014%20pro&time=1743887965&order=newest_first&disabled_personalization=true&page=1&catalog%5B%5D=2999&brand_ids%5B%5D=54661&sim_lock_ids%5B%5D=1313"  # Replace this with a valid URL
    items = asyncio.run(fetch_vinted_items(search_url))

    for item in items:
        print(f"📱 desc: {item['description']}")
        print(f"💰 price: {item['price']}")
        print(f"📦 estado: {item['conditions']}")
        print(f"🔗 article link: {item['url']}")
        print(f"📸 photo: {item['thumbnail']}")
        print("-" * 50)

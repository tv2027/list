from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

def crawl_thapcam():
    # Cấu hình Chrome chạy ẩn (Headless)
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Giả lập User-Agent để tránh bị chặn
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # Khởi tạo Driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        url = "https://thapcam24h.net/" # Thay đổi domain nếu họ đổi link
        driver.get(url)
        
        # Chờ 5-10 giây để JavaScript load xong các trận đấu
        time.sleep(7)

        # Lấy HTML đã render xong
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # Tìm các khối trận đấu (Lưu ý: Tên class có thể thay đổi theo giao diện web)
        # Thông thường sẽ nằm trong các thẻ div có class liên quan đến 'match-item' hoặc 'match-card'
        categories = soup.select('.nav-item') # Đây là CSS Selector ví dụ

        print(f"--- ĐANG CÓ {len(categories)} Categories ---")
        
        for category in categories:
            try:
                # Trích xuất thông tin (Ví dụ: Thời gian, Đội 1, Đội 2)
                item = category.select_one('.nav-item').text.strip()
                #team_home = category.select_one('.team-home').text.strip()
                #team_away = category.select_one('.team-away').text.strip()
                #league = category.select_one('.league-name').text.strip()

                print(f"item: {item}")
            except Exception:
                continue

    except Exception as e:
        print(f"Lỗi: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    crawl_thapcam()
